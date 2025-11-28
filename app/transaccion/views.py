import json
import logging
from decimal import Decimal
import stripe
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from commons.enums import EstadoTransaccionEnum, TipoMovimientoEnum, TipoTransaccionEnum, PaymentTypeEnum
from clientes.models import Cliente
from monedas.models import Moneda, TasaCambio
from payments.models import PaymentMethod
from .forms import TransaccionForm
from .models import Movimiento, Transaccion
from .services import (
    calcular_transaccion,
    confirmar_transaccion,
    cancelar_transaccion,
    crear_transaccion,
    crear_checkout_para_transaccion,
    expirar_transacciones_pendientes,
    requiere_pago_tarjeta,
    verificar_pago_stripe,
)
from tauser.services import validar_stock_tauser_para_transaccion

@require_POST
def marcar_pagada_simple(request, pk):
    # Filtrar por clientes del usuario autenticado
    if request.user.is_authenticated:
        tx = get_object_or_404(
            Transaccion.objects.filter(cliente__usuarios=request.user), 
            pk=pk
        )
    else:
        tx = get_object_or_404(Transaccion, pk=pk)
    
    if tx.estado != EstadoTransaccionEnum.PAGADA:
        tx.estado = EstadoTransaccionEnum.PAGADA
        tx.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))

@csrf_exempt
@require_http_methods(["POST"])
def vincular_tauser(request):
    """
    Recibe transaccion_id y tauser_id por POST, vincula el Tauser a la transacción (actualiza campo tauser_id).
    """
    transaccion_id = request.POST.get("transaccion_id")
    tauser_id = request.POST.get("tauser_id")
    if not transaccion_id or not tauser_id:
        return JsonResponse({"ok": False, "mensaje": "Faltan parámetros."}, status=400)
    try:
        # Filtrar por clientes del usuario autenticado
        if request.user.is_authenticated:
            tx = Transaccion.objects.filter(cliente__usuarios=request.user).get(id=transaccion_id)
        else:
            tx = Transaccion.objects.get(id=transaccion_id)
        
        tx.tauser_id = tauser_id
        tx.save(update_fields=["tauser_id"])
        return JsonResponse({"ok": True, "mensaje": "Tauser vinculado correctamente a la transacción."})
    except Transaccion.DoesNotExist:
        return JsonResponse({"ok": False, "mensaje": "Transacción no encontrada."}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "mensaje": f"Error al vincular Tauser: {str(e)}"}, status=500)

# --- API para validar stock de tauser para una transacción ---
from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
@require_http_methods(["POST"])
def validar_stock_tauser(request):
    """
    Recibe transaccion_id y tauser_id por POST, llama a validar_stock_tauser_para_transaccion y retorna el resultado como JSON.
    """
    tauser_id = request.POST.get("tauser_id")
    monto = request.POST.get("monto")
    moneda_id = request.POST.get("moneda_id")
    if not tauser_id or not monto or not moneda_id:
        return JsonResponse({"ok": False, "mensaje": "Faltan parámetros."}, status=400)
    # Llama a la función de validación adaptada para estos parámetros
    resultado = validar_stock_tauser_para_transaccion(tauser_id=tauser_id, monto=monto, moneda_id=moneda_id)
    # Serializar el objeto moneda si está presente
    if "moneda" in resultado and resultado["moneda"]:
        resultado["moneda"] = str(resultado["moneda"])
    return JsonResponse(resultado)

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY

@require_GET
def medios_pago_por_cliente(request):
    """
    Devuelve los métodos de pago asociados a un cliente en formato JSON.
    Recibe ?cliente_id=<id> por GET.
    """
    cliente_id = request.GET.get("cliente_id")
    if not cliente_id:
        return JsonResponse({"error": "Falta cliente_id"}, status=400)
    
    # Validar que el cliente pertenezca al usuario autenticado
    if request.user.is_authenticated:
        try:
            cliente = Cliente.objects.filter(usuarios=request.user).get(pk=cliente_id)
        except Cliente.DoesNotExist:
            return JsonResponse({"error": "Cliente no encontrado o no autorizado"}, status=404)
    else:
        return JsonResponse({"error": "Usuario no autenticado"}, status=401)
    
    medios = PaymentMethod.objects.filter(cliente_id=cliente_id)
    medios_list = [
        {
            "id": m.id,
            "tipo": m.payment_type,
            "descripcion": str(m),
        }
        for m in medios
    ]
    return JsonResponse({"medios": medios_list})


@require_GET
def medios_acreditacion_por_cliente(request):
    """
    Devuelve los medios de acreditación asociados a un cliente en formato JSON.
    Recibe ?cliente_id=<id> por GET.
    """
    from medios_acreditacion.models import MedioAcreditacion
    
    cliente_id = request.GET.get("cliente_id")
    if not cliente_id:
        return JsonResponse({"error": "Falta cliente_id"}, status=400)
    
    # Validar que el cliente pertenezca al usuario autenticado
    if request.user.is_authenticated:
        try:
            cliente = Cliente.objects.filter(usuarios=request.user).get(pk=cliente_id)
        except Cliente.DoesNotExist:
            return JsonResponse({"error": "Cliente no encontrado o no autorizado"}, status=404)
    else:
        return JsonResponse({"error": "Usuario no autenticado"}, status=401)
    
    medios = MedioAcreditacion.objects.filter(cliente_id=cliente_id)
    medios_list = [
        {
            "id": m.id,
            "tipo": m.tipo_medio,
            "descripcion": str(m),
        }
        for m in medios
    ]
    return JsonResponse({"medios": medios_list})

