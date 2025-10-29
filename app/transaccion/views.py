from decimal import Decimal
import json
import logging

import stripe
from django.conf import settings
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

from clientes.models import Cliente
from monedas.models import Moneda

from .forms import TransaccionForm
from .models import Movimiento, Transaccion
from .services import (
    calcular_transaccion,
    confirmar_transaccion,
    cancelar_transaccion,
    crear_transaccion,
    crear_checkout_para_transaccion,
    requiere_pago_tarjeta,
    verificar_pago_stripe,
)
from monedas.models import TasaCambio
from django.contrib import messages
from commons.enums import EstadoTransaccionEnum, TipoTransaccionEnum, TipoMovimientoEnum
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY



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
        "cancelada": EstadoTransaccionEnum.CANCELADA,
        "anulada": EstadoTransaccionEnum.ANULADA,
        "todas": None,
    }
    # default si no viene o no es válido
    if estado_qs not in estados_validos:
        estado_qs = "pendiente"

    transacciones = (
        Transaccion.objects
        .all()
        .select_related("cliente", "moneda")
    )

    # filtro por cliente (si aplica)
    if cliente_id:
        transacciones = transacciones.filter(cliente_id=cliente_id)

    # filtro por estado (si NO es 'todas')
    estado_enum = estados_validos[estado_qs]
    if estado_enum is not None:
        transacciones = transacciones.filter(estado=estado_enum)

    # orden por fecha (default desc)
    if order == "fecha":
        transacciones = transacciones.order_by("fecha" if dir_ == "asc" else "-fecha")
    else:
        transacciones = transacciones.order_by("-fecha")

    # ---- Contadores por estado (respetando cliente si está filtrado) ----
    base = Transaccion.objects.all()
    if cliente_id:
        base = base.filter(cliente_id=cliente_id)

    counts = {
        "pendiente": base.filter(estado=EstadoTransaccionEnum.PENDIENTE).count(),
        "pagada": base.filter(estado=EstadoTransaccionEnum.PAGADA).count(),
        "cancelada": base.filter(estado=EstadoTransaccionEnum.CANCELADA).count(),
        "anulada": base.filter(estado=EstadoTransaccionEnum.ANULADA).count(),
        "todas": base.count(),
    }

    clientes = Cliente.objects.all()
    ctx = {
        "transacciones": transacciones,
        "clientes": clientes,
        "cliente_id": cliente_id,
        "estado_qs": estado_qs,
        "counts": counts,
    }
    return render(request, "transacciones/transacciones_list.html", ctx)


def confirmar_view(request, pk):
    transaccion = get_object_or_404(Transaccion, pk=pk)
    try:
        confirmar_transaccion(transaccion)
        messages.success(request, f"Transacción {transaccion.id} confirmada correctamente.")
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect("transacciones:transacciones_list")


