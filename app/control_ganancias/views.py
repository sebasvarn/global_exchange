from django.shortcuts import render

from django.utils import timezone
from datetime import timedelta, datetime
from transaccion.models import Transaccion
from commons.enums import EstadoTransaccionEnum, TipoTransaccionEnum

from collections import defaultdict
import json
from collections import Counter, defaultdict
from clientes.models import Cliente
from transaccion.models import Transaccion
from monedas.models import Moneda

def dashboard(request):
	"""
	Vista principal del dashboard de control de ganancias.
    
	Esta vista procesa y filtra las transacciones por estado y rango de fechas (máximo 1 año),
	calculando métricas y datos estadísticos para el dashboard, incluyendo:
	- Ganancia total, por fecha, por moneda y por método de pago.
	- Distribución de transacciones por tipo y por segmento de cliente.
	- Conteo y montos de transacciones completadas y pagadas.
	- Spread promedio aplicado.
	- Detalle de transacciones para visualización en tabla.
    
	Los datos se envían al template para su visualización en gráficos y tablas.
    
	:param request: Objeto HttpRequest de Django.
	:type request: HttpRequest
	:return: Página renderizada con los datos del dashboard de control de ganancias.
	:rtype: HttpResponse
	"""
	# Filtro por rango de fechas (máx 1 año)
	today = timezone.now().date()
	default_start = today - timedelta(days=30)
	start_date = request.GET.get('start_date', default_start.strftime('%Y-%m-%d'))
	end_date = request.GET.get('end_date', today.strftime('%Y-%m-%d'))

	# Limitar rango a 1 año
	try:
		start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
		end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
		if (end_dt - start_dt).days > 365:
			start_dt = end_dt - timedelta(days=365)
	except Exception:
		start_dt = default_start
		end_dt = today

	# Filtrar transacciones por estado y rango de fechas
	transacciones_completadas = Transaccion.objects.filter(
		estado=EstadoTransaccionEnum.COMPLETADA,
		fecha__date__gte=start_dt,
		fecha__date__lte=end_dt
	)
	transacciones_pagadas = Transaccion.objects.filter(
		estado=EstadoTransaccionEnum.PAGADA,
		fecha__date__gte=start_dt,
		fecha__date__lte=end_dt
	)
	# Todas las transacciones pagadas o completadas
	transacciones = Transaccion.objects.filter(
		estado__in=[EstadoTransaccionEnum.COMPLETADA, EstadoTransaccionEnum.PAGADA],
		fecha__date__gte=start_dt,
		fecha__date__lte=end_dt
	)

	# Para gráfico de torta de tipo de cliente (completadas y pagadas)

	# Usar los tipos definidos en Cliente.SEGMENTOS para el orden y los labels
	tipos_clientes = [label for _, label in Cliente.SEGMENTOS]
	# Mapear display a valor interno para contar correctamente
	tipo_display_map = {valor: label for valor, label in Cliente.SEGMENTOS}
	# Contar por valor interno y luego mapear a display
	clientes_tipo_completadas = Counter([tipo_display_map.get(t.cliente.tipo, t.cliente.get_tipo_display()) for t in transacciones_completadas])
	clientes_tipo_pagadas = Counter([tipo_display_map.get(t.cliente.tipo, t.cliente.get_tipo_display()) for t in transacciones_pagadas])
	# Sumar completadas y pagadas por tipo de cliente
	transacciones_por_tipo_cliente = [clientes_tipo_completadas.get(tc, 0) + clientes_tipo_pagadas.get(tc, 0) for tc in tipos_clientes]

	# Ganancia total de todas las transacciones pagadas y completadas
	ganancia_total = sum([float(t.ganancia or 0) for t in transacciones])

	# Ganancia de completadas
	monto_completadas_total = sum([float(t.ganancia or 0) for t in transacciones_completadas])

	# Ganancia de pagadas
	monto_pagado_total = sum([float(t.ganancia or 0) for t in transacciones_pagadas])

	# Ganancia por fecha (para gráfico de líneas)
	ganancias_por_fecha = defaultdict(float)
	for t in transacciones:
		fecha_str = t.fecha.strftime('%Y-%m-%d')
		ganancias_por_fecha[fecha_str] += float(t.ganancia or 0)
	fechas = sorted(ganancias_por_fecha.keys())
	ganancias = [ganancias_por_fecha[f] for f in fechas]

	# Ganancia por moneda (para gráfico de barras)
	ganancias_por_moneda = defaultdict(float)
	monedas_set = set()
	for t in transacciones:
		if t.moneda:
			codigo = t.moneda.codigo
			monedas_set.add(codigo)
			ganancias_por_moneda[codigo] += float(t.ganancia or 0)
	monedas = sorted(monedas_set)
	ganancias_monedas = [ganancias_por_moneda[m] for m in monedas]

	# Ganancia por método de pago
	ganancias_por_metodo = defaultdict(float)
	for t in transacciones:
		if t.medio_pago:
			nombre = str(t.medio_pago)
			ganancias_por_metodo[nombre] += float(t.ganancia or 0)

	# Ganancia por tipo de transacción y conteo para gráfico de torta
	ganancias_por_tipo = defaultdict(float)
	transacciones_por_tipo = defaultdict(int)
	for t in transacciones:
		tipo = t.get_tipo_display() if hasattr(t, 'get_tipo_display') else t.tipo
		ganancias_por_tipo[tipo] += float(t.ganancia or 0)
		transacciones_por_tipo[tipo] += 1

	# Spread promedio (simulado, puedes ajustar la lógica)
	spread_promedio = None
	spreads = [float(getattr(t, 'tasa_aplicada', 0)) for t in transacciones if getattr(t, 'tasa_aplicada', None)]
	if spreads:
		spread_promedio = f"{sum(spreads)/len(spreads):.2f}%"
	else:
		spread_promedio = "2.5%"

	# Tipos para gráfico de torta
	tipos = list(transacciones_por_tipo.keys())
	transacciones_por_tipo_list = [transacciones_por_tipo[t] for t in tipos]

	# Detalle de transacciones (opcional, para tabla)
	detalle_transacciones = transacciones.select_related('moneda', 'medio_pago', 'cliente')

	context = {
		'fechas': json.dumps(fechas),
		'ganancias': json.dumps(ganancias),
		'monedas': json.dumps(monedas),
		'ganancias_monedas': json.dumps(ganancias_monedas),
		'ganancia_total': ganancia_total,
		'transacciones_completadas': transacciones_completadas.count(),
		'monto_completadas_total': monto_completadas_total,
		'transacciones_pagadas': transacciones_pagadas.count(),
		'monto_pagado_total': monto_pagado_total,
		'ganancias_por_metodo': dict(ganancias_por_metodo),
		'ganancias_por_tipo': dict(ganancias_por_tipo),
		'tipos': json.dumps(tipos),
		'transacciones_por_tipo': json.dumps(transacciones_por_tipo_list),
		'detalle_transacciones': detalle_transacciones,
		'tipos_clientes': json.dumps(tipos_clientes),
		'transacciones_por_tipo_cliente': json.dumps(transacciones_por_tipo_cliente),
		'start_date': start_dt.strftime('%Y-%m-%d'),
		'end_date': end_dt.strftime('%Y-%m-%d'),
	}
	return render(request, 'control_ganancias/dashboard.html', context)