@require_http_methods(["GET", "POST"])
def tramitar_transaccion_terminal(request):
    """
    Simula la terminal física (tauser) para pagos en efectivo.
    Permite buscar por ID y confirmar o cancelar la transacción.
    """
    datos_transaccion = None
    error = None
    mensaje = None
    transaccion_id = ""

    if request.method == "POST":
        transaccion_id = request.POST.get("transaccion_id", "").strip()
        accion = request.POST.get("accion", "buscar")

        if not transaccion_id:
            error = "Debe ingresar el ID de la transacción."
        else:
            try:
                tx = Transaccion.objects.select_related("cliente", "moneda").get(pk=transaccion_id)
            except Transaccion.DoesNotExist:
                tx = None
                error = f"No se encontró la transacción #{transaccion_id}."

            if tx:
                if accion == "buscar":
                    # Solo mostrar si está pendiente
                    if tx.estado != EstadoTransaccionEnum.PENDIENTE:
                        error = f"La transacción #{tx.id} no está pendiente (estado actual: {tx.estado})."
                    else:
                        tasa_actual = (
                            TasaCambio.objects.filter(moneda=tx.moneda, activa=True)
                            .latest("fecha_creacion")
                            .compra
                        )
                        datos_transaccion = {
                            "id": tx.id,
                            "tipo": tx.get_tipo_display(),
                            "moneda": tx.moneda,
                            "tasa": tx.tasa_aplicada,
                            "tasa_recalculada": tasa_actual,
                            "monto_operado": tx.monto_operado,
                            "monto_pyg": tx.monto_pyg,
                            "cliente": tx.cliente,
                            "estado": tx.estado,
                        }

                elif accion == "confirmar":
                    try:
                        confirmar_transaccion(tx)
                        mensaje = f"Transacción #{tx.id} confirmada correctamente."
                    except Exception as e:
                        error = str(e)

                elif accion == "cancelar":
                    try:
                        cancelar_transaccion(tx)
                        mensaje = f"Transacción #{tx.id} cancelada correctamente."
                    except Exception as e:
                        error = str(e)

    context = {
        "datos_transaccion": datos_transaccion,
        "error": error,
        "mensaje": mensaje,
        "transaccion_id": transaccion_id,
    }
    return render(request, "transacciones/terminal.html", context)

def transacciones_list(request):
    order = request.GET.get("order")
    dir_ = request.GET.get("dir")
    cliente_id = request.GET.get("cliente")

    # ----- Estado: por defecto 'pendiente' -----
    estado_qs = request.GET.get("estado", "").lower().strip()
    estados_validos = {
        "pendiente": EstadoTransaccionEnum.PENDIENTE,
        "pagada": EstadoTransaccionEnum.PAGADA,
        "completada": EstadoTransaccionEnum.COMPLETADA,
        "cancelada": EstadoTransaccionEnum.CANCELADA,
        "anulada": EstadoTransaccionEnum.ANULADA,
        "todas": None,
    }
    # default si no viene o no es válido
    if estado_qs not in estados_validos:
        estado_qs = "pendiente"

    # Si el usuario no está autenticado, no filtrar por usuario (evita error de SimpleLazyObject)
    if request.user.is_authenticated:
        transacciones = (
            Transaccion.objects
            .filter(cliente__usuarios=request.user)
            .select_related("cliente", "moneda", "medio_pago", "medio_cobro")
        )
        base = Transaccion.objects.filter(cliente__usuarios=request.user)
    else:
        transacciones = (
            Transaccion.objects
            .select_related("cliente", "moneda", "medio_pago", "medio_cobro")
        )
        base = Transaccion.objects.all()

    expirar_transacciones_pendientes(base)

    # filtro por cliente (si aplica)
    if cliente_id:
        transacciones = transacciones.filter(cliente_id=cliente_id)
        base = base.filter(cliente_id=cliente_id)

    # filtro por estado (si NO es 'todas')
    estado_enum = estados_validos[estado_qs]
    if estado_enum is not None:
        transacciones = transacciones.filter(estado=estado_enum)

    # orden por fecha (default desc)
    if order == "fecha":
        transacciones = transacciones.order_by("fecha" if dir_ == "asc" else "-fecha")
    else:
        transacciones = transacciones.order_by("-fecha")

    counts = {
        "pendiente": base.filter(estado=EstadoTransaccionEnum.PENDIENTE).count(),
        "pagada": base.filter(estado=EstadoTransaccionEnum.PAGADA).count(),
        "completada": base.filter(estado=EstadoTransaccionEnum.COMPLETADA).count(),
        "cancelada": base.filter(estado=EstadoTransaccionEnum.CANCELADA).count(),
        "anulada": base.filter(estado=EstadoTransaccionEnum.ANULADA).count(),
        "todas": base.count(),
    }

    # Solo mostrar clientes asociados al usuario autenticado
    if request.user.is_authenticated:
        clientes = Cliente.objects.filter(usuarios=request.user).order_by("nombre")
    else:
        clientes = Cliente.objects.none()
    
    from tauser.models import Tauser
    tausers = Tauser.objects.filter(estado="activo")
    ctx = {
        "transacciones": transacciones,
        "clientes": clientes,
        "cliente_id": cliente_id,
        "estado_qs": estado_qs,
        "counts": counts,
        "tausers": tausers,
    }
    return render(request, "transacciones/transacciones_list.html", ctx)


