
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from transaccion.models import Transaccion
from transaccion.services import confirmar_transaccion, cancelar_transaccion
from monedas.models import TasaCambio
from commons.enums import EstadoTransaccionEnum
from django.utils import timezone


from django.shortcuts import render
from django.contrib import messages
from transaccion.models import Transaccion
from transaccion.services import confirmar_transaccion, cancelar_transaccion, calcular_transaccion
from monedas.models import TasaCambio
from commons.enums import EstadoTransaccionEnum
from django.utils import timezone

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
                if cantidad > 0:
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
    Permite consultar datos de una transacción por ID y muestra mensajes de error si corresponde.
    """

    tausers_activos = Tauser.objects.filter(estado="activo").order_by('nombre')
    tauser_seleccionado = request.POST.get("tauser_id", "")

    datos_transaccion = None
    error = None
    mensaje = None
    transaccion_uuid = request.POST.get("transaccion_uuid", "").strip()

    if request.method == "POST":
        accion = request.POST.get("accion", "buscar")

        if not transaccion_uuid:
            error = "Debe ingresar el código de transacción."
        else:
            try:
                tx = Transaccion.objects.select_related("moneda", "cliente").get(uuid=transaccion_uuid)
            except Transaccion.DoesNotExist:
                tx = None
                error = "No se encontró ninguna transacción con ese código."

            if tx:
                # Buscar tasa actual según tipo de transacción
                tasa_obj = TasaCambio.objects.filter(moneda=tx.moneda, activa=True).latest("fecha_creacion")
                if tx.tipo == "compra":
                    # Si la transacción es COMPRA, mostrar la tasa de VENTA
                    tasa_actual = tasa_obj.venta
                else:
                    # Si la transacción es VENTA, mostrar la tasa de COMPRA
                    tasa_actual = tasa_obj.compra

                if accion == "buscar":
                    datos_transaccion = {
                        "uuid": tx.uuid,
                        "id": tx.id,
                        "cliente": tx.cliente,
                        "tipo": tx.get_tipo_display(),
                        "moneda": tx.moneda,
                        "tasa": tx.tasa_aplicada,
                        "tasa_recalculada": tasa_actual,
                        "monto_operado": tx.monto_operado,
                        "monto_pyg": tx.monto_pyg,
                        "fecha": tx.fecha.astimezone(timezone.get_current_timezone()),
                        "estado": tx.estado,
                    }

                elif accion == "recalcular":
                    try:
                        # recalcular usando la tasa nueva
                        recalculo = calcular_transaccion(tx.cliente, tx.tipo, tx.moneda, tx.monto_operado)
                        tx.tasa_aplicada = recalculo["tasa_aplicada"]
                        tx.monto_pyg = recalculo["monto_pyg"]
                        tx.save(update_fields=["tasa_aplicada", "monto_pyg"])
                        mensaje = "Transacción recalculada con la nueva tasa."
                        datos_transaccion = {
                            "uuid": tx.uuid,
                            "id": tx.id,
                            "cliente": tx.cliente,
                            "tipo": tx.get_tipo_display(),
                            "moneda": tx.moneda,
                            "tasa": tx.tasa_aplicada,
                            "tasa_recalculada": tx.tasa_aplicada,
                            "monto_operado": tx.monto_operado,
                            "monto_pyg": tx.monto_pyg,
                            "fecha": tx.fecha,
                            "estado": tx.estado,
                        }
                    except Exception as e:
                        error = f"No se pudo recalcular: {e}"

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

    return render(request, "tramitar_transacciones.html", {
        "datos_transaccion": datos_transaccion,
        "error": error,
        "mensaje": mensaje,
        "transaccion_uuid": transaccion_uuid,
        "tausers": tausers_activos,
        "tauser_seleccionado": tauser_seleccionado,
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
