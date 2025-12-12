import logging
import json
import os
from datetime import timedelta
from decimal import Decimal, ROUND_DOWN

import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction as dj_tx
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

# Redondeo a denominación PYG
from commons.redondeo import redondear_a_denom_py

from clientes.models import LimitePYG, LimiteMoneda, TasaComision
from monedas.models import TasaCambio, PrecioBaseComision
from .models import Transaccion, Movimiento
from tauser.models import ReservaDenominacionTauser, TauserStock, Denominacion, Tauser
from commons.enums import EstadoTransaccionEnum, TipoTransaccionEnum, TipoMovimientoEnum
from pagos.services import PaymentOrchestrator
from pagos.models import PagoPasarela

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


# =========================
# Cálculo de transacción
# =========================
def calcular_transaccion(cliente, tipo, moneda, monto_operado, medio_pago=None, tipo_metodo_override=None):
    """
    Calcula tasa, comisión y monto_pyg, sumando comisión por método de pago.
    
    Args:
        cliente: Cliente que realiza la transacción
        tipo: TipoTransaccionEnum (COMPRA/VENTA)
        moneda: Moneda operada
        monto_operado: Monto en la moneda extranjera
        medio_pago: PaymentMethod o ID (opcional si tipo_metodo_override está definido)
        tipo_metodo_override: str - Tipo de método para casos especiales como 'efectivo' o 'tarjeta'
                               que no requieren PaymentMethod guardado
    """

    from payments.models import ComisionMetodoPago, PaymentMethod

    # Determinar el tipo de método de pago
    tipo_metodo = None
    
    from commons.enums import PaymentTypeEnum
    if tipo_metodo_override:
        # Usar siempre el valor del Enum para mapeo correcto
        if tipo_metodo_override == "transferencia":
            tipo_metodo = PaymentTypeEnum.CUENTA_BANCARIA.value
        elif tipo_metodo_override == "billetera":
            tipo_metodo = PaymentTypeEnum.BILLETERA.value
        elif tipo_metodo_override == "efectivo":
            tipo_metodo = PaymentTypeEnum.EFECTIVO.value
        elif tipo_metodo_override == "tarjeta":
            tipo_metodo = PaymentTypeEnum.TARJETA.value
        else:
            tipo_metodo = tipo_metodo_override
    elif medio_pago is not None:
        payment_method_obj = None
        if isinstance(medio_pago, (int, str)):
            try:
                payment_method_obj = PaymentMethod.objects.get(pk=medio_pago)
            except PaymentMethod.DoesNotExist:
                raise ValidationError("El método de pago seleccionado no existe.")
        else:
            payment_method_obj = medio_pago
        tipo_metodo = payment_method_obj.payment_type
    else:
        tipo_metodo = PaymentTypeEnum.EFECTIVO.value

    # 1) Segmento del cliente (fallback 'MIN')
    segmento = getattr(cliente, "tipo", "MIN").upper()

    # 2) Obtener precio base y comisiones desde PrecioBaseComision
    try:
        pb = PrecioBaseComision.objects.get(moneda=moneda)
    except PrecioBaseComision.DoesNotExist:
        raise ValidationError(f"No hay precio base/comisiones para la moneda {moneda}.")

    # 3) Descuento por segmento (si existe)
    tc = TasaComision.vigente_para_tipo(segmento)
    descuento_pct = Decimal(str(tc.porcentaje)) if tc else Decimal("0")

    monto_operado = Decimal(monto_operado)


    if tipo == TipoTransaccionEnum.VENTA:
        # Comisión de compra
        comision = Decimal(str(pb.comision_compra))
        comision_descuento = comision * descuento_pct / Decimal("100")
        comision_final = comision - comision_descuento
        tasa_aplicada = Decimal(str(pb.precio_base)) - comision_final
        monto_pyg = monto_operado * tasa_aplicada
    elif tipo == TipoTransaccionEnum.COMPRA:
        # Comisión de venta
        comision = Decimal(str(pb.comision_venta))
        comision_descuento = comision * descuento_pct / Decimal("100")
        comision_final = comision - comision_descuento
        tasa_aplicada = Decimal(str(pb.precio_base)) + comision_final
        monto_pyg = monto_operado * tasa_aplicada
    else:
        raise ValidationError("Tipo de transacción inválido.")

    # Comisión por método de pago (obligatorio)
    comision_metodo_pago = Decimal("0")
    porcentaje_metodo_pago = Decimal("0")
    try:
        cmp = ComisionMetodoPago.objects.get(tipo_metodo=tipo_metodo)
        porcentaje_metodo_pago = Decimal(str(cmp.porcentaje_comision))
        comision_metodo_pago = monto_pyg * porcentaje_metodo_pago / Decimal("100")
        if tipo == TipoTransaccionEnum.VENTA:
            monto_pyg -= comision_metodo_pago
        else:
            monto_pyg += comision_metodo_pago
    except ComisionMetodoPago.DoesNotExist:
        pass  # Si no hay comisión configurada, no suma nada

    # Redondear monto_pyg a denominación válida de PYG
    monto_pyg_redondeado = redondear_a_denom_py(monto_pyg)

    return {
        "descuento_pct": descuento_pct,
        "precio_base": Decimal(str(pb.precio_base)),
        "tasa_aplicada": tasa_aplicada,
        "comision": comision,
        "comision_final": comision_final,
        "monto_pyg": monto_pyg_redondeado,
        "comision_metodo_pago": comision_metodo_pago,
        "porcentaje_metodo_pago": porcentaje_metodo_pago,
    }