def confirmar_view(request, pk):
    """
    Confirma una transacción pendiente.
    - Si no tiene medio_pago (tarjeta por Stripe) → redirigir a Stripe checkout
    - Si tiene medio_pago guardado (transferencia/billetera) → procesa por SIPAP
    - Si es efectivo → confirmación manual
    """
    # Filtrar por clientes del usuario autenticado
    if request.user.is_authenticated:
        transaccion = get_object_or_404(
            Transaccion.objects.filter(cliente__usuarios=request.user), 
            pk=pk
        )
    else:
        transaccion = get_object_or_404(Transaccion, pk=pk)
    
    try:
        # Si NO tiene medio_pago, asumimos que es tarjeta (Stripe)
        if not transaccion.medio_pago:
            messages.info(
                request,
                f"Redirigiendo a pasarela de pago Stripe para transacción {transaccion.id}..."
            )
            return redirect("transacciones:iniciar_pago_tarjeta", pk=transaccion.id)
        
        # Si tiene medio_pago, usar SIPAP automáticamente
        confirmar_transaccion(transaccion)
        
        # Mensaje personalizado según si usó SIPAP o no
        if transaccion.medio_pago.puede_usar_sipap():
            messages.success(
                request, 
                f"✅ Transacción {transaccion.id} confirmada exitosamente. "
                f"Pago procesado via pasarela SIPAP ({transaccion.medio_pago.get_metodo_sipap()})."
            )
        else:
            messages.success(
                request, 
                f"✅ Transacción {transaccion.id} confirmada correctamente (manual)."
            )
    
    except ValidationError as e:
        # Error de validación o rechazo de SIPAP
        messages.error(
            request, 
            f"❌ Error al confirmar transacción {transaccion.id}: {str(e)}"
        )
    except Exception as e:
        # Error inesperado
        logger.error(
            f"Error inesperado al confirmar transacción {transaccion.id}: {str(e)}", 
            exc_info=True
        )
        messages.error(
            request, 
            f"❌ Error inesperado al confirmar transacción {transaccion.id}. "
            f"Contacte al administrador."
        )
    
    return redirect("transacciones:transacciones_list")


def cancelar_view(request, pk):
    # Filtrar por clientes del usuario autenticado
    if request.user.is_authenticated:
        transaccion = get_object_or_404(
            Transaccion.objects.filter(cliente__usuarios=request.user), 
            pk=pk
        )
    else:
        transaccion = get_object_or_404(Transaccion, pk=pk)
    
    try:
        cancelar_transaccion(transaccion)
        messages.success(request, f"Transacción {transaccion.id} cancelada.")
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect("transacciones:transacciones_list")


def transaccion_create(request):
    if request.method == "POST":
        form = TransaccionForm(request.POST)
        if form.is_valid():
            cliente = form.cleaned_data["cliente"]
            tipo = form.cleaned_data["tipo"]
            moneda_operada = form.cleaned_data["moneda"]
            monto_operado = form.cleaned_data["monto_operado"]
            medio_pago = form.cleaned_data["medio_pago"]

            try:
                tauser_id = request.POST.get("tauser_id")
                tauser = None
                if tauser_id:
                    from tauser.models import Tauser
                    tauser = Tauser.objects.filter(id=tauser_id).first()
                calculo = calcular_transaccion(cliente, tipo, moneda_operada, monto_operado, medio_pago)
                transaccion = crear_transaccion(
                    cliente,
                    tipo,
                    moneda_operada,
                    monto_operado,
                    calculo["tasa_aplicada"],
                    calculo["comision"],
                    calculo["monto_pyg"],
                    medio_pago,
                    tauser
                )
                messages.success(request, 
                    f"Transacción {transaccion.id} creada correctamente. "
                    f"Código para pago en terminal: {transaccion.uuid}"
                )
                return redirect("transacciones:transacciones_list")
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Error en el cálculo: {e}")

        # Si hay error, vuelve a mostrar el formulario con mensajes
        return render(request, "transacciones/transaccion_form.html", {"form": form})
    else:
        form = TransaccionForm()

    return render(request, "transacciones/transaccion_form.html", {"form": form})


@require_http_methods(["GET", "POST"])
def compra_moneda(request):
    """
    Vista dedicada para COMPRA de moneda extranjera.
    El cliente PAGA en PYG:
    - Efectivo → Terminal (Tauser)
    - Tarjeta → Stripe (checkout directo, no se guarda en DB)
    - Transferencia → SIPAP (usa cuenta bancaria guardada)
    - Billetera → SIPAP (usa billetera guardada)
    """
    if request.method == "POST":
        try:
            cliente_id = request.POST.get("cliente_id")
            moneda_id = request.POST.get("moneda_id")
            monto_operado = request.POST.get("monto_operado")
            metodo_pago = request.POST.get("metodo_pago")  # 'efectivo', 'tarjeta', 'transferencia', 'billetera'
            metodo_pago_id = request.POST.get("metodo_pago_id")  # ID del PaymentMethod (si aplica)

            # Validaciones básicas
            if not all([cliente_id, moneda_id, monto_operado, metodo_pago]):
                messages.error(request, "Faltan datos requeridos")
                return redirect("transacciones:compra_moneda")

            cliente = get_object_or_404(Cliente, pk=int(cliente_id))
            moneda = get_object_or_404(Moneda, pk=int(moneda_id))
            monto = Decimal(str(monto_operado))
            
            # Determinar medio_pago según el método seleccionado
            medio_pago_obj = None
            tipo_metodo_override = None
            
            if metodo_pago == 'efectivo':
                # Para efectivo, usar método del sistema
                medio_pago_obj = PaymentMethod.get_metodo_sistema('efectivo')
                tipo_metodo_override = 'efectivo'
            elif metodo_pago == 'tarjeta':
                # Para tarjeta, usar método del sistema
                medio_pago_obj = PaymentMethod.get_metodo_sistema('tarjeta')
                tipo_metodo_override = 'tarjeta'
            elif metodo_pago in ['transferencia', 'billetera']:
                # Para transferencia y billetera, se requiere un método guardado del cliente
                if not metodo_pago_id:
                    messages.error(request, f"Debe seleccionar un método de {metodo_pago} guardado")
                    return redirect("transacciones:compra_moneda")
                medio_pago_obj = get_object_or_404(PaymentMethod, pk=int(metodo_pago_id), cliente=cliente)
                
                # Validar que el tipo de PaymentMethod corresponda al método seleccionado
                if metodo_pago == 'transferencia' and medio_pago_obj.payment_type != PaymentTypeEnum.CUENTA_BANCARIA.value:
                    messages.error(request, "El método seleccionado no es una cuenta bancaria válida")
                    return redirect("transacciones:compra_moneda")
                elif metodo_pago == 'billetera' and medio_pago_obj.payment_type != PaymentTypeEnum.BILLETERA.value:
                    messages.error(request, "El método seleccionado no es una billetera válida")
                    return redirect("transacciones:compra_moneda")
            else:
                messages.error(request, f"Método de pago '{metodo_pago}' no reconocido")
                return redirect("transacciones:compra_moneda")

            # Calcular y crear transacción
            tauser_id = request.POST.get("tauser_id")
            tauser = None
            if tauser_id:
                from tauser.models import Tauser
                tauser = Tauser.objects.filter(id=tauser_id).first()
            calculo = calcular_transaccion(
                cliente, 
                TipoTransaccionEnum.COMPRA, 
                moneda, 
                monto,
                medio_pago_obj,
                tipo_metodo_override
            )
            transaccion = crear_transaccion(
                cliente,
                TipoTransaccionEnum.COMPRA,
                moneda,
                monto,
                calculo["tasa_aplicada"],
                calculo["comision"],
                calculo["monto_pyg"],
                medio_pago_obj,
                tauser
            )

            # Preparar datos para el modal
            context = {
                'transaccion': transaccion,
                'metodo_pago': metodo_pago,
                'calculo': calculo,
                'cliente': cliente,
                'moneda': moneda,
            }
            # Renderizar template con modal de confirmación
            return render(request, "transacciones/transaccion_confirmada.html", context)

        except ValidationError as e:
            messages.error(request, f"Error de validación: {str(e)}")
        except Exception as e:
            logger.exception("Error al crear transacción de compra")
            messages.error(request, f"Error inesperado: {str(e)}")
        
        return redirect("transacciones:compra_moneda")
    
    # GET: mostrar formulario
    # Solo mostrar clientes asociados al usuario operador
    clientes = Cliente.objects.filter(usuarios=request.user).order_by("nombre")
    monedas = Moneda.objects.filter(activa=True).order_by("nombre")
    from tauser.models import Tauser
    tausers = Tauser.objects.filter(estado="activo")
    context = {
        "clientes": clientes,
        "monedas": monedas,
        "tausers": tausers,
    }
    return render(request, "transacciones/compra_moneda.html", context)


