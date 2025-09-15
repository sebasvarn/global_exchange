"""
Vistas y lógica de negocio para la aplicación de usuarios.

Incluye vistas para registro, login, verificación de cuenta y gestión de sesiones y roles.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .decorators import role_required
from .forms import AsignarClientesAUsuarioForm, RegistroForm, LoginForm, UserForm, AsignarRolForm, RoleForm, UserCreateForm, PasswordResetRequestForm
from .models import Role, UserRole
from commons.enums import EstadoRegistroEnum
from clientes.models import Cliente

User = get_user_model()


def dashboard_view(request):
    """
    Vista principal del dashboard.

    Muestra estadísticas generales de usuarios, roles y clientes.

    :param request: HttpRequest
    :return: HttpResponse con el dashboard
    """
    context = {}
    if request.user.is_authenticated:
        from django.db.models import Count
        total_usuarios = User.objects.count()
        usuarios_activos = User.objects.filter(is_active=True).count()
        total_roles = Role.objects.count()
        total_clientes = Cliente.objects.count()
        tasas = [
            {
                "base_currency": "PYG",
                "currency": "ARS",
                "buy": "4.500000",
                "sell": "5.600000",
                "source": "Cambios Chaco",
                "timestamp": "2025-09-15T14:22:53.964357Z"
            },
            {
                "base_currency": "PYG",
                "currency": "BRL",
                "buy": "1310.000000",
                "sell": "1350.000000",
                "source": "Cambios Chaco",
                "timestamp": "2025-09-15T14:22:53.961464Z"
            },
            {
                "base_currency": "PYG",
                "currency": "CLP",
                "buy": "6.000000",
                "sell": "10.000000",
                "source": "Cambios Chaco",
                "timestamp": "2025-09-15T14:22:53.970341Z"
            },
            {
                "base_currency": "PYG",
                "currency": "EUR",
                "buy": "8250.000000",
                "sell": "8750.000000",
                "source": "Cambios Chaco",
                "timestamp": "2025-09-15T14:22:53.967095Z"
            },
            {
                "base_currency": "PYG",
                "currency": "GBP",
                "buy": "9500.000000",
                "sell": "11000.000000",
                "source": "Cambios Chaco",
                "timestamp": "2025-09-15T14:22:53.973501Z"
            },
            {
                "base_currency": "PYG",
                "currency": "USD",
                "buy": "7130.000000",
                "sell": "7210.000000",
                "source": "Cambios Chaco",
                "timestamp": "2025-09-15T14:22:53.953558Z"
            }
        ]
        # Adaptar para el template: crear objetos simples
        from decimal import Decimal
        tasas_obj = []
        for d in tasas:
            class MonedaSimple:
                pass
            m = MonedaSimple()
            m.codigo = d.get('currency', '')
            m.nombre = d.get('currency', '')
            m.simbolo = d.get('currency', '')
            m.decimales = 2
            class TasaSimple:
                pass
            t = TasaSimple()
            t.moneda = m
            t.compra = Decimal(d.get('buy', '0'))
            t.venta = Decimal(d.get('sell', '0'))
            t.variacion = Decimal('0')
            tasas_obj.append(t)
        ultima_actualizacion_tasas = max(d.get('timestamp', '') for d in tasas if d.get('timestamp'))
        context.update({
            'total_usuarios': total_usuarios,
            'total_clientes' : total_clientes,
            'usuarios_activos': usuarios_activos,
            'total_roles': total_roles,
            'tasas': tasas_obj,
            'ultima_actualizacion_tasas': ultima_actualizacion_tasas
        })
    return render(request, "dashboard.html", context)

@login_required
@role_required("Admin")
def usuario_restore(request, user_id):
    """
    Vista para restaurar un usuario eliminado lógicamente.
    """
    usuario = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        usuario.estado = EstadoRegistroEnum.ACTIVO.value
        usuario.save()
        messages.success(request, "Usuario restaurado correctamente.")
        return redirect("usuarios:usuarios_list")
    return render(request, "usuarios/usuario_restore_confirm.html", {"usuario": usuario})

@login_required
@role_required("Admin")
def usuario_create(request):
    """
    Vista para crear usuarios desde el panel de administración.
    Args:
        request: HttpRequest
    Returns:
        HttpResponse con el formulario o redirección.
    """
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Usuario {user.email} creado exitosamente.")
            return redirect("usuarios:usuarios_list")
    else:
        """
        Vistas para la aplicación de usuarios.
        Define las funciones y clases que gestionan las peticiones HTTP relacionadas con usuarios.
        """
        form = UserCreateForm()
        # Por defecto, los usuarios creados desde admin están activos
        form.fields['is_active'].initial = True

    return render(request, "usuarios/usuario_form.html", {"form": form, "usuario": None})


@login_required
@role_required("Admin")
def usuarios_list(request):
    """
    Vista para listar usuarios registrados.

    Permite filtrar por estado, rol y búsqueda por email. Muestra la lista paginada de usuarios.

    :param request: HttpRequest
    :return: HttpResponse con la lista paginada de usuarios
    """
    from django.core.paginator import Paginator
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    role_filter = request.GET.get('role', '')

    # Filtro para mostrar/ocultar eliminados
    show_deleted = request.GET.get('show_deleted', '0') == '1'

    # Consulta base
    usuarios = User.objects.all()
    if not show_deleted:
        usuarios = usuarios.filter(estado=EstadoRegistroEnum.ACTIVO.value)

    # Aplicar filtros
    if search_query:
        usuarios = usuarios.filter(email__icontains=search_query)

    if status_filter == 'active':
        usuarios = usuarios.filter(is_active=True)
    elif status_filter == 'inactive':
        usuarios = usuarios.filter(is_active=False)

    if role_filter:
        usuarios = usuarios.filter(user_roles__role__name=role_filter).distinct()

    # Ordenar por fecha de creación (más recientes primero)
    usuarios = usuarios.order_by("-date_joined")

    # Paginación
    paginator = Paginator(usuarios, 10)  # 10 usuarios por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ...existing code...
    # Obtener todos los roles para el filtro
    roles = Role.objects.all()

    context = {
        "usuarios": page_obj,
        "page_obj": page_obj,
        "roles": roles,
        "search_query": search_query,
        "status_filter": status_filter,
        "role_filter": role_filter,
        "show_deleted": show_deleted,
        "total_usuarios": usuarios.count(),
    }

    return render(request, "usuarios/usuarios_list.html", context)


@login_required
@role_required("Admin")
def usuario_edit(request, user_id):
    """
    Vista para editar un usuario existente.
    Args:
        request: HttpRequest
        user_id: ID del usuario a editar.
    Returns:
        HttpResponse con el formulario de edición o redirección.
    """
    usuario = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        form = UserForm(request.POST, instance=usuario)
        if form.is_valid():
            password = form.cleaned_data.get("password")
            form.save()
            # Si el usuario editado es el mismo que el logueado y se cambió la contraseña, actualiza la sesión para evitar logout
            if password and request.user.pk == usuario.pk:
                update_session_auth_hash(request, usuario)
                messages.success(request, "Contraseña actualizada correctamente.")
                return redirect("usuarios:usuarios_list")
            messages.success(request, "Usuario actualizado.")
            return redirect("usuarios:usuarios_list")
    else:
        form = UserForm(instance=usuario)
    return render(request, "usuarios/usuario_form.html", {"form": form, "usuario": usuario})


@login_required
@role_required("Admin")
def usuario_delete(request, user_id):
    """
    Vista para eliminar un usuario.
    Args:
        request: HttpRequest
        user_id: ID del usuario a eliminar.
    Returns:
        HttpResponse con la confirmación de eliminación.
    """
    usuario = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        usuario.estado = EstadoRegistroEnum.ELIMINADO.value
        usuario.save()
        messages.success(request, "Usuario eliminado lógicamente.")
        return redirect("usuarios:usuarios_list")
    return render(request, "usuarios/usuario_delete_confirm.html", {"usuario": usuario})


def _enviar_verificacion(user):
    """
    Envía un correo de verificación de cuenta al usuario.

    :param user: Usuario al que se envía el correo.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    url = f"{settings.SITE_URL}/usuarios/verificar/{uid}/{token}/"
    asunto = "Verifica tu cuenta"
    cuerpo = (
        "¡Bienvenido/a!\n\n"
        "Para activar tu cuenta, hace clic en el siguiente enlace:\n"
        f"{url}\n\n"
        "Si no creaste esta cuenta, ignora este mensaje."
    )
    send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, [user.email])


