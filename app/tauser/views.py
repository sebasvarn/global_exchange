import uuid
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import JsonResponse
from facturacion.models import FacturaElectronica
from commons.enums import EstadoTransaccionEnum, TipoTransaccionEnum
from mfa.services import generate_otp
from monedas.models import TasaCambio, Moneda
from transaccion.models import Transaccion
from transaccion.services import cancelar_transaccion, calcular_transaccion, confirmar_transaccion
from .services import validar_stock_tauser_para_transaccion
from .forms import TauserForm, TauserStockForm
from .models import Tauser, TauserStock, Denominacion, TauserStockMovimiento, ReservaDenominacionTauser
import os
import json
from django.db import models
def movimientos_tauser(request, tauser_id):
    """
    Muestra los movimientos de stock de un Tauser, permitiendo filtrar por moneda, tipo y fechas.
    Calcula sumas de entradas y salidas, y muestra información de usuario y cliente asociada a cada movimiento.
    """
    tausers = Tauser.objects.all().order_by('nombre')
    tauser_id_selected = request.GET.get('tauser') or tauser_id
    tauser = get_object_or_404(Tauser, id=tauser_id_selected)
    movimientos = TauserStockMovimiento.objects.filter(tauser=tauser).select_related('denominacion', 'denominacion__moneda', 'transaccion').order_by('-fecha')
    monedas = Moneda.objects.all()
    moneda_codigo = request.GET.get('moneda', '')
    tipo_movimiento = request.GET.get('tipo', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    if moneda_codigo:
        movimientos = movimientos.filter(denominacion__moneda__codigo=moneda_codigo)
    if tipo_movimiento:
        movimientos = movimientos.filter(tipo_movimiento=tipo_movimiento)
    if fecha_inicio:
        movimientos = movimientos.filter(fecha__date__gte=fecha_inicio)
    if fecha_fin:
        movimientos = movimientos.filter(fecha__date__lte=fecha_fin)

    # Calcular sumas de entrada y salida para la moneda filtrada
    suma_entrada_valor = 0.0
    suma_salida_valor = 0.0
    for mov in movimientos:
        total_valor = float(mov.denominacion.value) * mov.cantidad
        if mov.tipo_movimiento == 'entrada':
            suma_entrada_valor += total_valor
        elif mov.tipo_movimiento == 'salida':
            suma_salida_valor += total_valor

    # Prepara un diccionario con usuario y cliente para cada movimiento
    movimientos_info = []
    for mov in movimientos:
        usuario = None
        cliente = None
        if mov.transaccion:
            cliente = mov.transaccion.cliente
            # Busca el primer usuario asociado al cliente (si existe)
            usuario = cliente.usuarios.first() if hasattr(cliente, 'usuarios') else None
        movimientos_info.append({
            'mov': mov,
            'usuario': usuario,
            'cliente': cliente,
        })
    return render(request, 'movimientos_tauser.html', {
        'tauser': tauser,
        'tausers': tausers,
        'movimientos_info': movimientos_info,
        'monedas': monedas,
        'moneda_codigo': moneda_codigo,
        'tauser_id_selected': int(tauser_id_selected),
        'tipo_movimiento': tipo_movimiento,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'suma_entrada_valor': suma_entrada_valor,
        'suma_salida_valor': suma_salida_valor,
    })


def ver_stock_tauser(request, tauser_id):
    """
    Muestra el stock detallado de un Tauser, filtrando por moneda si se especifica en el querystring.
    """
    tauser = get_object_or_404(Tauser, id=tauser_id)
    monedas = Moneda.objects.all()

    moneda_codigo = request.GET.get('moneda', '')
    stock_qs = TauserStock.objects.filter(
        tauser=tauser
    ).select_related('denominacion__moneda')

    if moneda_codigo:
        stock_qs = stock_qs.filter(denominacion__moneda__codigo=moneda_codigo)

    stock = stock_qs.order_by(
        'denominacion__moneda__codigo',
        '-denominacion__type',
        '-denominacion__value'
    )

    return render(request, 'ver_stock_tauser.html', {
        'tauser': tauser,
        'stock': stock,
        'monedas': monedas,
        'moneda_codigo': moneda_codigo,
    })


def asignar_stock_tauser(request):
    """
    Permite asignar o actualizar el stock de divisas del Tauser, basado en las denominaciones definidas en denominaciones.json.
    Procesa el formulario para agregar o quitar cantidades de cada denominación.
    """
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
                denominaciones = [
                    d for d in denominaciones_data
                    if d['currency'] == moneda_seleccionada.codigo
                ]
            except Moneda.DoesNotExist:
                denominaciones = []

        form = TauserStockForm(request.POST, denominaciones=denominaciones)

        if 'guardar' in request.POST and form.is_valid():
            tauser = form.cleaned_data['tauser']
            moneda = form.cleaned_data['moneda']
            operacion = form.cleaned_data['operacion']
            from .models import TauserStockMovimiento
            hubo_error = False
            for d in denominaciones:
                field_name = f"den_{d['type']}_{str(d['value']).replace('.', '_')}"
                cantidad = form.cleaned_data.get(field_name, 0) or 0
                if cantidad == 0:
                    continue
                denom_obj, _ = Denominacion.objects.get_or_create(
                    moneda=moneda,
                    value=d['value'],
                    type=d['type']
                )
                stock_obj, created = TauserStock.objects.get_or_create(
                    tauser=tauser,
                    denominacion=denom_obj,
                    defaults={'quantity': 0}
                )
                if operacion == 'agregar':
                    stock_obj.quantity += cantidad
                    tipo_mov = TauserStockMovimiento.ENTRADA
                else:
                    if cantidad > stock_obj.quantity:
                        messages.error(
                            request,
                            f"No hay suficiente stock de {denom_obj} para descontar {cantidad}. Disponible: {stock_obj.quantity}."
                        )
                        hubo_error = True
                        continue
                    stock_obj.quantity -= cantidad
                    tipo_mov = TauserStockMovimiento.SALIDA
                stock_obj.save()
                TauserStockMovimiento.objects.create(
                    tauser=tauser,
                    denominacion=denom_obj,
                    cantidad=cantidad,
                    tipo_movimiento=tipo_mov
                )
            if not hubo_error:
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
    Permite tramitar transacciones de clientes activos mediante código de verificación.
    Incluye validación MFA, consulta, validación de stock, confirmación, conclusión de venta, generación de factura y cancelación.
    """

    tausers_activos = Tauser.objects.filter(estado="activo").order_by('nombre')
    tauser_seleccionado = request.POST.get("tauser_id", "")

    datos_transaccion = None
    error = None
    mensaje = None
    codigo_verificacion = request.POST.get("codigo_verificacion", "").strip().upper()


    if request.method == "POST":
        accion = request.POST.get("accion", "buscar")
        generar_factura = request.POST.get("generar_factura", "no") == "si"  # NUEVO
        cambio_cotizacion_aceptado = request.POST.get("cambio_cotizacion_aceptado") == "si"

        # Validación de código primero (antes de MFA)
        if not codigo_verificacion:
            error = "Debe ingresar el código de verificación de la transacción."
        else:
            try:
                tx = Transaccion.objects.select_related("moneda", "cliente").get(
                    codigo_verificacion=codigo_verificacion
                )
            except Transaccion.DoesNotExist:
                tx = None
                error = f"No se encontró ninguna transacción con el código '{codigo_verificacion}'."

            if tx:
                # Obtener clave de sesión para este código de verificación
                session_key_cotizacion = f'cotizacion_aceptada_{codigo_verificacion}'
                cotizacion_ya_aceptada = request.session.get(session_key_cotizacion, False)
                
                # Verificar cambio de cotización ANTES de solicitar MFA (solo si está pendiente y no fue aceptado previamente)
                if accion == "buscar" and not cambio_cotizacion_aceptado and not cotizacion_ya_aceptada and tx.estado == EstadoTransaccionEnum.PENDIENTE:
                    verificacion = tx.verificar_cambio_cotizacion()
                    if verificacion['ha_cambiado']:
                        # Guardar en sesión para mostrar en el template
                        request.session['verificacion_cotizacion_temp'] = {
                            'codigo': codigo_verificacion,
                            'ha_cambiado': True,
                            'monto_pyg_original': str(verificacion['monto_pyg_original']),
                            'monto_pyg_nuevo': str(verificacion['monto_pyg_nuevo']),
                            'tasa_original': str(verificacion['tasa_original']),
                            'tasa_nueva': str(verificacion['tasa_nueva']),
                            'diferencia_pyg': str(verificacion['diferencia_pyg']),
                            'diferencia_porcentaje': str(verificacion['diferencia_porcentaje']),
                        }
                        # Retornar para mostrar el modal de confirmación
                        return render(request, "tramitar_transacciones.html", {
                            "codigo_verificacion": codigo_verificacion,
                            "tausers": tausers_activos,
                            "tauser_seleccionado": tauser_seleccionado,
                            "verificacion_cotizacion_previa": request.session['verificacion_cotizacion_temp'],
                            "mostrar_modal_cotizacion": True,
                        })
                
                # Si el usuario aceptó el cambio, actualizar la transacción con los nuevos valores
                if accion == "buscar" and cambio_cotizacion_aceptado and not cotizacion_ya_aceptada:
                    verificacion = tx.verificar_cambio_cotizacion()
                    if verificacion['ha_cambiado']:
                        calculo_nuevo = verificacion['calculo_completo']
                        tx.tasa_aplicada = calculo_nuevo['tasa_aplicada']
                        tx.comision = calculo_nuevo['comision']
                        tx.monto_pyg = calculo_nuevo['monto_pyg']
                        tx.save(update_fields=['tasa_aplicada', 'comision', 'monto_pyg'])
                        # Marcar en sesión que ya se aceptó el cambio para este código
                        request.session[session_key_cotizacion] = True

                # === MFA obligatorio para búsqueda (después de aceptar cambio de cotización) ===
                if accion == "buscar":
                    mfa_purpose = 'tauser_search_transaction'
                    mfa_verified_session_key = f'mfa_verified_{mfa_purpose}'

                    if not request.session.get(mfa_verified_session_key):
                        return render(request, "tramitar_transacciones.html", {
                            "codigo_verificacion": codigo_verificacion,
                            "tausers": tausers_activos,
                            "tauser_seleccionado": tauser_seleccionado,
                        })
                    # Limpiar la verificación después de usarla
                    del request.session[mfa_verified_session_key]
                    # Limpiar verificación temporal de la sesión
                    if 'verificacion_cotizacion_temp' in request.session:
                        del request.session['verificacion_cotizacion_temp']

            if tx:
                # Si es venta y pendiente, permitir siempre
                if str(tx.tipo).lower() == 'venta' and tx.estado == EstadoTransaccionEnum.PENDIENTE:
                    pass  # permitido
                else:
                    # Validación TAUser asignado
                    if not tx.tauser:
                        error = "Por favor, seleccione un Tauser válido para esta transacción antes de continuar."
                    else:
                        # Solo permitir acceso a pagadas, excepto efectivo en pendiente
                        if str(tx.tipo).lower() == 'compra':
                            es_efectivo = tx.medio_pago and tx.medio_pago.payment_type == 'efectivo'
                        else:
                            es_efectivo = tx.medio_cobro and getattr(tx.medio_cobro, 'payment_type', None) == 'efectivo'

                        estado = tx.estado

                        if es_efectivo:
                            if estado in (EstadoTransaccionEnum.PENDIENTE, EstadoTransaccionEnum.PAGADA):
                                pass
                            else:
                                error = "Solo se pueden tramitar transacciones en efectivo si están pendientes o pagadas."
                        else:
                            if estado == EstadoTransaccionEnum.PAGADA:
                                pass
                            else:
                                error = "Solo se pueden tramitar transacciones pagadas, excepto efectivo pendiente."

                # Si todo OK
                if not error:
                    # Buscar tasa actual según tipo de transacción
                    tasa_obj = TasaCambio.objects.filter(moneda=tx.moneda, activa=True).latest("fecha_creacion")
                    if str(tx.tipo).lower() == "compra":
                        # Si la transacción es COMPRA, mostrar la tasa de VENTA
                        tasa_actual = tasa_obj.venta
                    else:
                        # Si la transacción es VENTA, mostrar la tasa de COMPRA
                        tasa_actual = tasa_obj.compra

                    # Verificar cambio de cotización
                    verificacion_cotizacion = None
                    if accion in ["buscar", "validar"]:
                        verificacion = tx.verificar_cambio_cotizacion()
                        if verificacion['ha_cambiado']:
                            verificacion_cotizacion = {
                                'ha_cambiado': True,
                                'monto_pyg_original': verificacion['monto_pyg_original'],
                                'monto_pyg_nuevo': verificacion['monto_pyg_nuevo'],
                                'tasa_original': verificacion['tasa_original'],
                                'tasa_nueva': verificacion['tasa_nueva'],
                                'diferencia_pyg': verificacion['diferencia_pyg'],
                                'diferencia_porcentaje': verificacion['diferencia_porcentaje'],
                            }

                    # Construcción info transacción
                    if accion in ["buscar", "validar"]:
                        medio_pago_str = "N/A"

                        if tx.medio_pago:
                            pt = getattr(tx.medio_pago, 'payment_type', None)
                            if pt == 'efectivo':
                                medio_pago_str = "Efectivo"
                            elif pt == 'tarjeta':
                                medio_pago_str = "Tarjeta de crédito"
                            elif pt == 'cuenta_bancaria':
                                medio_pago_str = f"Cuenta bancaria ({tx.medio_pago.banco} - {tx.medio_pago.numero_cuenta})"
                            elif pt == 'billetera':
                                medio_pago_str = f"Billetera ({tx.medio_pago.proveedor_billetera} - {tx.medio_pago.billetera_email_telefono})"
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
                            "fecha_actualizacion": getattr(tx, 'fecha_actualizacion', None),
                            "fecha_expiracion": getattr(tx, 'fecha_expiracion', None),
                            "fecha_pago": getattr(tx, 'fecha_pago', None),
                            "datos_metodo_pago": getattr(tx, 'datos_metodo_pago', None),
                            "estado": tx.estado,
                            "factura_electronica": hasattr(tx, 'factura_electronica'),
                        }

                        if tx.tauser:
                            datos_transaccion["tauser"] = {
                                "nombre": tx.tauser.nombre,
                                "ubicacion": tx.tauser.ubicacion,
                            }

                        # Validar stock
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
                        # Verificar si la cotización cambió antes de confirmar
                        verificacion = tx.verificar_cambio_cotizacion()
                        if verificacion['ha_cambiado']:
                            # Solicitar confirmación del usuario sobre el cambio
                            confirmar_cambio = request.POST.get("confirmar_cambio_cotizacion")
                            if confirmar_cambio != "si":
                                # Mostrar alerta de cambio y solicitar confirmación
                                error = f"La cotización ha cambiado. Monto original: {verificacion['monto_pyg_original']} PYG, Nuevo monto: {verificacion['monto_pyg_nuevo']} PYG. Diferencia: {verificacion['diferencia_pyg']} PYG ({verificacion['diferencia_porcentaje']:.2f}%). Para continuar, debe aceptar el cambio."
                                verificacion_cotizacion = {
                                    'ha_cambiado': True,
                                    'monto_pyg_original': verificacion['monto_pyg_original'],
                                    'monto_pyg_nuevo': verificacion['monto_pyg_nuevo'],
                                    'tasa_original': verificacion['tasa_original'],
                                    'tasa_nueva': verificacion['tasa_nueva'],
                                    'diferencia_pyg': verificacion['diferencia_pyg'],
                                    'diferencia_porcentaje': verificacion['diferencia_porcentaje'],
                                    'requiere_confirmacion': True,
                                }
                                # Reconstruir datos_transaccion para mostrar en el template
                                medio_pago_str = "N/A"
                                if tx.medio_pago:
                                    pt = getattr(tx.medio_pago, 'payment_type', None)
                                    if pt == 'efectivo':
                                        medio_pago_str = "Efectivo"
                                    elif pt == 'tarjeta':
                                        medio_pago_str = "Tarjeta de crédito"
                                    elif pt == 'cuenta_bancaria':
                                        medio_pago_str = f"Cuenta bancaria ({tx.medio_pago.banco} - {tx.medio_pago.numero_cuenta})"
                                    elif pt == 'billetera':
                                        medio_pago_str = f"Billetera ({tx.medio_pago.proveedor_billetera} - {tx.medio_pago.billetera_email_telefono})"
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
                                    "fecha_actualizacion": getattr(tx, 'fecha_actualizacion', None),
                                    "fecha_expiracion": getattr(tx, 'fecha_expiracion', None),
                                    "fecha_pago": getattr(tx, 'fecha_pago', None),
                                    "datos_metodo_pago": getattr(tx, 'datos_metodo_pago', None),
                                    "estado": tx.estado,
                                }
                                if tx.tauser:
                                    datos_transaccion["tauser"] = {
                                        "nombre": tx.tauser.nombre,
                                        "ubicacion": tx.tauser.ubicacion,
                                    }
                        
                        if not error:
                            try:
                                # Si se aceptó el cambio, actualizar la transacción con los nuevos valores
                                if verificacion['ha_cambiado'] and request.POST.get("confirmar_cambio_cotizacion") == "si":
                                    calculo_nuevo = verificacion['calculo_completo']
                                    tx.tasa_aplicada = calculo_nuevo['tasa_aplicada']
                                    tx.comision = calculo_nuevo['comision']
                                    tx.monto_pyg = calculo_nuevo['monto_pyg']
                                
                                # Marcar como COMPLETADA
                                tx.estado = EstadoTransaccionEnum.COMPLETADA
                                tx.save()

                                # Registrar movimiento de stock del tauser (igual que en concluir_venta, pero sin denominaciones del POST)
                                tauser = tx.tauser
                                if not tauser:
                                    raise Exception("No hay TAUser asignado a la transacción.")
                                from .models import Denominacion, TauserStock, TauserStockMovimiento, ReservaDenominacionTauser
                                from monedas.models import Moneda

                                tipo_tx = str(tx.tipo).lower()
                                medio_pago = getattr(tx, 'medio_pago', None)
                                medio_cobro = getattr(tx, 'medio_cobro', None)
                                pago_efectivo = getattr(medio_pago, 'payment_type', None) == 'efectivo'
                                cobro_efectivo = getattr(medio_cobro, 'payment_type', None) == 'efectivo'

                                # Variable para mensajes adicionales
                                mensaje_adicional = ""

                                # --- VENTA ---
                                if tipo_tx == "venta":
                                    # OMITIDO: procesamiento SIPAP para transferencias/billetera
                                    # Si NO es efectivo (transferencia/billetera), omitir SIPAP temporalmente
                                    # if not cobro_efectivo:
                                    #     from transaccion.services import procesar_pago_via_sipap
                                    #     try:
                                    #         success, mensaje_sipap, pago_obj = procesar_pago_via_sipap(tx)
                                    #         if not success:
                                    #             raise Exception(f"Error al procesar transferencia SIPAP: {mensaje_sipap}")
                                    #         mensaje_adicional = " Transferencia SIPAP procesada exitosamente."
                                    #     except Exception as e:
                                    #         raise Exception(f"Error al procesar transferencia SIPAP: {str(e)}")
                                    
                                    # Marcar como COMPLETADA
                                    tx.estado = EstadoTransaccionEnum.COMPLETADA
                                    tx.save()
                                    
                                    # SALIDA solo si el cobro es efectivo (entrega PYG)
                                    if cobro_efectivo:
                                        moneda_pyg = Moneda.objects.get(codigo="PYG")
                                        reservas = ReservaDenominacionTauser.objects.filter(transaccion=tx)
                                        for reserva in reservas:
                                            if reserva.denominacion.moneda == moneda_pyg:
                                                TauserStockMovimiento.objects.create(
                                                    tauser=reserva.tauser,
                                                    denominacion=reserva.denominacion,
                                                    cantidad=reserva.cantidad,
                                                    tipo_movimiento=TauserStockMovimiento.SALIDA,
                                                    transaccion=tx
                                                )
                                # --- COMPRA ---
                                elif tipo_tx == "compra":
                                    # SALIDA siempre (entrega moneda extranjera)
                                    reservas = ReservaDenominacionTauser.objects.filter(transaccion=tx)
                                    if not reservas.exists():
                                        import logging
                                        logging.warning(f"[TAUSER] No se encontraron reservas para registrar salida en compra. Transacción: {tx.id}")
                                    for reserva in reservas:
                                        TauserStockMovimiento.objects.create(
                                            tauser=reserva.tauser,
                                            denominacion=reserva.denominacion,
                                            cantidad=reserva.cantidad,
                                            tipo_movimiento=TauserStockMovimiento.SALIDA,
                                            transaccion=tx
                                        )

                                # FACTURA
                                if generar_factura:
                                    from facturacion.services import ServicioFacturacion

                                    # Asignar datos fiscales si no existen
                                    if not hasattr(tx, 'datos_fiscales') or not tx.datos_fiscales:
                                        tx.datos_fiscales = {
                                            "nombre": request.POST.get("fact_nombre") or "SIN NOMBRE",
                                            "cedula": request.POST.get("fact_cedula") or "",
                                            "ruc": request.POST.get("fact_ruc") or "",
                                            "dv": request.POST.get("fact_dv") or "",
                                            "email": request.POST.get("fact_email") or "",
                                            "direccion": request.POST.get("fact_direccion") or "",
                                        }
                                        tx.save()

                                    if hasattr(tx, 'factura_electronica'):
                                        mensaje = f"Transacción #{tx.id} completada. Ya existe factura: {tx.factura_electronica.cdc}{mensaje_adicional}"
                                    else:
                                        servicio = ServicioFacturacion()
                                        resultado = servicio.generar_factura(tx)

                                        if resultado['success']:
                                            mensaje = f"Transacción #{tx.id} completada y factura generada exitosamente!{mensaje_adicional}"
                                        else:
                                            mensaje = f"Transacción #{tx.id} completada, pero hubo error en la factura: {resultado['error']}{mensaje_adicional}"
                                else:
                                    mensaje = f"Transacción #{tx.id} (código: {tx.codigo_verificacion}) completada correctamente.{mensaje_adicional}"
                                
                                # Limpiar bandera de cotización aceptada de la sesión
                                session_key_cotizacion = f'cotizacion_aceptada_{codigo_verificacion}'
                                if session_key_cotizacion in request.session:
                                    del request.session[session_key_cotizacion]
                                
                                # Retornar JSON si es una petición AJAX
                                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/x-www-form-urlencoded':
                                    return JsonResponse({
                                        "success": True,
                                        "mensaje": mensaje
                                    })

                            except Exception as e:
                                error = str(e)
                                # Retornar JSON de error si es AJAX
                                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/x-www-form-urlencoded':
                                    return JsonResponse({
                                        "success": False,
                                        "error": error
                                    })

                    elif accion == "concluir_venta":
                        # Verificar si la cotización cambió antes de concluir la venta
                        verificacion = tx.verificar_cambio_cotizacion()
                        if verificacion['ha_cambiado']:
                            confirmar_cambio = request.POST.get("confirmar_cambio_cotizacion")
                            if confirmar_cambio != "si":
                                # Retornar error JSON solicitando confirmación
                                return JsonResponse({
                                    "success": False,
                                    "cambio_cotizacion": True,
                                    "error": f"La cotización ha cambiado. Monto original: {verificacion['monto_pyg_original']} PYG, Nuevo monto: {verificacion['monto_pyg_nuevo']} PYG. Diferencia: {verificacion['diferencia_pyg']} PYG ({verificacion['diferencia_porcentaje']:.2f}%).",
                                    "verificacion": {
                                        'monto_pyg_original': str(verificacion['monto_pyg_original']),
                                        'monto_pyg_nuevo': str(verificacion['monto_pyg_nuevo']),
                                        'tasa_original': str(verificacion['tasa_original']),
                                        'tasa_nueva': str(verificacion['tasa_nueva']),
                                        'diferencia_pyg': str(verificacion['diferencia_pyg']),
                                        'diferencia_porcentaje': str(verificacion['diferencia_porcentaje']),
                                    }
                                })
                        
                        try:
                            # Si se aceptó el cambio, actualizar la transacción con los nuevos valores
                            if verificacion['ha_cambiado'] and request.POST.get("confirmar_cambio_cotizacion") == "si":
                                calculo_nuevo = verificacion['calculo_completo']
                                tx.tasa_aplicada = calculo_nuevo['tasa_aplicada']
                                tx.comision = calculo_nuevo['comision']
                                tx.monto_pyg = calculo_nuevo['monto_pyg']
                                tx.save()
                            
                            # ===========================
                            # 1. Procesar denominaciones
                            # ===========================
                            denominaciones = {}

                            for key, value in request.POST.items():
                                if key.startswith("den_"):
                                    try:
                                        cantidad = int(value)
                                    except:
                                        cantidad = 0

                                    if cantidad > 0:
                                        _, tipo, valor_str = key.split("_", 2)
                                        valor = float(valor_str.replace("_", "."))
                                        denominaciones[(tipo, valor)] = cantidad

                            # 2. Calcular y guardar la ganancia antes de completar
                            if tx.monto_operado is not None and tx.comision is not None:
                                tx.ganancia = tx.monto_operado * tx.comision
                                tx.save(update_fields=['ganancia'])

                            # 3. Confirmar la transacción y pasar a COMPLETADA
                            confirmar_transaccion(tx)
                            tx.estado = EstadoTransaccionEnum.COMPLETADA
                            tx.save()

                            # 5. Ahora sí, actualizar stock del tauser y registrar movimientos
                            tauser = tx.tauser
                            if not tauser:
                                raise Exception("No hay TAUser asignado a la transacción.")
                            from .models import Denominacion, TauserStock, TauserStockMovimiento, ReservaDenominacionTauser
                            from monedas.models import Moneda

                            tipo_tx = str(tx.tipo).lower()
                            medio_pago = getattr(tx, 'medio_pago', None)
                            medio_cobro = getattr(tx, 'medio_cobro', None)
                            pago_efectivo = getattr(medio_pago, 'payment_type', None) == 'efectivo'
                            cobro_efectivo = getattr(medio_cobro, 'payment_type', None) == 'efectivo'

                            # --- VENTA ---
                            if tipo_tx == "venta":
                                # ENTRADA siempre (recibe moneda extranjera)
                                moneda = tx.moneda
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
                                    stock_obj.quantity += cantidad
                                    stock_obj.save()
                                    if cantidad > 0:
                                        TauserStockMovimiento.objects.create(
                                            tauser=tauser,
                                            denominacion=denom_obj,
                                            cantidad=cantidad,
                                            tipo_movimiento=TauserStockMovimiento.ENTRADA,
                                            transaccion=tx
                                        )
                                # SALIDA solo si el cobro es efectivo (entrega PYG)
                                if cobro_efectivo:
                                    moneda_pyg = Moneda.objects.get(codigo="PYG")
                                    reservas = ReservaDenominacionTauser.objects.filter(transaccion=tx)
                                    for reserva in reservas:
                                        if reserva.denominacion.moneda == moneda_pyg:
                                            TauserStockMovimiento.objects.create(
                                                tauser=reserva.tauser,
                                                denominacion=reserva.denominacion,
                                                cantidad=reserva.cantidad,
                                                tipo_movimiento=TauserStockMovimiento.SALIDA,
                                                transaccion=tx
                                            )

                            # --- COMPRA ---
                            elif tipo_tx == "compra":
                                # ENTRADA (recibe PYG) SIEMPRE, sin importar el método de pago
                                moneda_pyg = Moneda.objects.get(codigo="PYG")
                                for (tipo, valor), cantidad in denominaciones.items():
                                    denom_obj, _ = Denominacion.objects.get_or_create(
                                        moneda=moneda_pyg,
                                        value=valor,
                                        type=tipo
                                    )
                                    stock_obj, _ = TauserStock.objects.get_or_create(
                                        tauser=tauser,
                                        denominacion=denom_obj
                                    )
                                    stock_obj.quantity += cantidad
                                    stock_obj.save()
                                    if cantidad > 0:
                                        TauserStockMovimiento.objects.create(
                                            tauser=tauser,
                                            denominacion=denom_obj,
                                            cantidad=cantidad,
                                            tipo_movimiento=TauserStockMovimiento.ENTRADA,
                                            transaccion=tx
                                        )
                                # SALIDA siempre (entrega moneda extranjera)
                                reservas = ReservaDenominacionTauser.objects.filter(transaccion=tx)
                                if not reservas.exists():
                                    # Depuración: si no hay reservas, dejar constancia
                                    import logging
                                    logging.warning(f"[TAUSER] No se encontraron reservas para registrar salida en compra. Transacción: {tx.id}")
                                for reserva in reservas:
                                    TauserStockMovimiento.objects.create(
                                        tauser=reserva.tauser,
                                        denominacion=reserva.denominacion,
                                        cantidad=reserva.cantidad,
                                        tipo_movimiento=TauserStockMovimiento.SALIDA,
                                        transaccion=tx
                                    )
                                    
                            # ===========================
                            # 5. Generar factura (NUEVO)
                            # ===========================
                            result_factura = None
                            if generar_factura:
                                from facturacion.services import ServicioFacturacion
                                # =====================
                                # CAPTURAR DATOS FISCALES
                                # =====================

                                # Soportar datos fiscales por POST o JSON (AJAX)
                                datos_fiscales = {
                                    "nombre": request.POST.get("fact_nombre"),
                                    "cedula": request.POST.get("fact_cedula"),
                                    "ruc": request.POST.get("fact_ruc"),
                                    "dv": request.POST.get("fact_dv"),
                                    "email": request.POST.get("fact_email"),
                                    "direccion": request.POST.get("fact_direccion"),
                                }
                                if not datos_fiscales["nombre"]:
                                    try:
                                        body = json.loads(request.body)
                                        df = body.get("datos_fiscales", {})
                                        datos_fiscales = {
                                            "nombre": df.get("nombre"),
                                            "cedula": df.get("cedula"),
                                            "ruc": df.get("ruc"),
                                            "dv": df.get("dv"),
                                            "email": df.get("email"),
                                            "direccion": df.get("direccion"),
                                        }
                                    except Exception:
                                        pass
                                tx.datos_fiscales = datos_fiscales
                                tx.save()

                                from facturacion.services import ServicioFacturacion
                                servicio = ServicioFacturacion()
                                result_factura = servicio.generar_factura(tx)
   
                            # Limpiar bandera de cotización aceptada de la sesión
                            session_key_cotizacion = f'cotizacion_aceptada_{codigo_verificacion}'
                            if session_key_cotizacion in request.session:
                                del request.session[session_key_cotizacion]

                            return JsonResponse({
                                "success": True,
                                "factura": result_factura
                            })

                        except Exception as e:
                            return JsonResponse({"success": False, "error": str(e)})

                    # ======================
                    #   ACCIÓN: CANCELAR
                    # ======================
                    elif accion == "cancelar":
                        try:
                            cancelar_transaccion(tx)
                            mensaje = f"Transacción #{tx.id} cancelada correctamente."
                        except Exception as e:
                            error = str(e)

    # Cargar denominaciones para venta/compra en efectivo
    denominaciones_venta = []
    if datos_transaccion:
        tipo = datos_transaccion["tipo"].lower()

        denominaciones_json_path = os.path.join(os.path.dirname(__file__), 'denominaciones.json')
        with open(denominaciones_json_path, 'r') as f:
            denominaciones_data = json.load(f)

        if tipo == "compra" and datos_transaccion.get("medio_pago") == "Efectivo":
            denominaciones_venta = [d for d in denominaciones_data if d["currency"] == "PYG"]
            denominaciones_venta.sort(key=lambda x: float(x["value"]), reverse=True)
        elif tipo == "venta":
            moneda_codigo = datos_transaccion["moneda"].codigo
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
        "verificacion_cotizacion": verificacion_cotizacion if 'verificacion_cotizacion' in locals() else None,
    })


def nuevo_tauser(request):
    """
    Permite crear un nuevo Tauser mediante un formulario.
    Muestra mensaje de éxito al guardar correctamente.
    """

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
    """
    Lista todos los Tausers, permitiendo filtrar por estado y fechas de alta.
    """
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
    """
    Permite editar el estado de un Tauser seleccionado.
    Guarda el nuevo estado si es válido y redirige a la lista de Tausers.
    """
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
