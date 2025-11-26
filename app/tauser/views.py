from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from commons.enums import EstadoTransaccionEnum
from mfa.services import generate_otp
from monedas.models import TasaCambio
from transaccion.models import Transaccion
from transaccion.services import cancelar_transaccion, calcular_transaccion, confirmar_transaccion
from .services import validar_stock_tauser_para_transaccion
from .forms import TauserForm, TauserStockForm
from .models import Tauser, TauserStock, Denominacion
from monedas.models import Moneda
import os, json

def ver_stock_tauser(request, tauser_id):
    tauser = get_object_or_404(Tauser, id=tauser_id)
    monedas = Moneda.objects.all()
    moneda_codigo = request.GET.get('moneda', '')
    stock_qs = TauserStock.objects.filter(tauser=tauser).select_related('denominacion__moneda')
    if moneda_codigo:
        stock_qs = stock_qs.filter(denominacion__moneda__codigo=moneda_codigo)
    stock = stock_qs.order_by('denominacion__moneda__codigo', '-denominacion__type', '-denominacion__value')
    return render(request, 'ver_stock_tauser.html', {
        'tauser': tauser,
        'stock': stock,
        'monedas': monedas,
        'moneda_codigo': moneda_codigo,
    })

def asignar_stock_tauser(request):
    # Leer denominaciones.json
    denominaciones_json_path = os.path.join(os.path.dirname(__file__), 'denominaciones.json')
    with open(denominaciones_json_path, 'r') as f:
        denominaciones_data = json.load(f)

    denominaciones = []
    moneda_seleccionada = None
    if request.method == 'POST':
        moneda_id = request.POST.get('moneda')
        if moneda_id:
            try:
                moneda_seleccionada = Moneda.objects.get(id=moneda_id)
                denominaciones = [d for d in denominaciones_data if d['currency'] == moneda_seleccionada.codigo]
            except Moneda.DoesNotExist:
                denominaciones = []
        form = TauserStockForm(request.POST, denominaciones=denominaciones)
        if 'guardar' in request.POST and form.is_valid():
            tauser = form.cleaned_data['tauser']
            moneda = form.cleaned_data['moneda']
            # Guardar cada denominación
            for d in denominaciones:
                field_name = f"den_{d['type']}_{str(d['value']).replace('.', '_')}"
                cantidad = form.cleaned_data.get(field_name, 0) or 0
                # Buscar o crear Denominacion
                denom_obj, _ = Denominacion.objects.get_or_create(
                    moneda=moneda,
                    value=d['value'],
                    type=d['type']
                )
                TauserStock.objects.update_or_create(
                    tauser=tauser,
                    denominacion=denom_obj,
                    defaults={'quantity': cantidad}
                )
            messages.success(request, 'Stock actualizado correctamente.')
            return redirect('tauser:asignar_stock_tauser')
    else:
        form = TauserStockForm()
    return render(request, 'asignar_stock.html', {
        'form': form,
        'denominaciones': denominaciones,
        'moneda_seleccionada': moneda_seleccionada,
    })

