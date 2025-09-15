"""
Librería de filtros de template para 'monedas'.

- money: formatea números como moneda con decimales dinámicos y separadores de
  miles 'es-PY' (puntos para miles, coma para decimales).
"""

from decimal import Decimal, ROUND_HALF_UP
from django import template

register = template.Library()


@register.filter
def money(value, decs=0):
    """Formato con cantidad de decimales dinámica y separador de miles."""
    try:
        decs = int(decs)
        q = Decimal('1.' + ('0' * decs)) if decs > 0 else Decimal('1')
        v = Decimal(value).quantize(q, rounding=ROUND_HALF_UP)
        s = f'{v:,.{decs}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        return s
    except Exception:
        return value
