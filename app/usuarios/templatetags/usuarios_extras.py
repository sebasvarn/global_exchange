from django import template

register = template.Library()

@register.filter(name='replace')
def replace(value, arg):
    """
    Reemplaza la primera coma por el separador y luego el texto a buscar y el texto de reemplazo.
    Uso: {{ value|replace:"buscar,reemplazo" }}
    """
    try:
        buscar, reemplazo = arg.split(',')
        return value.replace(buscar, reemplazo)
    except Exception:
        return value

@register.filter
def has_permission(user, perm_code):
    """
    Filtro para verificar si el usuario tiene un permiso específico.
    Uso: {% if request.user|has_permission:'usuarios.create' %}
    """
    if not user.is_authenticated:
        return False
    return hasattr(user, 'has_permission') and user.has_permission(perm_code)

@register.filter
def has_any_permission(user, perm_codes):
    """
    Filtro para verificar si el usuario tiene al menos uno de los permisos indicados (separados por coma).
    Uso: {% if request.user|has_any_permission:'usuarios.view,usuarios.create' %}
    """
    if not user.is_authenticated:
        return False
    if not hasattr(user, 'has_permission'):
        return False
    codes = [c.strip() for c in perm_codes.split(',') if c.strip()]
    return any(user.has_permission(code) for code in codes)