def tramitar_transacciones(request):
    """
    Vista para tramitar transacciones de un cliente activo.
    Permite consultar datos de una transacción por código de verificación.
    """

    tausers_activos = Tauser.objects.filter(estado="activo").order_by('nombre')
    tauser_seleccionado = request.POST.get("tauser_id", "")

    datos_transaccion = None
    error = None
    mensaje = None
    codigo_verificacion = request.POST.get("codigo_verificacion", "").strip().upper()


    if request.method == "POST":
        accion = request.POST.get("accion", "buscar")

        # --- Verificación de MFA solo para la acción de búsqueda ---
        if accion == "buscar":
            mfa_purpose = 'tauser_search_transaction'
            mfa_verified_session_key = f'mfa_verified_{mfa_purpose}'

            if not request.session.get(mfa_verified_session_key):
                error = "Se requiere verificación de seguridad para realizar esta acción."
                return render(request, "tramitar_transacciones.html", {
                    "error": error,
                    "codigo_verificacion": codigo_verificacion,
                    "tausers": tausers_activos,
                    "tauser_seleccionado": tauser_seleccionado,
                })
            
            # Limpiar la marca de sesión para que no se reutilice en futuras búsquedas
            del request.session[mfa_verified_session_key]

        if not codigo_verificacion:
            error = "Debe ingresar el código de verificación de la transacción."
        else:
            try:
                tx = Transaccion.objects.select_related("moneda", "cliente").get(codigo_verificacion=codigo_verificacion)
            except Transaccion.DoesNotExist:
                tx = None
                error = f"No se encontró ninguna transacción con el código '{codigo_verificacion}'."

            if tx:
                # Validación 1: Tauser asignado
                if not tx.tauser:
                    error = "Por favor, seleccione un Tauser válido para esta transacción antes de continuar."
                # Validación de acceso:
                else:
                    # Solo permitir acceso a pagadas, excepto efectivo en pendiente
                    if tx.tipo == 'compra':
                        es_efectivo = tx.medio_pago and tx.medio_pago.payment_type == 'efectivo'
                    else:
                        es_efectivo = tx.medio_cobro and getattr(tx.medio_cobro, 'payment_type', None) == 'efectivo'
                    estado = tx.estado
                    if es_efectivo:
                        if estado == EstadoTransaccionEnum.PENDIENTE:
                            pass  # permitido
                        elif estado == EstadoTransaccionEnum.PAGADA:
                            pass  # permitido
                        else:
                            error = "Solo se pueden tramitar transacciones en efectivo si están pendientes o pagadas."
                    else:
                        if estado == EstadoTransaccionEnum.PAGADA:
                            pass  # permitido
                        else:
                            error = "Solo se pueden tramitar transacciones pagadas, excepto efectivo pendiente."
                if not error:
                    # Buscar tasa actual según tipo de transacción
                    tasa_obj = TasaCambio.objects.filter(moneda=tx.moneda, activa=True).latest("fecha_creacion")
                    if tx.tipo == "compra":
                        # Si la transacción es COMPRA, mostrar la tasa de VENTA
                        tasa_actual = tasa_obj.venta
                    else:
                        # Si la transacción es VENTA, mostrar la tasa de COMPRA
                        tasa_actual = tasa_obj.compra

                    if accion == "buscar" or accion == "validar":
                        # Construir string legible para el medio de pago
                        # Mostrar medio de pago legible o N/A
                        medio_pago_str = 'N/A'
                        if tx.medio_pago:
                            pt = getattr(tx.medio_pago, 'payment_type', None)
                            if pt == 'efectivo':
                                medio_pago_str = 'Efectivo'
                            elif pt == 'tarjeta':
                                medio_pago_str = 'Tarjeta de crédito'
                            elif pt == 'cuenta_bancaria':
                                banco = getattr(tx.medio_pago, 'banco', '')
                                numero = getattr(tx.medio_pago, 'numero_cuenta', '')
                                medio_pago_str = f"Cuenta bancaria ({banco} - {numero})"
                            elif pt == 'billetera':
                                prov = getattr(tx.medio_pago, 'proveedor_billetera', '')
                                email = getattr(tx.medio_pago, 'billetera_email_telefono', '')
                                medio_pago_str = f"Billetera ({prov} - {email})"
                            else:
                                medio_pago_str = str(tx.medio_pago)
                        medio_cobro_str = str(tx.medio_cobro) if tx.medio_cobro else 'N/A'
                        datos_transaccion = {
                            "codigo_verificacion": tx.codigo_verificacion,
                            "id": tx.id,
                            "cliente": tx.cliente,
                            "tipo": tx.get_tipo_display(),
                            "moneda": tx.moneda,
                            "tasa": tx.tasa_aplicada,
                            "tasa_recalculada": tasa_actual,
                            "monto_operado": tx.monto_operado,
                            "monto_pyg": tx.monto_pyg,
                            "comision": tx.comision,
                            "medio_pago": medio_pago_str,
                            "medio_cobro": medio_cobro_str,
                            "fecha": tx.fecha.astimezone(timezone.get_current_timezone()),
                            "fecha_actualizacion": tx.fecha_actualizacion.astimezone(timezone.get_current_timezone()) if hasattr(tx, 'fecha_actualizacion') and tx.fecha_actualizacion else None,
                            "fecha_expiracion": tx.fecha_expiracion.astimezone(timezone.get_current_timezone()) if hasattr(tx, 'fecha_expiracion') and tx.fecha_expiracion else None,
                            "fecha_pago": tx.fecha_pago.astimezone(timezone.get_current_timezone()) if hasattr(tx, 'fecha_pago') and tx.fecha_pago else None,
                            "datos_metodo_pago": tx.datos_metodo_pago if hasattr(tx, 'datos_metodo_pago') else None,
                            "estado": tx.estado,
                        }
                        # Incluir Tauser y su ubicación si existe
                        if tx.tauser:
                            datos_transaccion["tauser"] = {
                                "nombre": tx.tauser.nombre,
                                "ubicacion": tx.tauser.ubicacion,
                            }

                        if accion == "validar":
                            tauser_id = request.POST.get("tauser_id")
                            if not tauser_id:
                                error = "Debe seleccionar un Tauser para validar la transacción."
                            else:
                                resultado = validar_stock_tauser_para_transaccion(
                                    int(tauser_id),
                                    tx.monto_operado,
                                    tx.moneda.id
                                )
                                if resultado['ok']:
                                    mensaje = resultado['mensaje']
                                else:
                                    error = resultado['mensaje']

                    elif accion == "confirmar":
                        try:
                            # Cambiar el estado a 'completada' en vez de 'pagada'
                            tx.estado = EstadoTransaccionEnum.COMPLETADA
                            tx.save()
                            mensaje = f"Transacción #{tx.id} (código: {tx.codigo_verificacion}) completada correctamente."
                        except Exception as e:
                            error = str(e)
                    elif accion == "concluir_venta":
                        # Procesar denominaciones y concluir la venta
                        try:
                            # 1. Parsear denominaciones del POST
                            denominaciones = {}
                            for key, value in request.POST.items():
                                if key.startswith("den_"):
                                    try:
                                        cantidad = int(value)
                                    except (ValueError, TypeError):
                                        cantidad = 0
                                    if cantidad > 0:
                                        # key format: den_{type}_{value}
                                        _, tipo, valor_str = key.split("_", 2)
                                        valor = float(valor_str.replace("_", ".")) if "_" in valor_str else float(valor_str)
                                        denominaciones[(tipo, valor)] = cantidad

                            # 2. Actualizar stock del tauser
                            tauser = tx.tauser
                            if not tauser:
                                raise Exception("No hay TAUser asignado a la transacción.")
                            from .models import Denominacion, TauserStock
                            from monedas.models import Moneda
                            moneda = tx.moneda if tx.tipo == "venta" else Moneda.objects.get(codigo="PYG")
                            for (tipo, valor), cantidad in denominaciones.items():
                                denom_obj, _ = Denominacion.objects.get_or_create(
                                    moneda=moneda,
                                    value=valor,
                                    type=tipo
                                )
                                stock_obj, _ = TauserStock.objects.get_or_create(
                                    tauser=tauser,
                                    denominacion=denom_obj
                                )
                                stock_obj.quantity = stock_obj.quantity + cantidad
                                stock_obj.save()

                            # 3. Completar la transacción
                            tx.estado = EstadoTransaccionEnum.COMPLETADA
                            tx.save()
                            from django.http import JsonResponse
                            return JsonResponse({"success": True})
                        except Exception as e:
                            from django.http import JsonResponse
                            return JsonResponse({"success": False, "error": str(e)})

                    elif accion == "cancelar":
                        try:
                            cancelar_transaccion(tx)
                            mensaje = f"Transacción #{tx.id} (código: {tx.codigo_verificacion}) cancelada correctamente."
                        except Exception as e:
                            error = str(e)

    # Si es venta o compra en efectivo, pasar denominaciones de la moneda
    denominaciones_venta = []
    if datos_transaccion:
        tipo = str(datos_transaccion.get("tipo", "")).lower()
        denominaciones_json_path = os.path.join(os.path.dirname(__file__), 'denominaciones.json')
        with open(denominaciones_json_path, 'r') as f:
            denominaciones_data = json.load(f)
        if tipo == "compra" and datos_transaccion.get("medio_pago") == "Efectivo":
            denominaciones_venta = [d for d in denominaciones_data if d["currency"] == "PYG"]
            denominaciones_venta.sort(key=lambda x: float(x["value"]), reverse=True)
        elif tipo == "venta":
            moneda_codigo = datos_transaccion["moneda"].codigo if hasattr(datos_transaccion["moneda"], "codigo") else str(datos_transaccion["moneda"])
            denominaciones_venta = [d for d in denominaciones_data if d["currency"] == moneda_codigo]
            denominaciones_venta.sort(key=lambda x: float(x["value"]), reverse=True)

    return render(request, "tramitar_transacciones.html", {
        "datos_transaccion": datos_transaccion,
        "error": error,
        "mensaje": mensaje,
        "codigo_verificacion": codigo_verificacion,
        "tausers": tausers_activos,
        "tauser_seleccionado": tauser_seleccionado,
        "denominaciones_venta": denominaciones_venta,
    })