@require_http_methods(["GET", "POST"])
def venta_moneda(request):
    """
    Vista dedicada para VENTA de moneda extranjera.
    El cliente ENTREGA moneda extranjera en efectivo y RECIBE PYG 
    (en efectivo o por transferencia).
    """
    if request.method == "POST":
        try:
            cliente_id = request.POST.get("cliente_id")
            moneda_id = request.POST.get("moneda_id")
            monto_operado = request.POST.get("monto_operado")
            metodo_cobro = request.POST.get("metodo_cobro")  # 'efectivo', 'transferencia'
            medio_cobro_id = request.POST.get("medio_cobro_id")  # ID del MedioAcreditacion (si aplica)

            # Validaciones básicas
            if not all([cliente_id, moneda_id, monto_operado, metodo_cobro]):
                messages.error(request, "Faltan datos requeridos")
                return redirect("transacciones:venta_moneda")

            cliente = get_object_or_404(Cliente, pk=int(cliente_id))
            moneda = get_object_or_404(Moneda, pk=int(moneda_id))
            monto = Decimal(str(monto_operado))
            
            # Para VENTA, el cliente COBRA en PYG (no paga)
            # Determinar el tipo de método para calcular comisiones
            tipo_metodo_override = None
            medio_pago_obj = None
            medio_cobro_obj = None
            
            if metodo_cobro == 'efectivo':
                # Cliente cobra en efectivo - usar sistema MedioAcreditacion
                from medios_acreditacion.models import MedioAcreditacion
                medio_cobro_obj = MedioAcreditacion.get_metodo_sistema('efectivo')
                tipo_metodo_override = 'efectivo'
            elif metodo_cobro == 'tarjeta':
                # Cliente cobra en tarjeta - usar sistema MedioAcreditacion
                from medios_acreditacion.models import MedioAcreditacion
                medio_cobro_obj = MedioAcreditacion.get_metodo_sistema('tarjeta')
                tipo_metodo_override = 'tarjeta'
            elif metodo_cobro == 'transferencia':
                # Cliente cobra por transferencia - usar MedioAcreditacion del cliente
                tipo_metodo_override = 'transferencia'
                
                # Validar que tenga un medio de cobro configurado
                if not medio_cobro_id:
                    messages.error(request, "Debe seleccionar una cuenta bancaria para recibir la transferencia")
                    return redirect("transacciones:venta_moneda")
                
                from medios_acreditacion.models import MedioAcreditacion
                medio_cobro_obj = get_object_or_404(
                    MedioAcreditacion, 
                    pk=int(medio_cobro_id), 
                    cliente=cliente
                )
            else:
                messages.error(request, f"Método de cobro '{metodo_cobro}' no reconocido")
                return redirect("transacciones:venta_moneda")
            
            # Calcular y crear transacción
            tauser_id = request.POST.get("tauser_id")
            tauser = None
            if tauser_id:
                from tauser.models import Tauser
                tauser = Tauser.objects.filter(id=tauser_id).first()
            calculo = calcular_transaccion(
                cliente, 
                TipoTransaccionEnum.VENTA, 
                moneda, 
                monto,
                medio_pago=None,  # Para VENTA no hay medio_pago (el cliente cobra)
                tipo_metodo_override=tipo_metodo_override
            )
            transaccion = crear_transaccion(
                cliente,
                TipoTransaccionEnum.VENTA,
                moneda,
                monto,
                calculo["tasa_aplicada"],
                calculo["comision"],
                calculo["monto_pyg"],
                None,  # medio_pago=None para VENTA
                tauser,
                medio_cobro_obj
            )

            # Preparar datos para el modal
            context = {
                'transaccion': transaccion,
                'metodo_cobro': metodo_cobro,
                'calculo': calculo,
                'cliente': cliente,
                'moneda': moneda,
                'tipo': 'VENTA',
            }
            # Renderizar template con modal de confirmación
            return render(request, "transacciones/transaccion_confirmada.html", context)

        except ValidationError as e:
            messages.error(request, f"Error de validación: {str(e)}")
        except Exception as e:
            logger.exception("Error al crear transacción de venta")
            messages.error(request, f"Error inesperado: {str(e)}")
        
        return redirect("transacciones:venta_moneda")
    
    # GET: mostrar formulario
    # Solo mostrar clientes asociados al usuario operador
    clientes = Cliente.objects.filter(usuarios=request.user).order_by("nombre")
    monedas = Moneda.objects.filter(activa=True).order_by("nombre")
    from tauser.models import Tauser
    tausers = Tauser.objects.filter(estado="activo")
    context = {
        "clientes": clientes,
        "monedas": monedas,
        "tausers": tausers,
    }
    return render(request, "transacciones/venta_moneda.html", context)


