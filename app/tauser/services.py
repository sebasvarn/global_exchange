from decimal import Decimal
from .models import Tauser, Denominacion
from transaccion.models import Transaccion
from monedas.models import Moneda

def validar_stock_tauser_para_transaccion(transaccion_id, tauser_id):
    """
    Verifica si el Tauser puede entregar el monto exacto de la transacción usando su stock de denominaciones.
    Retorna un diccionario con:
      - 'ok': True/False
      - 'faltante': monto faltante (Decimal, si aplica)
      - 'moneda': Moneda de entrega
      - 'entregado': lista de (valor, cantidad) de denominaciones usadas
      - 'mensaje': mensaje de resultado
    """
    try:
        tx = Transaccion.objects.select_related("moneda").get(id=transaccion_id)
    except Transaccion.DoesNotExist:
        return {'ok': False, 'mensaje': 'Transacción no encontrada.'}
    try:
        tauser = Tauser.objects.get(id=tauser_id)
    except Tauser.DoesNotExist:
        return {'ok': False, 'mensaje': 'Tauser no encontrado.'}

    if tx.tipo == "venta":
        moneda_entrega = Moneda.objects.get(codigo="PYG")
        monto_entregar = tx.monto_pyg
    else:  # compra
        moneda_entrega = tx.moneda
        monto_entregar = tx.monto_operado

    stock_qs = tauser.stocks.filter(denominacion__moneda=moneda_entrega, quantity__gt=0).select_related('denominacion').order_by('-denominacion__value')
    stock_list = [(s.denominacion.value, s.quantity) for s in stock_qs]

    monto_restante = Decimal(monto_entregar)
    entregado = []
    for valor, cantidad in stock_list:
        valor = Decimal(valor)
        max_billetes = int(monto_restante // valor)
        usar = min(max_billetes, cantidad)
        if usar > 0:
            entregado.append((valor, usar))
            monto_restante -= valor * usar
    if monto_restante == 0:
        return {
            'ok': True,
            'faltante': Decimal('0'),
            'moneda': moneda_entrega,
            'entregado': entregado,
            'mensaje': 'Stock suficiente: el Tauser puede entregar el monto exacto usando las denominaciones disponibles.'
        }
    else:
        return {
            'ok': False,
            'faltante': monto_restante,
            'moneda': moneda_entrega,
            'entregado': entregado,
            'mensaje': f'Stock insuficiente: el Tauser no puede entregar el monto exacto con las denominaciones disponibles. Faltante: {monto_restante} {moneda_entrega.codigo}.'
        }
