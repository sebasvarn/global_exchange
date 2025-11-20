from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.http import Http404


def role_required(*required_roles):
    """
    Decorador que requiere que el usuario tenga al menos uno de los roles especificados.

    Si no se especifica ningún rol, solo verifica que el usuario esté autenticado.

    Args:
        *required_roles: Lista de nombres de roles permitidos para acceder a la vista.

    Ejemplos:
        @role_required("Admin")
        @role_required("Admin", "Moderator")

    Returns:
        Función decorada que verifica los roles antes de ejecutar la vista.
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('usuarios:login')

            # Si no se requieren roles específicos, solo verificar autenticación
            if not required_roles:
                return view_func(request, *args, **kwargs)

            # Verificar si el usuario tiene alguno de los roles requeridos
            if request.user.has_any_role(*required_roles):
                return view_func(request, *args, **kwargs)

            # Usuario no tiene permisos
            messages.error(
                request,
                f"No tienes permisos para acceder a esta sección. "
                f"Se requiere uno de los siguientes roles: {', '.join(required_roles)}"
            )
            return redirect('usuarios:dashboard')

        return wrapper

    return decorator


def admin_required(view_func):
    """
    Decorador que requiere que el usuario tenga el rol 'Admin'.

    Este decorador es un atajo para:
        @role_required("Admin")

    Args:
        view_func (callable): Vista que se desea proteger.

    Returns:
        Función decorada que verifica que el usuario tenga rol Admin.
    """
    return role_required("Admin")(view_func)


def role_required_or_owner(required_role):
    """
    Decorador que permite acceso si el usuario tiene un rol específico
    o si es el propietario de un objeto (por ejemplo, su propio perfil).

    Esto es útil para vistas que permiten que un usuario edite su perfil
    aunque no tenga rol de administrador.

    Args:
        required_role (str): Nombre del rol requerido para acceder.

    Ejemplo:
        @role_required_or_owner("Admin")
        def edit_user(request, user_id):
            ...

    Returns:
        Función decorada que verifica rol o propiedad antes de ejecutar la vista.
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Si tiene el rol requerido, permitir acceso
            if request.user.has_role(required_role):
                return view_func(request, *args, **kwargs)

            # Si está editando su propio perfil
            user_id = kwargs.get('user_id')
            if user_id and str(request.user.id) == str(user_id):
                return view_func(request, *args, **kwargs)

            # No tiene permisos
            messages.error(
                request,
                "No tienes permisos para realizar esta acción."
            )
            return redirect('usuarios:dashboard')

        return wrapper

    return decorator


def role_required_ajax(*required_roles):
    """
    Decorador para vistas AJAX que requieren roles específicos.

    A diferencia de role_required, en caso de no tener permisos lanza Http404
    en lugar de redirigir al dashboard, ya que es común en APIs o AJAX no redirigir.

    Args:
        *required_roles: Lista de roles permitidos para acceder a la vista.

    Returns:
        Función decorada que verifica los roles antes de ejecutar la vista.
        Lanza Http404 si el usuario no tiene permisos.
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not request.user.has_any_role(*required_roles):
                raise Http404("No tienes permisos para acceder a este recurso.")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
