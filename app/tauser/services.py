from decimal import Decimal

from .models import Tauser, Denominacion
from monedas.models import Moneda

def validar_stock_tauser_para_transaccion(tauser_id, monto, moneda_id):
    """
    Verifica si el Tauser puede entregar el monto exacto usando su stock de denominaciones.
    Recibe:
      - tauser_id: ID del Tauser
      - monto: Decimal (monto a entregar)
      - moneda_id: ID de la moneda a entregar
    Retorna un diccionario con:
      - 'ok': True/False
      - 'faltante': monto faltante (Decimal, si aplica)
      - 'moneda': Moneda de entrega
      - 'entregado': lista de (valor, cantidad) de denominaciones usadas
      - 'mensaje': mensaje de resultado
    """
    try:
        tauser = Tauser.objects.get(id=tauser_id)
    except Tauser.DoesNotExist:
        return {'ok': False, 'mensaje': 'Tauser no encontrado.'}
    try:
        moneda_entrega = Moneda.objects.get(id=moneda_id)
    except Moneda.DoesNotExist:
        return {'ok': False, 'mensaje': 'Moneda no encontrada.'}

    stock_qs = tauser.stocks.filter(denominacion__moneda=moneda_entrega, quantity__gt=0).select_related('denominacion').order_by('-denominacion__value')
    stock_list = [(s.denominacion.value, s.quantity) for s in stock_qs]

    monto_restante = Decimal(monto)
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
            'moneda': str(moneda_entrega),
            'entregado': entregado,
            'mensaje': 'Stock suficiente: el Tauser puede entregar el monto exacto usando las denominaciones disponibles.'
        }
    else:
        return {
            'ok': False,
            'faltante': monto_restante,
            'moneda': str(moneda_entrega),
            'entregado': entregado,
            'mensaje': f'Stock insuficiente: el Tauser no puede entregar el monto exacto con las denominaciones disponibles. Faltante: {monto_restante} {moneda_entrega.codigo}.'
        }