#creo que esta funcion ya no se usa mas
def obtener_datos_transaccion(transaccion_id):
    try:
        tx = Transaccion.objects.select_related('cliente', 'moneda').get(pk=transaccion_id)
    except Transaccion.DoesNotExist:
        return None

    # Tasa actual
    tasa_actual = (
        TasaCambio.objects.filter(moneda=tx.moneda, activa=True)
        .latest("fecha_creacion")
        .compra  # o venta, según el tipo
    )

    return {
        "id": tx.id,
        "tipo": tx.get_tipo_display(),
        "moneda": tx.moneda,
        "tasa": tx.tasa_aplicada,
        "tasa_recalculada": tasa_actual,
        "monto_operado": tx.monto_operado,
        "monto_pyg": tx.monto_pyg,
        "estado": tx.estado,
    }

#no se usa actualmente
""""
def confirmar_transaccion_con_otp(transaccion, user, raw_code, context_match=None):
    """"""
    Verifica un OTP para la transacción (purpose='transaction_debit') y si es válido
    procede a confirmar la transacción (crear movimiento y marcar PAGADA).

    Esta función no realiza redirecciones ni I/O; lanza ValidationError en caso de fallo.
    """"""
    from django.core.exceptions import ValidationError
    from mfa.services import verify_otp

    # Solo confirmar si está pendiente
    if transaccion.estado != EstadoTransaccionEnum.PENDIENTE:
        raise ValidationError("Solo transacciones pendientes pueden confirmarse.")

    # Verificar OTP
    ok, otp = verify_otp(user, 'transaction_debit', raw_code, context_match=context_match)
    if not ok:
        raise ValidationError('OTP inválido para la transacción.')

    # Si OK, delegar en confirmar_transaccion existente para crear movimiento y marcar PAGADA
    return confirmar_transaccion(transaccion)
"""""

# =========================
# Límites y creación
# =========================
def _check_limit_pyg(cliente, monto_pyg):
    """Límite por operación en PYG."""
    try:
        lim = LimitePYG.objects.get(cliente=cliente)
    except LimitePYG.DoesNotExist:
        return  # sin límite configurado

    if monto_pyg > lim.max_por_operacion:
        raise ValidationError(
            f"Operación en PYG ({monto_pyg}) excede el límite por operación ({lim.max_por_operacion})."
        )


def _sum_operado_en_periodo(cliente, moneda, desde):
    """Suma en MONEDA extranjera (no PYG) desde fecha dada."""
    return (
        Transaccion.objects.filter(
            cliente=cliente,
            moneda=moneda,  # <- FIX: antes usaba 'moneda_operada' (no existe en tu modelo)
            fecha__gte=desde,
            estado__in=[EstadoTransaccionEnum.PENDIENTE, EstadoTransaccionEnum.PAGADA],
        ).aggregate(total=Sum("monto_operado"))["total"]
        or 0
    )