def cancelar_view(request, pk):
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
                calculo = calcular_transaccion(cliente, tipo, moneda_operada, monto_operado)
                transaccion = crear_transaccion(
                    cliente,
                    tipo,
                    moneda_operada,
                    monto_operado,
                    calculo["tasa_aplicada"],
                    calculo["comision"],
                    calculo["monto_pyg"],
                    medio_pago,
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


@csrf_exempt
def calcular_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cliente = Cliente.objects.get(pk=int(data["cliente"]))
            tipo = data["tipo"]
            moneda = Moneda.objects.get(pk=int(data["moneda"]))
            monto = Decimal(str(data["monto_operado"]))

            calculo = calcular_transaccion(cliente, tipo, moneda, monto)
            return JsonResponse(
                {
                    "descuento_pct": str(calculo.get("descuento_pct", "")),
                    "precio_base": str(calculo.get("precio_base", "")),
                    "tasa_aplicada": str(calculo["tasa_aplicada"]),
                    "comision": str(calculo["comision"]),
                    "monto_pyg": str(calculo["monto_pyg"]),
                }
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Método no permitido"}, status=405)


def iniciar_pago_tarjeta(request, pk):
    tx = get_object_or_404(Transaccion, pk=pk)

    # Debe estar pendiente
    if str(tx.estado) != str(EstadoTransaccionEnum.PENDIENTE):
        messages.warning(request, "La transacción no está pendiente de pago.")
        return redirect("transacciones:transacciones_list")

    # Solo ciertos tipos (p. ej. COMPRA) van por tarjeta
    if not requiere_pago_tarjeta(tx):
        messages.info(request, "Este tipo de transacción no se paga por tarjeta.")
        return redirect("transacciones:transacciones_list")

    try:
        url = crear_checkout_para_transaccion(tx)
        return HttpResponseRedirect(url)
    except Exception as e:
        logger.exception("No se pudo iniciar el pago con Stripe para tx #%s", pk)
        messages.error(request, f"No se pudo iniciar el pago: {e}")
        return redirect("transacciones:transacciones_list")


def pago_success(request):
    session_id = request.GET.get("session_id")
    tx_id = request.GET.get("tx_id")
    info = None

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
                    # marcar pagada
                    tx.estado = EstadoTransaccionEnum.PAGADA
                    # opcional: guardar payment_intent / status si tenés esos campos
                    if hasattr(tx, "stripe_payment_intent_id") and info.get("payment_intent"):
                        tx.stripe_payment_intent_id = info["payment_intent"]
                    if hasattr(tx, "stripe_status"):
                        tx.stripe_status = "completed"
                    campos = ["estado"]
                    if hasattr(tx, "stripe_payment_intent_id") and info.get("payment_intent"):
                        campos.append("stripe_payment_intent_id")
                    if hasattr(tx, "stripe_status"):
                        campos.append("stripe_status")
                    tx.save(update_fields=campos)

                    # crear movimiento coherente con el tipo
                    if str(tx.tipo) == str(TipoTransaccionEnum.COMPRA):
                        mov_tipo = TipoMovimientoEnum.DEBITO
                        monto_mov = (tx.monto_pyg or 0) + (tx.comision or 0)
                    else:
                        mov_tipo = TipoMovimientoEnum.CREDITO
                        monto_mov = tx.monto_pyg

                    # idempotencia simple: no crear duplicados si ya existe
                    if not Movimiento.objects.filter(transaccion=tx).exists():
                        Movimiento.objects.create(
                            transaccion=tx,
                            cliente=tx.cliente,
                            medio=None,
                            tipo=mov_tipo,
                            monto=monto_mov,
                        )
        except Exception as e:
            logger.exception(f"[SUCCESS] Error en plan B para tx #{tx_id}: {e}")

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
                updates = {}
                if hasattr(tx, "stripe_payment_intent_id"):
                    updates["stripe_payment_intent_id"] = session.get("payment_intent")
                if hasattr(tx, "stripe_status"):
                    updates["stripe_status"] = "completed"
                if updates:
                    for k, v in updates.items():
                        setattr(tx, k, v)
                    tx.save(update_fields=list(updates.keys()))

                # Confirmar negocio
                tx.estado = EstadoTransaccionEnum.PAGADA
                tx.save(update_fields=["estado"])

                # Movimiento en caja PYG coherente con el tipo
                if str(tx.tipo) == str(TipoTransaccionEnum.COMPRA):
                    mov_tipo = TipoMovimientoEnum.DEBITO
                    monto_mov = (tx.monto_pyg or 0) + (tx.comision or 0)  # si cobrás comisión por Stripe
                else:  # VENTA
                    mov_tipo = TipoMovimientoEnum.CREDITO
                    monto_mov = tx.monto_pyg  # normalmente no cobrás por Stripe en VENTA

                Movimiento.objects.create(
                    transaccion=tx,
                    cliente=tx.cliente,
                    medio=None,
                    tipo=mov_tipo,
                    monto=monto_mov,
                )
                logger.info(f"[STRIPE] ✅ tx #{tx.id} marcada PAGADA y movimiento {mov_tipo} creado por ₲ {monto_mov}")

        except Transaccion.DoesNotExist:
            logger.warning(f"[STRIPE] Transacción {tx_id} no encontrada")
        except Exception as e:
            logger.exception(f"[STRIPE] Error al confirmar/movimentar tx #{tx_id}: {e}")

    else:
        # Logueá otros eventos para diagnóstico
        logger.info(f"[STRIPE] Evento no manejado: {event_type}")

    return HttpResponse(status=200)

    