@csrf_exempt
def calcular_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cliente = Cliente.objects.get(pk=int(data["cliente"]))
            tipo_str = data["tipo"]
            
            # Convertir el string al enum correspondiente
            if tipo_str == "COMPRA":
                tipo = TipoTransaccionEnum.COMPRA
            elif tipo_str == "VENTA":
                tipo = TipoTransaccionEnum.VENTA
            else:
                return JsonResponse({"error": f"Tipo de transacción inválido: {tipo_str}"}, status=400)
            
            moneda = Moneda.objects.get(pk=int(data["moneda"]))
            monto = Decimal(str(data["monto_operado"]))

            # Obtener método de pago (ID de PaymentMethod o tipo de método)
            medio_pago_id = data.get("medio_pago_id")  # ID del PaymentMethod
            tipo_metodo = data.get("tipo_metodo")  # 'efectivo', 'tarjeta', etc.
            
            # Si viene medio_pago_id, usarlo; si no, usar tipo_metodo como override
            medio_pago = None
            tipo_metodo_override = None
            
            if medio_pago_id:
                medio_pago = medio_pago_id
            elif tipo_metodo:
                tipo_metodo_override = tipo_metodo
            else:
                # Default: efectivo (para compatibilidad con código antiguo)
                tipo_metodo_override = 'efectivo'
            
            calculo = calcular_transaccion(
                cliente, 
                tipo, 
                moneda, 
                monto, 
                medio_pago, 
                tipo_metodo_override
            )
            return JsonResponse(
                {
                    "descuento_pct": str(calculo.get("descuento_pct", "")),
                    "precio_base": str(calculo.get("precio_base", "")),
                    "tasa_aplicada": str(calculo["tasa_aplicada"]),
                    "comision": str(calculo["comision"]),
                    "monto_pyg": str(calculo["monto_pyg"]),
                    "comision_metodo_pago": str(calculo.get("comision_metodo_pago", 0)),
                    "porcentaje_metodo_pago": str(calculo.get("porcentaje_metodo_pago", 0)),
                }
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Método no permitido"}, status=405)


def iniciar_pago_tarjeta(request, pk):
    # Filtrar por clientes del usuario autenticado
    if request.user.is_authenticated:
        tx = get_object_or_404(
            Transaccion.objects.filter(cliente__usuarios=request.user), 
            pk=pk
        )
    else:
        tx = get_object_or_404(Transaccion, pk=pk)

    # Debe estar pendiente
    if str(tx.estado) != str(EstadoTransaccionEnum.PENDIENTE):
        messages.warning(request, "La transacción no está pendiente de pago.")
        return redirect("transacciones:transacciones_list")

    # Solo ciertos tipos (p. ej. COMPRA) van por tarjeta
    if not requiere_pago_tarjeta(tx):
        messages.info(request, "Este tipo de transacción no se paga por tarjeta.")
        return redirect("transacciones:transacciones_list")

    # Verificar si la cotización cambió antes de proceder al pago (solo si está pendiente)
    # Ya validamos arriba que está pendiente, pero por claridad lo dejamos explícito
    verificacion = tx.verificar_cambio_cotizacion()
    if verificacion['ha_cambiado']:
        # Guardar los datos de verificación en la sesión para mostrar en la página de confirmación
        request.session['verificacion_cotizacion'] = {
            'transaccion_id': tx.id,
            'monto_pyg_original': str(verificacion['monto_pyg_original']),
            'monto_pyg_nuevo': str(verificacion['monto_pyg_nuevo']),
            'tasa_original': str(verificacion['tasa_original']),
            'tasa_nueva': str(verificacion['tasa_nueva']),
            'diferencia_pyg': str(verificacion['diferencia_pyg']),
            'diferencia_porcentaje': str(verificacion['diferencia_porcentaje']),
        }
        # Redirigir a una vista de confirmación de cambio de cotización
        return redirect("transacciones:confirmar_cambio_cotizacion", pk=pk)

    try:
        # Guardar el user_id autenticado en la sesión antes de redirigir a Stripe
        if request.user.is_authenticated:
            request.session['stripe_user_id'] = request.user.pk
        url = crear_checkout_para_transaccion(tx)
        return HttpResponseRedirect(url)
    except Exception as e:
        logger.exception("No se pudo iniciar el pago con Stripe para tx #%s", pk)
        messages.error(request, f"No se pudo iniciar el pago: {e}")
        return redirect("transacciones:transacciones_list")


def pago_success(request):

    from django.contrib.auth import get_user_model, login
    session_id = request.GET.get("session_id")
    tx_id = request.GET.get("tx_id")
    info = None

    # Si el usuario no está autenticado pero hay un stripe_user_id en sesión, re-autenticar
    # Pero NO limpiar la sesión, así persiste mientras no se cierre el navegador
    if not request.user.is_authenticated:
        user_id = request.session.get('stripe_user_id')
        if user_id:
            User = get_user_model()
            try:
                user = User.objects.get(pk=user_id)
                login(request, user)
            except User.DoesNotExist:
                pass

    if session_id:
        try:
            info = verificar_pago_stripe(session_id)
        except Exception:
            info = None

    # --- PLAN B: confirmar acá si Stripe ya cobró (idempotente) ---

    if tx_id and info and info.get("payment_status") == "paid":
        try:
            with transaction.atomic():
                tx = Transaccion.objects.select_for_update().get(pk=int(tx_id))

                if str(tx.estado) != str(EstadoTransaccionEnum.PAGADA):
                    # marcar pagada y recalcular ganancia
                    tx.estado = EstadoTransaccionEnum.PAGADA
                    if hasattr(tx, "stripe_payment_intent_id") and info.get("payment_intent"):
                        tx.stripe_payment_intent_id = info["payment_intent"]
                    if hasattr(tx, "stripe_status"):
                        tx.stripe_status = "completed"
                    # Guardar todo junto para que se ejecute la lógica de ganancia
                    tx.save()  # No usar update_fields para que se ejecute el cálculo de ganancia
                    # Ya no se crea el movimiento aquí. Solo se marca como pagada.
                    logger.info(f"[SUCCESS] ✅ tx #{tx.id} marcada PAGADA (movimiento de stock se creará en tauser)")

        except Exception as e:
            logger.exception(f"[SUCCESS] Error en plan B para tx #{tx_id}: {e}")

        # Redirigir a historial de transacciones después de pago exitoso
        messages.success(request, "¡Pago recibido! La transacción fue procesada correctamente.")
        return redirect("transacciones:transacciones_list")

    # Si no es pago exitoso, mostrar la página de éxito (fallback)
    return render(request, "pagos/success.html", {
        "tx_id": tx_id,
        "session_id": session_id,
        "info": info,
    })


def pago_cancel(request):
    """
    Vista de retorno cuando el usuario cancela en Stripe.
    Marca la transacción como 'cancelled' (si existe stripe_status)
    y mantiene el estado de negocio en PENDIENTE.
    """
    tx_id = request.GET.get("tx_id")

    if tx_id:
        try:
            tx = get_object_or_404(Transaccion, id=tx_id)
            if hasattr(tx, "stripe_status"):
                tx.stripe_status = "cancelled"
                tx.save(update_fields=["stripe_status"])
        except Exception as e:
            logger.error("Error al actualizar transacción cancelada #%s: %s", tx_id, str(e))

    messages.info(request, "Pago cancelado. La transacción sigue pendiente.")
    return render(request, "pagos/cancel.html", {"tx_id": tx_id})


# =========================
# Stripe Webhook (Checkout)
# =========================
@csrf_exempt
def stripe_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Método no permitido")

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        logger.warning(f"[STRIPE] Payload inválido: {e}")
        return HttpResponseBadRequest("Payload inválido")
    except stripe.error.SignatureVerificationError as e:
        logger.warning(f"[STRIPE] Firma inválida: {e}")
        return HttpResponseBadRequest("Firma inválida")

    event_type = event.get("type")
    obj = event.get("data", {}).get("object", {})
    logger.info(f"[STRIPE] Webhook recibido: {event_type} id={event.get('id')}")

    # Escuchamos ambos por si el pago es asíncrono
    if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        session = obj
        md = session.get("metadata") or {}
        tx_id = md.get("transaccion_id")

        if not tx_id:
            logger.info("[STRIPE] session sin transaccion_id en metadata")
            return HttpResponse(status=200)

        try:
            with transaction.atomic():
                tx = Transaccion.objects.select_for_update().get(pk=int(tx_id))
                logger.info(f"[STRIPE] Procesando tx #{tx.id} | estado actual: {tx.estado} | tipo: {tx.tipo}")

                # Idempotencia
                if str(tx.estado) == str(EstadoTransaccionEnum.PAGADA):
                    logger.info(f"[STRIPE] tx #{tx.id} ya estaba PAGADA (idempotente)")
                    return HttpResponse(status=200)

                # Guardar info útil

                # Guardar info útil y marcar pagada, recalculando ganancia
                if hasattr(tx, "stripe_payment_intent_id"):
                    tx.stripe_payment_intent_id = session.get("payment_intent")
                if hasattr(tx, "stripe_status"):
                    tx.stripe_status = "completed"
                tx.estado = EstadoTransaccionEnum.PAGADA
                tx.save()  # No usar update_fields para que se ejecute el cálculo de ganancia

                # Ya no se crea el movimiento aquí. Solo se marca como pagada.
                logger.info(f"[STRIPE] ✅ tx #{tx.id} marcada PAGADA (movimiento de stock se creará en tauser)")

        except Transaccion.DoesNotExist:
            logger.warning(f"[STRIPE] Transacción {tx_id} no encontrada")
        except Exception as e:
            logger.exception(f"[STRIPE] Error al confirmar/movimentar tx #{tx_id}: {e}")

    else:
        # Logueá otros eventos para diagnóstico
        logger.info(f"[STRIPE] Evento no manejado: {event_type}")

    return HttpResponse(status=200)


@require_GET
def mostrar_comprobante_sipap(request, pk):
    """
    Vista para mostrar el modal de comprobante SIPAP desde el historial de transacciones.
    Permite al usuario revisar los datos y proceder con el pago.
    Solo funciona para COMPRAS con métodos SIPAP (transferencia/billetera).
    
    Para VENTAS, el pago se procesa automáticamente al confirmar en el terminal Tauser.
    """
    # Filtrar por clientes del usuario autenticado
    if request.user.is_authenticated:
        transaccion = get_object_or_404(
            Transaccion.objects.filter(cliente__usuarios=request.user), 
            pk=pk
        )
    else:
        transaccion = get_object_or_404(Transaccion, pk=pk)
    
    # Verificar que la transacción esté pendiente
    if transaccion.estado != EstadoTransaccionEnum.PENDIENTE:
        messages.warning(request, "Esta transacción ya no está en estado pendiente.")
        return redirect('transacciones:transacciones_list')
    
    # Solo permitir para COMPRAS
    if transaccion.tipo != TipoTransaccionEnum.COMPRA:
        messages.warning(request, "Esta vista solo está disponible para transacciones de compra.")
        return redirect('transacciones:transacciones_list')
    
    # Verificar que sea un pago SIPAP (transferencia o billetera)
    metodo_pago = None
    if transaccion.medio_pago:
        if transaccion.medio_pago.payment_type in ['cuenta_bancaria', 'billetera']:
            metodo_pago = 'transferencia' if transaccion.medio_pago.payment_type == 'cuenta_bancaria' else 'billetera'
    
    if not metodo_pago:
        messages.warning(request, "Esta transacción no utiliza un método de pago SIPAP.")
        return redirect('transacciones:transacciones_list')
    
    # Verificar si la cotización cambió antes de mostrar el comprobante (solo si está pendiente)
    # Ya validamos arriba que está pendiente, pero por claridad lo dejamos explícito
    verificacion = transaccion.verificar_cambio_cotizacion()
    print( verificacion)
    if verificacion['ha_cambiado']:
        # Guardar los datos de verificación en la sesión
        request.session['verificacion_cotizacion'] = {
            'transaccion_id': transaccion.id,
            'monto_pyg_original': str(verificacion['monto_pyg_original']),
            'monto_pyg_nuevo': str(verificacion['monto_pyg_nuevo']),
            'tasa_original': str(verificacion['tasa_original']),
            'tasa_nueva': str(verificacion['tasa_nueva']),
            'diferencia_pyg': str(verificacion['diferencia_pyg']),
            'diferencia_porcentaje': str(verificacion['diferencia_porcentaje']),
        }
        # Redirigir a la vista de confirmación de cambio de cotización
        return redirect("transacciones:confirmar_cambio_cotizacion_sipap", pk=pk)
    
    # Preparar contexto para el template
    context = {
        'transaccion': transaccion,
        'metodo_pago': metodo_pago,
        'cliente': transaccion.cliente,
        'moneda': transaccion.moneda,
        'tipo': 'COMPRA',
        'mostrar_solo_sipap': True,  # Flag para indicar que solo mostramos el modal SIPAP
    }
    
    return render(request, "transacciones/transaccion_confirmada.html", context)


@require_http_methods(["GET", "POST"])
def confirmar_cambio_cotizacion(request, pk):
    """
    Vista para confirmar si el usuario desea proceder con el pago a pesar del cambio de cotización.
    Si acepta, cancela la transacción anterior y crea una nueva con los nuevos valores.
    """
    # Filtrar por clientes del usuario autenticado
    if request.user.is_authenticated:
        tx = get_object_or_404(
            Transaccion.objects.filter(cliente__usuarios=request.user), 
            pk=pk
        )
    else:
        tx = get_object_or_404(Transaccion, pk=pk)
    
    # Verificar que la transacción esté pendiente
    if tx.estado != EstadoTransaccionEnum.PENDIENTE:
        messages.warning(request, "Esta transacción ya no está en estado pendiente.")
        return redirect('transacciones:transacciones_list')
    
    # Obtener los datos de verificación de la sesión
    verificacion_data = request.session.get('verificacion_cotizacion')
    if not verificacion_data or verificacion_data.get('transaccion_id') != tx.id:
        # Si no hay datos en sesión, recalcular
        verificacion = tx.verificar_cambio_cotizacion()
        if not verificacion['ha_cambiado']:
            # Si ya no hay cambio, proceder directamente al pago
            messages.info(request, "La cotización se ha estabilizado. Procediendo al pago.")
            return redirect("transacciones:iniciar_pago_tarjeta", pk=pk)
        
        verificacion_data = {
            'transaccion_id': tx.id,
            'monto_pyg_original': str(verificacion['monto_pyg_original']),
            'monto_pyg_nuevo': str(verificacion['monto_pyg_nuevo']),
            'tasa_original': str(verificacion['tasa_original']),
            'tasa_nueva': str(verificacion['tasa_nueva']),
            'diferencia_pyg': str(verificacion['diferencia_pyg']),
            'diferencia_porcentaje': str(verificacion['diferencia_porcentaje']),
        }
    
    if request.method == "POST":
        accion = request.POST.get("accion")
        
        if accion == "aceptar":
            # El usuario acepta el cambio: cancelar la transacción anterior y crear una nueva
            try:
                with transaction.atomic():
                    # Recalcular con la cotización actual
                    verificacion = tx.verificar_cambio_cotizacion()
                    calculo_nuevo = verificacion['calculo_completo']
                    
                    # Cancelar la transacción anterior
                    cancelar_transaccion(tx)
                    
                    # Crear nueva transacción con los valores actualizados
                    nueva_tx = crear_transaccion(
                        cliente=tx.cliente,
                        tipo=tx.tipo,
                        moneda=tx.moneda,
                        monto_operado=tx.monto_operado,
                        tasa_aplicada=calculo_nuevo['tasa_aplicada'],
                        comision=calculo_nuevo['comision'],
                        monto_pyg=calculo_nuevo['monto_pyg'],
                        medio_pago=tx.medio_pago,
                        tauser=tx.tauser,
                        medio_cobro=tx.medio_cobro,
                    )
                    
                    # Limpiar datos de verificación de la sesión
                    if 'verificacion_cotizacion' in request.session:
                        del request.session['verificacion_cotizacion']
                    
                    messages.success(
                        request, 
                        f"Nueva transacción creada (#{nueva_tx.id}) con la cotización actualizada. La transacción anterior (#{tx.id}) fue cancelada."
                    )
                    
                    # Redirigir al pago de la nueva transacción
                    return redirect("transacciones:iniciar_pago_tarjeta", pk=nueva_tx.id)
                    
            except Exception as e:
                logger.exception(f"Error al recrear transacción: {e}")
                messages.error(request, f"Error al actualizar la transacción: {e}")
                return redirect("transacciones:transacciones_list")
        
        elif accion == "cancelar":
            # El usuario no acepta el cambio: cancelar todo
            try:
                cancelar_transaccion(tx)
                messages.info(request, f"Transacción #{tx.id} cancelada por cambio de cotización.")
            except Exception as e:
                logger.exception(f"Error al cancelar transacción: {e}")
                messages.error(request, f"Error al cancelar la transacción: {e}")
            
            # Limpiar datos de verificación de la sesión
            if 'verificacion_cotizacion' in request.session:
                del request.session['verificacion_cotizacion']
            
            return redirect("transacciones:transacciones_list")
    
    # GET: Mostrar la página de confirmación
    context = {
        'transaccion': tx,
        'verificacion': verificacion_data,
    }
    
    return render(request, "transacciones/confirmar_cambio_cotizacion.html", context)


@require_http_methods(["GET", "POST"])
def confirmar_cambio_cotizacion_sipap(request, pk):
    """
    Vista para confirmar si el usuario desea proceder con el pago SIPAP a pesar del cambio de cotización.
    Si acepta, cancela la transacción anterior y crea una nueva con los nuevos valores.
    """
    # Filtrar por clientes del usuario autenticado
    if request.user.is_authenticated:
        tx = get_object_or_404(
            Transaccion.objects.filter(cliente__usuarios=request.user), 
            pk=pk
        )
    else:
        tx = get_object_or_404(Transaccion, pk=pk)
    
    # Verificar que la transacción esté pendiente
    if tx.estado != EstadoTransaccionEnum.PENDIENTE:
        messages.warning(request, "Esta transacción ya no está en estado pendiente.")
        return redirect('transacciones:transacciones_list')
    
    # Obtener los datos de verificación de la sesión
    verificacion_data = request.session.get('verificacion_cotizacion')
    if not verificacion_data or verificacion_data.get('transaccion_id') != tx.id:
        # Si no hay datos en sesión, recalcular
        verificacion = tx.verificar_cambio_cotizacion()
        if not verificacion['ha_cambiado']:
            # Si ya no hay cambio, proceder directamente al comprobante SIPAP
            messages.info(request, "La cotización se ha estabilizado. Mostrando comprobante de pago.")
            return redirect("transacciones:mostrar_comprobante_sipap", pk=pk)
        
        verificacion_data = {
            'transaccion_id': tx.id,
            'monto_pyg_original': str(verificacion['monto_pyg_original']),
            'monto_pyg_nuevo': str(verificacion['monto_pyg_nuevo']),
            'tasa_original': str(verificacion['tasa_original']),
            'tasa_nueva': str(verificacion['tasa_nueva']),
            'diferencia_pyg': str(verificacion['diferencia_pyg']),
            'diferencia_porcentaje': str(verificacion['diferencia_porcentaje']),
        }
    
    if request.method == "POST":
        accion = request.POST.get("accion")
        
        if accion == "aceptar":
            # El usuario acepta el cambio: cancelar la transacción anterior y crear una nueva
            try:
                with transaction.atomic():
                    # Recalcular con la cotización actual
                    verificacion = tx.verificar_cambio_cotizacion()
                    calculo_nuevo = verificacion['calculo_completo']
                    
                    # Cancelar la transacción anterior
                    cancelar_transaccion(tx)
                    
                    # Crear nueva transacción con los valores actualizados
                    nueva_tx = crear_transaccion(
                        cliente=tx.cliente,
                        tipo=tx.tipo,
                        moneda=tx.moneda,
                        monto_operado=tx.monto_operado,
                        tasa_aplicada=calculo_nuevo['tasa_aplicada'],
                        comision=calculo_nuevo['comision'],
                        monto_pyg=calculo_nuevo['monto_pyg'],
                        medio_pago=tx.medio_pago,
                        tauser=tx.tauser,
                        medio_cobro=tx.medio_cobro,
                    )
                    
                    # Limpiar datos de verificación de la sesión
                    if 'verificacion_cotizacion' in request.session:
                        del request.session['verificacion_cotizacion']
                    
                    messages.success(
                        request, 
                        f"Nueva transacción creada (#{nueva_tx.id}) con la cotización actualizada. La transacción anterior (#{tx.id}) fue cancelada."
                    )
                    
                    # Redirigir al comprobante SIPAP de la nueva transacción
                    return redirect("transacciones:mostrar_comprobante_sipap", pk=nueva_tx.id)
                    
            except Exception as e:
                logger.exception(f"Error al recrear transacción: {e}")
                messages.error(request, f"Error al actualizar la transacción: {e}")
                return redirect("transacciones:transacciones_list")
        
        elif accion == "cancelar":
            # El usuario no acepta el cambio: cancelar todo
            try:
                cancelar_transaccion(tx)
                messages.info(request, f"Transacción #{tx.id} cancelada por cambio de cotización.")
            except Exception as e:
                logger.exception(f"Error al cancelar transacción: {e}")
                messages.error(request, f"Error al cancelar la transacción: {e}")
            
            # Limpiar datos de verificación de la sesión
            if 'verificacion_cotizacion' in request.session:
                del request.session['verificacion_cotizacion']
            
            return redirect("transacciones:transacciones_list")
    
    # GET: Mostrar la página de confirmación
    context = {
        'transaccion': tx,
        'verificacion': verificacion_data,
        'es_sipap': True,  # Flag para indicar que es un pago SIPAP
    }
    
    return render(request, "transacciones/confirmar_cambio_cotizacion.html", context)