def reporte_transacciones(request):
	# Filtros GET
	fecha_desde = request.GET.get('fecha_desde')
	fecha_hasta = request.GET.get('fecha_hasta')
	tipo = request.GET.get('tipo')
	estado = request.GET.get('estado')
	moneda = request.GET.get('moneda')
	cliente = request.GET.get('cliente')

	# Totales para tarjetas (sin filtros)
	total_transacciones = Transaccion.objects.count()
	total_completadas = Transaccion.objects.filter(estado=EstadoTransaccionEnum.COMPLETADA).count()
	total_pagadas = Transaccion.objects.filter(estado=EstadoTransaccionEnum.PAGADA).count()
	total_pendientes = Transaccion.objects.filter(estado=EstadoTransaccionEnum.PENDIENTE).count()
	total_canceladas = Transaccion.objects.filter(estado=EstadoTransaccionEnum.CANCELADA).count()
	total_anuladas = Transaccion.objects.filter(estado=EstadoTransaccionEnum.ANULADA).count()

	# Filtros para la tabla y gráfico
	transacciones = Transaccion.objects.all()
	if fecha_desde:
		transacciones = transacciones.filter(fecha__date__gte=fecha_desde)
	if fecha_hasta:
		transacciones = transacciones.filter(fecha__date__lte=fecha_hasta)
	if tipo:
		transacciones = transacciones.filter(tipo=tipo)
	if estado:
		transacciones = transacciones.filter(estado=estado)
	if moneda:
		transacciones = transacciones.filter(moneda__codigo=moneda)
	if cliente:
		transacciones = transacciones.filter(cliente__id=cliente)

	# Datos para gráfico de transacciones por día (según filtros)
	transacciones_por_fecha = defaultdict(int)
	for t in transacciones:
		fecha_str = t.fecha.strftime('%d-%m-%Y')
		transacciones_por_fecha[fecha_str] += 1
	fechas_grafico = sorted(transacciones_por_fecha.keys(), key=lambda x: datetime.strptime(x, '%d-%m-%Y'))
	cantidades_grafico = [transacciones_por_fecha[f] for f in fechas_grafico]
	fechas_grafico_json = json.dumps(fechas_grafico)
	cantidades_grafico_json = json.dumps(cantidades_grafico)

	# Datos para gráfico de torta por tipo de transacción (compra/venta) según filtro de fecha
	tipos_torta = [TipoTransaccionEnum.COMPRA, TipoTransaccionEnum.VENTA]
	tipos_torta_labels = ['Compra', 'Venta']
	transacciones_por_tipo_torta = [transacciones.filter(tipo=tipo).count() for tipo in tipos_torta]
	tipos_torta_json = json.dumps(tipos_torta_labels)
	transacciones_por_tipo_torta_json = json.dumps(transacciones_por_tipo_torta)

	# Opciones para selects
	monedas = Moneda.objects.all()
	clientes = Cliente.objects.filter(transacciones__isnull=False).distinct()

	# Poblar tabla
	detalle_transacciones = transacciones.select_related('moneda', 'medio_pago', 'cliente')

	context = {
		'total_transacciones': total_transacciones,
		'total_completadas': total_completadas,
		'total_pagadas': total_pagadas,
		'total_pendientes': total_pendientes,
		'total_canceladas': total_canceladas,
		'total_anuladas': total_anuladas,
		'monedas': monedas,
		'clientes': clientes,
		'detalle_transacciones': detalle_transacciones,
		'fechas_grafico': fechas_grafico_json,
		'cantidades_grafico': cantidades_grafico_json,
		'tipos_torta': tipos_torta_json,
		'transacciones_por_tipo_torta': transacciones_por_tipo_torta_json,
		'filtros': {
			'fecha_desde': fecha_desde,
			'fecha_hasta': fecha_hasta,
			'tipo': tipo,
			'estado': estado,
			'moneda': moneda,
			'cliente': cliente,
		}
	}
	return render(request, 'control_ganancias/reporte_transacciones.html', context)
