from transaccion.models import Transaccion
from transaccion.services import calcular_transaccion
from monedas.models import TasaCambio 

#no se usa actualmente creo

def obtener_datos_transaccion(transaccion_id):
    """
    Dado el id de una transacción, retorna un diccionario con los datos clave de la transacción.

    Args:
        transaccion_id (int): ID de la transacción.

    Returns:
        dict | None: Diccionario con tipo, moneda, tasa aplicada y tasa recalculada, o None si no existe.
    """
    try:
        transaccion = Transaccion.objects.select_related('moneda').get(pk=transaccion_id)
    except Transaccion.DoesNotExist:
        return None

    # Recalcular la tasa usando el servicio oficial
    recalculo = calcular_transaccion(
        transaccion.cliente,
        transaccion.tipo,
        transaccion.moneda,
        transaccion.monto_operado
    )
    tasa_recalculada = recalculo['tasa_aplicada']

    datos = {
        'tipo': transaccion.tipo,
        'moneda': {
            'codigo': transaccion.moneda.codigo,
        },
        'tasa': transaccion.tasa_aplicada,
        'tasa_recalculada': tasa_recalculada,
    }

    return datos