def _check_limit_moneda(cliente, moneda, monto_operado):
    """Límites en la moneda extranjera (por operación y acumulados)."""
    try:
        lim = LimiteMoneda.objects.get(cliente=cliente, moneda=moneda)
    except LimiteMoneda.DoesNotExist:
        return

    if monto_operado > lim.max_por_operacion:
        raise ValidationError(
            f"Operación {monto_operado} {moneda} excede el límite por operación ({lim.max_por_operacion} {moneda})."
        )

    if lim.max_mensual:
        now = timezone.now().astimezone(timezone.get_current_timezone())
        inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        total_mes = _sum_operado_en_periodo(cliente, moneda, inicio_mes)
        if total_mes + monto_operado > lim.max_mensual:
            raise ValidationError(
                f"Límite mensual en {moneda} excedido: mes {total_mes} + {monto_operado} > {lim.max_mensual}."
            )


def validate_limits(cliente, moneda_operada, monto_operado, monto_pyg):
    """
    Validaciones antes de crear transacción:
      1) Límite PYG por operación
      2) Límite por moneda extranjera (operación + mensual)
      3) Límites diarios/mensuales en PYG por tipo de cliente (CLIENT_LIMITS)
    """
    _check_limit_pyg(cliente, monto_pyg)
    _check_limit_moneda(cliente, moneda_operada, monto_operado)

    # límites por tipo de cliente (solo tabla LimiteClienteTipo)
    from clientes.models import LimiteClienteTipo
    tipo_map = {"MIN": "minorista", "CORP": "corporativo", "VIP": "vip"}
    tipo_cliente = tipo_map.get(getattr(cliente, "tipo", "MIN"), "minorista")
    try:
        limites_obj = LimiteClienteTipo.objects.get(tipo_cliente=tipo_cliente)
        limite_diario = Decimal(limites_obj.limite_diario)
        limite_mensual = Decimal(limites_obj.limite_mensual)
    except LimiteClienteTipo.DoesNotExist:
        raise ValidationError("No hay límites configurados para el tipo de cliente: %s" % tipo_cliente)

    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    estados_validos = [EstadoTransaccionEnum.PENDIENTE, EstadoTransaccionEnum.PAGADA]

    total_diario = (
        Transaccion.objects.filter(
            cliente=cliente,
            moneda=moneda_operada,
            fecha__date=hoy,
            estado__in=estados_validos,
        ).aggregate(total=Sum("monto_pyg"))["total"]
        or 0
    )
    total_mensual = (
        Transaccion.objects.filter(
            cliente=cliente,
            moneda=moneda_operada,
            fecha__date__gte=inicio_mes,
            fecha__date__lte=hoy,
            estado__in=estados_validos,
        ).aggregate(total=Sum("monto_pyg"))["total"]
        or 0
    )

    total_diario = Decimal(total_diario)
    total_mensual = Decimal(total_mensual)
    monto_pyg = Decimal(monto_pyg)

    if total_diario + monto_pyg > limite_diario:
        raise ValidationError(
            f"Límite diario alcanzado | total_diario: {total_diario} + monto_pyg: {monto_pyg} > limite_diario: {limite_diario}"
        )
    if total_mensual + monto_pyg > limite_mensual:
        raise ValidationError(
            f"Límite mensual alcanzado | total_mensual: {total_mensual} + monto_pyg: {monto_pyg} > limite_mensual: {limite_mensual}"
        )