def nuevo_tauser(request):

    mensaje = None
    if request.method == 'POST':
        form = TauserForm(request.POST)
        if form.is_valid():
            form.save()
            mensaje = "Tauser creado exitosamente."
            form = TauserForm()  # Limpiar formulario tras guardar
    else:
        form = TauserForm()

    return render(request, 'nuevo_tauser.html', {
        'form': form,
        'mensaje': mensaje,
    })


def lista_tausers(request):
    estados = Tauser.ESTADOS
    estado = request.GET.get('estado', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    tausers = Tauser.objects.all()
    if estado:
        tausers = tausers.filter(estado=estado)
    if fecha_inicio:
        tausers = tausers.filter(fecha_alta__date__gte=fecha_inicio)
    if fecha_fin:
        tausers = tausers.filter(fecha_alta__date__lte=fecha_fin)
    tausers = tausers.order_by('id')
    return render(request, 'lista_tausers.html', {
        'tausers': tausers,
        'estados': estados,
        'estado_selected': estado,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    })

def editar_estado_tauser(request, tauser_id):
    tauser = get_object_or_404(Tauser, id=tauser_id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Tauser.ESTADOS):
            tauser.estado = nuevo_estado
            tauser.save()
            return redirect('tauser:lista_tausers')
    return render(request, 'editar_estado_tauser.html', {
        'tauser': tauser,
        'estados': Tauser.ESTADOS,
    })
