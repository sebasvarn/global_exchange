import json
from decimal import Decimal, ROUND_UP
import os

def redondear_a_denom_py(monto, denominaciones_path=None):
    """
    Redondea el monto al valor más cercano (arriba o abajo) que se pueda formar con las denominaciones válidas de PYG.
    """
    if denominaciones_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        denominaciones_path = os.path.join(base_dir, '../tauser/denominaciones.json')

    with open(denominaciones_path, 'r') as f:
        denominaciones = json.load(f)

    # Filtrar solo denominaciones de PYG
    denoms_pyg = [Decimal(str(d['value'])) for d in denominaciones if d['currency'] == 'PYG']
    denoms_pyg = sorted(denoms_pyg, reverse=True)  # Ordenar de mayor a menor

    monto = Decimal(monto)

    # Función para descomponer un monto en denominaciones (greedy)
    def descomponer(monto_objetivo):
        monto_objetivo = Decimal(monto_objetivo)
        monto_actual = Decimal('0')
        restante = monto_objetivo
        for denom in denoms_pyg:
            cantidad = (restante // denom)
            monto_actual += cantidad * denom
            restante -= cantidad * denom
        return monto_actual

    # Buscar el múltiplo inferior y superior de la denominación más baja
    denom_min = min(denoms_pyg)
    abajo = (monto // denom_min) * denom_min
    arriba = ((monto + denom_min - 1) // denom_min) * denom_min

    # Descomponer ambos
    monto_abajo = descomponer(abajo)
    monto_arriba = descomponer(arriba)

    # Elegir el más cercano
    if abs(monto - monto_abajo) <= abs(monto_arriba - monto):
        return monto_abajo
    else:
        return monto_arriba