def crear_transaccion(
    cliente, tipo, moneda, monto_operado, tasa_aplicada, comision, monto_pyg, medio_pago=None, tauser=None, medio_cobro=None
):
    """
    Crea la transacción en estado PENDIENTE (sin movimientos aún).
    Si es en efectivo y tiene tauser, descuenta stock y crea reservas.
    """
    validate_limits(cliente, moneda, monto_operado, monto_pyg)
    with dj_tx.atomic():
        fecha_expiracion = None
        expiracion_min = getattr(settings, "TRANSACCION_EXPIRACION_MINUTOS", 0)
        if expiracion_min:
            fecha_expiracion = timezone.now() + timedelta(minutes=expiracion_min)

        t = Transaccion.objects.create(
            cliente=cliente,
            moneda=moneda,
            tipo=tipo,
            monto_operado=monto_operado,
            monto_pyg=monto_pyg,
            tasa_aplicada=tasa_aplicada,
            comision=comision,
            medio_pago=medio_pago,
            tauser=tauser,
            medio_cobro=medio_cobro,
            estado=EstadoTransaccionEnum.PENDIENTE,
            fecha_expiracion=fecha_expiracion,
        )
        # En compra: siempre reservar moneda internacional
        # En venta: solo reservar PYG si el medio de cobro es efectivo
        from monedas.models import Moneda
        if tauser:
            if tipo == TipoTransaccionEnum.COMPRA or (hasattr(tipo, 'lower') and tipo.lower() == 'compra'):
                reservar_stock_tauser_para_transaccion(tauser, t, monto_operado, moneda)
            elif tipo == TipoTransaccionEnum.VENTA or (hasattr(tipo, 'lower') and tipo.lower() == 'venta'):
                # Buscar si el medio de cobro es efectivo (usar tipo_medio)
                es_efectivo_cobro = False
                if hasattr(t, 'medio_cobro') and t.medio_cobro and hasattr(t.medio_cobro, 'tipo_medio'):
                    es_efectivo_cobro = t.medio_cobro.tipo_medio == 'efectivo'
                if es_efectivo_cobro:
                    moneda_pyg = Moneda.objects.filter(codigo='PYG').first()
                    if moneda_pyg:
                        reservar_stock_tauser_para_transaccion(tauser, t, monto_pyg, moneda_pyg)
    return t


