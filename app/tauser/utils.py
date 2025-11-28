from transaccion.models import Transaccion
from transaccion.services import calcular_transaccion
from monedas.models import TasaCambio 

def obtener_datos_transaccion(transaccion_id):
    """
    Obtiene y retorna los datos relevantes de una transacción para su procesamiento o visualización.

    :param transaccion_id: ID de la transacción a consultar.
    :type transaccion_id: int
    :returns: Información de la transacción.
    :rtype: dict
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