def registro(request):
    """
    Vista para registrar un nuevo usuario.
    Args:
        request: HttpRequest
    Returns:
        HttpResponse con el formulario de registro o redirección.
    """
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            user = User.objects.create_user(email=email, password=form.cleaned_data['password1'])
            user.is_active = False  # inactivo hasta verificar
            user.save()
            _enviar_verificacion(user)
            messages.success(request, "Registro exitoso. Revisa tu correo para activar la cuenta.")
            return redirect('usuarios:login')
    else:
        form = RegistroForm()
    return render(request, 'usuarios/registro.html', {'form': form})


def verificar_email(request, uidb64, token):
    """
    Vista para verificar el email de un usuario mediante enlace enviado por correo.

    :param request: HttpRequest
    :param uidb64: ID del usuario codificado en base64
    :param token: Token de verificación
    :return: Redirección a login con mensaje
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError):
        messages.error(request, "Enlace inválido.")
        return redirect('usuarios:login')

    if default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save()
        messages.success(request, "Cuenta activada correctamente. Ya podes iniciar sesion.")
        return redirect('usuarios:login')
    messages.error(request, "Token invalido o expirado.")
    return redirect('usuarios:login')


def login_view(request):
    """
    Vista para iniciar sesión de usuario.

    :param request: HttpRequest
    :return: HttpResponse con el formulario de login o redirección
    """
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        email = request.POST.get('username', '').strip().lower()
        try:
            user = User.objects.get(email=email)
            if not user.is_active or user.estado == EstadoRegistroEnum.ELIMINADO.value:
                messages.error(request, "Tu cuenta está inactiva o eliminada. Contacta al administrador.")
                form.errors.pop('__all__', None)  # Elimina el error por defecto
                return render(request, 'usuarios/login.html', {'form': form})
        except User.DoesNotExist:
            pass  # Deja que el formulario maneje el error de usuario inexistente

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('usuarios:dashboard')
    else:
        form = LoginForm()
    return render(request, 'usuarios/login.html', {'form': form})

def logout_view(request):
    """
    Vista para cerrar la sesión del usuario.

    :param request: HttpRequest.
    :return: Redirección a la página de login.
    """
    logout(request)
    return redirect('usuarios:login')


@login_required
@role_required("Admin")
def roles_list(request):
    """
    Vista para listar los roles (grupos) existentes.

    :param request: HttpRequest.
    :return: HttpResponse con la lista de roles.
    """

    # Filtro para mostrar/ocultar eliminados
    show_deleted = request.GET.get('show_deleted', '0') == '1'

    # Consulta base
 
    roles = Role.objects.all()
    if not show_deleted:
        roles = roles.filter(estado=EstadoRegistroEnum.ACTIVO.value)

    return render(request, "usuarios/roles_list.html", {"roles": roles, "show_deleted": show_deleted})


@login_required
@role_required("Admin")
def rol_create(request):
    """
    Vista para crear un nuevo rol en el sistema.

    Muestra un formulario para ingresar el nombre y la descripción del rol.

    :param request: HttpRequest
    :return: HttpResponse con el formulario o redirección
    """
    if request.method == "POST":
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Rol creado exitosamente.")
            return redirect("usuarios:roles_list")
    else:
        form = RoleForm()
    return render(request, "usuarios/rol_form.html", {"form": form})


@login_required
@role_required("Admin")
def rol_edit(request, role_id):
    """
   Vista para editar los permisos de un rol (grupo).

   :param request: HttpRequest.
   :param group_id: ID del grupo a editar.
   :return: HttpResponse con el formulario de edición o redirección.
   """
    role = get_object_or_404(Role, pk=role_id)
    if request.method == "POST":
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, "Rol actualizado exitosamente.")
            return redirect("usuarios:roles_list")
    else:
        form = RoleForm(instance=role)
    return render(request, "usuarios/rol_form.html", {"form": form, "role": role})


@login_required
@role_required("Admin")
def rol_delete(request, role_id):
    """
    Vista para eliminar un rol del sistema.

    Muestra una confirmación y elimina el rol, mostrando cuántos usuarios se ven afectados.

    :param request: HttpRequest
    :param role_id: ID del rol a eliminar
    :return: HttpResponse con la confirmación o redirección
    """
    role = get_object_or_404(Role, pk=role_id)

    if request.method == "POST":
        # Contar usuarios afectados antes de eliminar
        users_count = role.user_roles.count()
        affected_users = [ur.user.email for ur in role.user_roles.all()]

        role.estado = EstadoRegistroEnum.ELIMINADO.value
        role.save()
        messages.success(request, "Role eliminado lógicamente.")

        return redirect("usuarios:roles_list")

    # Para GET request, mostrar página de confirmación
    return render(request, "usuarios/rol_delete_confirm.html", {"role": role})

@login_required
@role_required("Admin")
def role_restore(request, role_id):
    """
    Vista para restaurar un rol eliminado lógicamente.
    """
    role = get_object_or_404(Role, pk=role_id)
    if request.method == "POST":
        role.estado = EstadoRegistroEnum.ACTIVO.value
        role.save()
        messages.success(request, "Rol restaurado correctamente.")
        return redirect("usuarios:roles_list")
    return render(request, "usuarios/role_restore_confirm.html", {"role": role})

@login_required
@role_required("Admin")
def asignar_rol_a_usuario(request, user_id):
    """
    Vista para asignar roles (grupos) a un usuario.

    :param request: HttpRequest.
    :param user_id: ID del usuario.
    :return: HttpResponse con el formulario de asignación o redirección.
    """
    usuario = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        form = AsignarRolForm(request.POST, user=usuario)
        if form.is_valid():
            # Limpiar roles actuales del usuario
            UserRole.objects.filter(user=usuario).delete()

            # Asignar nuevos roles seleccionados
            selected_roles = form.cleaned_data['roles']
            for role_id in selected_roles:
                UserRole.objects.create(user=usuario, role_id=role_id)

            if selected_roles:
                messages.success(request, f"Roles asignados correctamente a {usuario.email}.")
            else:
                messages.info(request, f"Se eliminaron todos los roles de {usuario.email}.")
            return redirect("usuarios:usuarios_list")
    else:
        form = AsignarRolForm(user=usuario)

    return render(request, "usuarios/asignar_rol.html", {
        "form": form,
        "usuario": usuario
    })


@login_required
@role_required("Admin")
def ver_usuario_roles(request, user_id):
    """Vista para ver los roles de un usuario específico"""
    usuario = get_object_or_404(User, pk=user_id)
    roles_usuario = UserRole.objects.filter(user=usuario).select_related('role')

    return render(request, "usuarios/usuario_roles.html", {
        "usuario": usuario,
        "roles_usuario": roles_usuario
    })

@login_required
@role_required("Admin")
def asignar_clientes_a_usuario(request, user_id):
    """
    Vista para asignar clientes a un usuario específico.

    :param request: HttpRequest
    :param user_id: ID del usuario
    :return: HttpResponse con el formulario o redirección
    """
    usuario = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        form = AsignarClientesAUsuarioForm(request.POST, usuario=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f"Clientes asignados a {usuario.email}.")
            return redirect("usuarios:usuarios_list")
    else:
        form = AsignarClientesAUsuarioForm(usuario=usuario)
    return render(request, "usuarios/asignar_clientes.html", {"form": form, "usuario": usuario})

# Recuperación de contraseña

def password_reset_request(request):
    """Solicitar enlace de recuperación de contraseña"""
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            print(f"Email recibido: {email}")  # Para depuración

            try:
                user = User.objects.get(email=email)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_link = f"{settings.SITE_URL}/usuarios/reset/{uid}/{token}/"

                # Mostrar el enlace en la consola
                print("=" * 50)
                print("ENLACE DE RECUPERACIÓN DE CONTRASEÑA:")
                print(reset_link)
                print("=" * 50)

            except User.DoesNotExist:
                # Por seguridad, no revelamos si el email existe o no
                print(f"No se encontró usuario con email: {email}")

            # Siempre mostrar el mismo mensaje por seguridad
            messages.success(request,
                             "Si el correo existe en nuestro sistema, se generó un enlace de recuperación. Revisá la consola del servidor.")
            return redirect('usuarios:login')
    else:
        form = PasswordResetRequestForm()

    # Si es GET o el formulario es inválido, mostrar el formulario
    return render(request, "usuarios/password_reset_form.html", {'form': form})

def password_reset_done(request):
    """Confirmación de envío de correo"""
    return render(request, "usuarios/password_reset_done.html")


def password_reset_confirm(request, uidb64, token):
    """Resetear la contraseña usando el token"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError):
        messages.error(request, "Enlace inválido o expirado.")
        return redirect('usuarios:login')

    if not default_token_generator.check_token(user, token):
        messages.error(request, "Enlace inválido o expirado.")
        return redirect('usuarios:login')

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Contraseña actualizada correctamente. Ya podés iniciar sesión.")
            return redirect('usuarios:login')
        else:
            pass  # Los errores estarán en form.errors
    else:
        form = SetPasswordForm(user)

    return render(request, "usuarios/password_reset_confirm.html", {"form": form})