# --- Lógica de reserva de stock ---
from decimal import Decimal
def reservar_stock_tauser_para_transaccion(tauser, transaccion, monto, moneda):
    """
    Descuenta del stock del tauser las denominaciones necesarias y crea reservas para la transacción.
    """
    # Obtener denominaciones ordenadas de mayor a menor
    denominaciones = Denominacion.objects.filter(moneda=moneda).order_by('-value')
    monto_restante = Decimal(monto)
    from tauser.models import TauserStockMovimiento
    for denom in denominaciones:
        try:
            stock = TauserStock.objects.get(tauser=tauser, denominacion=denom)
        except TauserStock.DoesNotExist:
            continue
        if stock.quantity <= 0:
            continue
        max_billetes = int(monto_restante // denom.value)
        usar = min(max_billetes, stock.quantity)
        if usar > 0:
            # Descontar del stock (reserva lógica, no movimiento definitivo)
            stock.quantity -= usar
            stock.save(update_fields=['quantity'])
            # Crear reserva
            ReservaDenominacionTauser.objects.create(
                tauser=tauser,
                transaccion=transaccion,
                denominacion=denom,
                cantidad=usar
            )
            # NO crear movimiento de stock aquí, solo al completar la transacción
            monto_restante -= denom.value * usar
        if monto_restante <= 0:
            break
    if monto_restante > 0:
        raise ValidationError(f"Stock insuficiente para reservar denominaciones para el monto {monto} {moneda}.")


def _liberar_reservas_tauser(transaccion: Transaccion):
    """Devuelve al stock del tauser las reservas asociadas a la transacción."""
    if not getattr(transaccion, "tauser_id", None):
        return

    from tauser.models import ReservaDenominacionTauser, TauserStock

    reservas = ReservaDenominacionTauser.objects.filter(transaccion=transaccion)
    if not reservas.exists():
        return

    for reserva in reservas:
        stock, _ = TauserStock.objects.get_or_create(
            tauser=reserva.tauser,
            denominacion=reserva.denominacion,
        )
        stock.quantity += reserva.cantidad
        stock.save(update_fields=["quantity"])
    reservas.delete()


# =========================
# Confirmar / Cancelar
# =========================
def procesar_pago_via_sipap(transaccion: Transaccion):
    """
    Procesa el pago/cobro de una transacción a través de SIPAP.
    Funciona tanto para COMPRAS (medio_pago) como para VENTAS (medio_cobro).
    
    Args:
        transaccion: Instancia de Transacción en estado PENDIENTE
    
    Returns:
        tuple: (success: bool, mensaje: str, pago_pasarela: PagoPasarela or None)
    
    Raises:
        ValidationError: Si la transacción no cumple requisitos
    """
    # Validaciones previas
    if transaccion.estado != EstadoTransaccionEnum.PENDIENTE:
        raise ValidationError("Solo transacciones PENDIENTES pueden procesarse por SIPAP.")
    
    # Determinar si es COMPRA o VENTA y obtener los datos correspondientes
    metodo_sipap = None
    datos_sipap = None
    
    # Para COMPRA: usar medio_pago
    if transaccion.tipo == TipoTransaccionEnum.COMPRA:
        if not transaccion.medio_pago:
            raise ValidationError("La transacción de COMPRA debe tener un medio de pago asignado.")
        
        if not transaccion.medio_pago.puede_usar_sipap():
            raise ValidationError(
                f"El método de pago '{transaccion.medio_pago.get_payment_type_display()}' "
                f"no puede procesarse por pasarela SIPAP."
            )
        
        metodo_sipap = transaccion.medio_pago.get_metodo_sipap()
        datos_sipap = transaccion.medio_pago.get_datos_sipap()
        
        if not metodo_sipap or not datos_sipap:
            raise ValidationError(
                f"No se pudieron extraer los datos necesarios del método de pago "
                f"'{transaccion.medio_pago}'."
            )
    
    # Para VENTA: usar medio_cobro (solo transferencia)
    elif transaccion.tipo == TipoTransaccionEnum.VENTA:
        if not transaccion.medio_cobro:
            raise ValidationError("La transacción de VENTA debe tener un medio de cobro asignado.")
        
        if transaccion.medio_cobro.tipo_medio != 'transferencia':
            raise ValidationError(
                f"Solo transferencias bancarias pueden procesarse por SIPAP en ventas."
            )
        
        # Para medio_cobro, generar datos SIPAP manualmente
        metodo_sipap = 'transferencia'
        
        # Generar número de comprobante único
        import hashlib
        from datetime import datetime
        
        cuenta = transaccion.medio_cobro.numero_cuenta or 'CUENTA'
        data = f"{cuenta}{datetime.now().timestamp()}"
        comprobante_hash = hashlib.md5(data.encode()).hexdigest()[:10].upper()
        comprobante = f"TRF{comprobante_hash}"
        
        datos_sipap = {
            'numero_comprobante': comprobante,
        }
    
    # Usar solo monto_pyg para SIPAP
    monto_total = transaccion.monto_pyg

    logger.info(
        f"Procesando {'pago' if transaccion.tipo == TipoTransaccionEnum.COMPRA else 'cobro'} via SIPAP | "
        f"Transacción: {transaccion.uuid} | Método: {metodo_sipap} | Monto: {monto_total} PYG"
    )

    # Procesar pago a través del orquestador
    orchestrator = PaymentOrchestrator()

    try:
        resultado = orchestrator.procesar_pago(
            transaccion=transaccion,
            monto=float(monto_total),
            metodo=metodo_sipap,
            moneda='PYG',
            datos=datos_sipap
        )
        
        # resultado es un dict con 'success', 'pago', 'estado', etc.
        if resultado.get('success') and resultado.get('estado') == 'exito':
            pago = resultado.get('pago')
            logger.info(
                f"{'Pago' if transaccion.tipo == TipoTransaccionEnum.COMPRA else 'Cobro'} EXITOSO via SIPAP | "
                f"Transacción: {transaccion.uuid} | ID Externo: {resultado.get('payment_id')}"
            )
            return (True, f"{'Pago' if transaccion.tipo == TipoTransaccionEnum.COMPRA else 'Cobro'} procesado exitosamente", pago)
        
        else:
            # Pago/cobro fallido o pendiente
            pago = resultado.get('pago')
            estado = resultado.get('estado', 'desconocido')
            
            # Intentar obtener mensaje de error de varias fuentes
            mensaje_error = None
            if pago and hasattr(pago, 'mensaje_error') and pago.mensaje_error:
                mensaje_error = pago.mensaje_error
            elif 'error' in resultado:
                mensaje_error = resultado.get('error')
            else:
                mensaje_error = f"Error al procesar el {'pago' if transaccion.tipo == TipoTransaccionEnum.COMPRA else 'cobro'}. Por favor, verifique los datos e intente nuevamente."
            
            logger.warning(
                f"{'Pago' if transaccion.tipo == TipoTransaccionEnum.COMPRA else 'Cobro'} FALLIDO via SIPAP | "
                f"Transacción: {transaccion.uuid} | "
                f"Estado: {estado} | Mensaje: {mensaje_error}"
            )
            return (False, mensaje_error, pago)
    
    except Exception as e:
        logger.error(
            f"Error al procesar pago via SIPAP | Transacción: {transaccion.uuid} | "
            f"Error: {str(e)}",
            exc_info=True
        )
        return (False, f"Error al procesar pago: {str(e)}", None)


def confirmar_transaccion(transaccion: Transaccion):
    """
    Confirmar transacción.
    - Si el medio_pago puede usar SIPAP → procesa automáticamente por pasarela (COMPRA)
    - Si el medio_cobro es transferencia → procesa por SIPAP (VENTA)
    - Si no → confirmación manual (crea movimiento y marca PAGADA)
    """
    if transaccion.estado != EstadoTransaccionEnum.PENDIENTE:
        raise ValidationError("Solo transacciones pendientes pueden confirmarse.")
    
    # Verificar si debe procesarse por SIPAP
    procesar_sipap = False
    
    # Para COMPRA: verificar medio_pago
    if transaccion.medio_pago and transaccion.medio_pago.puede_usar_sipap():
        procesar_sipap = True
        logger.info(
            f"Transacción {transaccion.uuid} (COMPRA) se procesará por SIPAP "
            f"(método: {transaccion.medio_pago.get_payment_type_display()})"
        )
    
    # Para VENTA: verificar medio_cobro (solo transferencia usa SIPAP)
    elif (transaccion.tipo == TipoTransaccionEnum.VENTA and 
          transaccion.medio_cobro and 
          transaccion.medio_cobro.tipo_medio == 'transferencia'):
        procesar_sipap = True
        logger.info(
            f"Transacción {transaccion.uuid} (VENTA) se procesará por SIPAP "
            f"(método: transferencia)"
        )
    
    if procesar_sipap:
        success, mensaje, pago_pasarela = procesar_pago_via_sipap(transaccion)
        
        if not success:
            raise ValidationError(f"Error al procesar por SIPAP: {mensaje}")
        
        # Si el pago/cobro fue exitoso, continuar con la confirmación
        logger.info(f"Operación exitosa por SIPAP, confirmando transacción {transaccion.uuid}")
    
    # Confirmación manual o después de SIPAP exitoso
    with dj_tx.atomic():
        transaccion.estado = EstadoTransaccionEnum.PAGADA
        transaccion.save()  # Ejecuta lógica de ganancia

        # Mapear a DEBITO/CREDITO en PYG según tipo de operación
        mov_tipo = (
            TipoMovimientoEnum.DEBITO
            if transaccion.tipo == TipoTransaccionEnum.COMPRA
            else TipoMovimientoEnum.CREDITO
        )

        Movimiento.objects.create(
            transaccion=transaccion,
            cliente=transaccion.cliente,
            tipo=mov_tipo,
            monto=transaccion.monto_pyg,
        )

    return transaccion


def cancelar_transaccion(transaccion: Transaccion):
    """Cancela una transacción pendiente. Libera stock reservado si corresponde."""
    if transaccion.estado != EstadoTransaccionEnum.PENDIENTE:
        raise ValidationError("Solo transacciones pendientes pueden cancelarse.")

    _liberar_reservas_tauser(transaccion)

    transaccion.estado = EstadoTransaccionEnum.CANCELADA
    transaccion.save(update_fields=["estado"])
    return transaccion


def expirar_transaccion(transaccion: Transaccion) -> bool:
    """Marca una transacción como anulada por expiración si sigue pendiente."""
    if transaccion.estado != EstadoTransaccionEnum.PENDIENTE:
        return False

    _liberar_reservas_tauser(transaccion)
    transaccion.estado = EstadoTransaccionEnum.ANULADA
    transaccion.save(update_fields=["estado"])
    return True


def expirar_transacciones_pendientes(base_queryset=None) -> int:
    """Expira las transacciones pendientes cuyo plazo venció."""
    qs = base_queryset if base_queryset is not None else Transaccion.objects.all()
    ahora = timezone.now()
    expiradas = 0

    with dj_tx.atomic():
        pendientes = (
            qs.filter(
                estado=EstadoTransaccionEnum.PENDIENTE,
                fecha_expiracion__isnull=False,
                fecha_expiracion__lte=ahora,
            )
            .select_for_update()
        )

        for transaccion in pendientes:
            if expirar_transaccion(transaccion):
                expiradas += 1

    return expiradas


# =========================
# Stripe helpers
# =========================
def requiere_pago_tarjeta(tx: Transaccion) -> bool:
    """
    True cuando el flujo es 'el cliente paga a la casa de cambio en PYG'.
    Por defecto: COMPRA => Stripe OK. VENTA => no Stripe.
    """
    return str(tx.tipo) == str(TipoTransaccionEnum.COMPRA)


def crear_checkout_para_transaccion(tx: Transaccion) -> str:
    """
    Crea una Session de Checkout en PYG (zero-decimal).
    Para COMPRA: cobra el total en PYG (monto_pyg + comisión si corresponde).
    """
    if not requiere_pago_tarjeta(tx):
        raise ValueError("Esta transacción no requiere pago por tarjeta.")

    # Cobrar solo monto_pyg (sin comisión) en Stripe
    monto = Decimal(tx.monto_pyg or 0)
    if monto <= 0:
        raise ValueError("El monto a cobrar debe ser mayor a 0.")

    unit_amount = int(monto.quantize(Decimal("1"), rounding=ROUND_DOWN))  # PYG zero-decimal

    success_url = (
        f"{settings.SITE_URL}"
        f"{reverse('transacciones:pago_success')}"
        f"?session_id={{CHECKOUT_SESSION_ID}}&tx_id={tx.id}"
    )
    cancel_url = (
        f"{settings.SITE_URL}"
        f"{reverse('transacciones:pago_cancel')}"
        f"?tx_id={tx.id}"
    )

    nombre_producto = f"Transacción #{tx.id} - {tx.get_tipo_display()}"
    descripcion = (
        f"{tx.get_tipo_display()} {tx.monto_operado} {tx.moneda.codigo} "
        f"@ {tx.tasa_aplicada} | Cliente: {tx.cliente}"
    )

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "pyg",
                    "unit_amount": unit_amount,
                    "product_data": {"name": nombre_producto, "description": descripcion},
                },
                "quantity": 1,
            }
        ],
        metadata={
            "transaccion_id": str(tx.id),
            "cliente_id": str(tx.cliente_id),
            "tipo": str(tx.tipo),
            "moneda": tx.moneda.codigo,
            "monto_operado": str(tx.monto_operado),
            "tasa": str(tx.tasa_aplicada),
            "monto_pyg": str(tx.monto_pyg),
            "comision": str(tx.comision),
        },
        success_url=success_url,
        cancel_url=cancel_url,
    )

    changed = False
    if hasattr(tx, "stripe_session_id"):
        tx.stripe_session_id = session.id
        changed = True
    if hasattr(tx, "stripe_status"):
        tx.stripe_status = "checkout_created"
        changed = True
    if changed:
        tx.save(
            update_fields=[
                f for f in ["stripe_session_id", "stripe_status"] if hasattr(tx, f)
            ]
        )

    logger.info(f"[STRIPE] Checkout creada para tx #{tx.id}: {session.id}")
    return session.url


def verificar_pago_stripe(session_id: str) -> dict:
    """
    Verifica el estado de un pago en Stripe.
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "payment_status": session.payment_status,  # 'paid', 'unpaid', 'no_payment_required'
            "status": session.status,                  # 'complete', 'open', 'expired'
            "amount_total": session.amount_total,
            "customer_email": (
                session.customer_details.email if getattr(session, "customer_details", None) else None
            ),
            "payment_intent": session.payment_intent,
        }
    except stripe.error.StripeError as e:
        logger.error(f"[STRIPE] Error al verificar pago: {str(e)}")
        raise Exception(f"Error al verificar pago: {str(e)}")
