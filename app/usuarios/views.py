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
from django.db.models import OuterRef, Subquery
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .decorators import role_required
from .forms import AsignarClientesAUsuarioForm, RegistroForm, LoginForm, UserForm, AsignarRolForm, RoleForm, UserCreateForm, PasswordResetRequestForm
from .models import Role, UserRole
from commons.enums import EstadoRegistroEnum
from clientes.models import Cliente
from monedas.models import TasaCambio, Moneda
from transaccion.models import Transaccion

User = get_user_model()


def dashboard_view(request):
    """
    Vista principal del dashboard.

    Muestra estadísticas generales de usuarios, roles y clientes.

    :param request: HttpRequest
    :return: HttpResponse con el dashboard
    """
    context = {}
    # Agregar el cliente activo de la sesión al contexto
    cliente_activo_id = request.session.get('cliente_activo')
    context['cliente_activo_id'] = cliente_activo_id
    if request.user.is_authenticated:
        total_usuarios = User.objects.count()
        usuarios_activos = User.objects.filter(is_active=True).count()
        total_roles = Role.objects.count()
        total_clientes = Cliente.objects.count()

        monedas_activas = Moneda.objects.filter(
            activa=True,
            es_base=False
        ).order_by('codigo')

        ultimas_cotizaciones = []
        for moneda in monedas_activas:
            ultima_tasa = TasaCambio.objects.filter(
                moneda=moneda,
                activa=True
            ).order_by('-fecha_creacion').first()

            if ultima_tasa:
                ultimas_cotizaciones.append(ultima_tasa)

        # Obtener totales para las tarjetas
        total_monedas = Moneda.objects.filter(activa=True).count()
        total_cotizaciones = TasaCambio.objects.count()
        total_transacciones = Transaccion.objects.count()

        context.update({
            'total_usuarios': total_usuarios,
            'total_clientes': total_clientes,
            'usuarios_activos': usuarios_activos,
            'total_roles': total_roles,
            'ultimas_cotizaciones': ultimas_cotizaciones,
            'total_monedas': total_monedas,
            'total_cotizaciones': total_cotizaciones,
            'total_transacciones': total_transacciones,
        })

        # Para el gráfico: monedas activas (no base)
        context['monedas_activas'] = list(monedas_activas)

    return render(request, "dashboard.html", context)


@login_required
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
            # If user has MFA enabled, generate a login OTP and require verification
            try:
                mfa_conf = getattr(user, 'mfa_config', None)
                if mfa_conf and getattr(mfa_conf, 'enabled', False):
                    # generate OTP for purpose 'login'
                    from mfa.services import generate_otp
                    otp = generate_otp(user, purpose='login')
                    # store pending login in session (short-lived)
                    request.session['mfa_login_pending'] = {
                        'user_pk': user.pk,
                        'otp_id': str(otp.id),
                    }
                    request.session.modified = True
                    return redirect('usuarios:login_verify')
            except Exception:
                # If MFA app not available or generation fails, fallback to normal login
                pass

            login(request, user)
            # Si el usuario no tiene MFA, se considera verificado.
            # Si tiene MFA, el flag se pondrá en la vista de verificación.
            if not (hasattr(user, 'user_mfa_profile') and user.user_mfa_profile.is_enabled):
                request.session['mfa_verified'] = True

            return redirect('usuarios:dashboard')
    else:
        form = LoginForm()
    return render(request, 'usuarios/login.html', {'form': form})


def login_verify(request):
    """
    View to verify OTP after credentials were validated and an OTP was generated.
    Uses session key 'mfa_login_pending' to know which user is pending.
    """
    pending = request.session.get('mfa_login_pending')
    if not pending:
        return redirect('usuarios:login')

    User = get_user_model()
    try:
        user = User.objects.get(pk=pending.get('user_pk'))
    except User.DoesNotExist:
        request.session.pop('mfa_login_pending', None)
        return redirect('usuarios:login')

    error = None
    ttl_seconds = None
    block_ttl_remaining = None # Nuevo: para el contador de bloqueo

    # --- Manejo de reenvío de código ---
    if request.method == 'POST' and 'resend_code' in request.POST:
        from mfa.services import generate_otp
        try:
            # Antes de intentar generar, comprobamos si ya está bloqueado
            from django.core.cache import cache
            block_key = f'mfa:block:{user.pk}:login'
            if cache.get(block_key):
                 block_ttl_remaining = cache.ttl(block_key)
                 error = f"Has solicitado demasiados códigos. Inténtalo de nuevo en {block_ttl_remaining // 60} minutos y {block_ttl_remaining % 60} segundos."
            else:
                generate_otp(user, purpose='login')
                messages.info(request, "Se ha enviado un nuevo código a tu correo.")
        except Exception as e:
            try:
                from django.core.exceptions import ValidationError
                if isinstance(e, ValidationError):
                    error = e.message # Usar el mensaje de la excepción
                    # Si el error es por bloqueo, extraemos el tiempo restante
                    block_key = f'mfa:block:{user.pk}:login'
                    from django.core.cache import cache
                    if cache.get(block_key):
                        block_ttl_remaining = cache.ttl(block_key)
                else:
                    error = str(e)
            except Exception:
                error = str(e)
    
    # --- Fin de manejo de reenvío ---

    # Obtener el OTP más reciente para calcular el TTL del código
    try:
        otp_id = pending.get('otp_id')
        from mfa.models import MfaOtp
        _otp = MfaOtp.objects.filter(user=user, purpose='login', used=False).order_by('-created_at').first()
        if _otp and getattr(_otp, 'expires_at', None):
            from django.utils import timezone
            ttl_seconds = max(int((_otp.expires_at - timezone.now()).total_seconds()), 0)
            # Actualizar el otp_id en sesión por si se reenvió
            pending['otp_id'] = str(_otp.id)
            request.session['mfa_login_pending'] = pending

    except Exception:
        ttl_seconds = None

    # --- Comprobar si el usuario está bloqueado (también para GET requests) ---
    if not block_ttl_remaining:
        from django.core.cache import cache
        block_key = f'mfa:block:{user.pk}:login'
        if cache.get(block_key):
            block_ttl_remaining = cache.ttl(block_key)
    # --- Fin de comprobación de bloqueo ---

    if request.method == 'POST' and 'verify_code' in request.POST:
        code = request.POST.get('code', '').strip()
        if not code:
            error = 'Ingrese el código.'
        else:
            # Quick server-side length check: expected length equals otp_length default (6)
            expected_len = int(getattr(settings, 'MFA_DEFAULT_LENGTH', 6))
            if len(code) < expected_len:
                error = f'El código debe tener {expected_len} dígitos.'
            else:
                try:
                    from mfa.services import verify_otp
                    ok, otp = verify_otp(user, purpose='login', raw_code=code)
                    if ok:
                        # OTP valid: complete login
                        login(request, user)
                        # clear pending and set mfa_verified flag
                        request.session.pop('mfa_login_pending', None)
                        request.session['mfa_verified'] = True
                        return redirect('usuarios:dashboard')
                    else:
                        error = 'Código inválido.'
                except Exception as e:
                    # keep the previously computed ttl_seconds so the frontend timer doesn't reset
                    # Map common validation error messages to friendly ones
                    try:
                        from django.core.exceptions import ValidationError
                        if isinstance(e, ValidationError):
                            msg = str(e)
                            low = msg.lower()
                            if 'expir' in low:
                                error = 'OTP expirado.'
                            elif 'maximo' in low or 'intentos' in low:
                                error = 'Máximo de intentos alcanzado para este código.'
                            else:
                                error = 'Código inválido.'
                        else:
                            error = str(e)
                    except Exception:
                        error = str(e)

    return render(request, 'usuarios/login_verify.html', {
        'usuario': user, 
        'error': error, 
        'ttl_seconds': ttl_seconds,
        'block_ttl_remaining': block_ttl_remaining # Pasar el tiempo de bloqueo al template
    })



@login_required
def security_settings(request):
    """Página de Seguridad: permite habilitar/deshabilitar MFA de inicio de sesión.

    Nota: los códigos OTP se muestran por terminal (simulación).
    """
    user = request.user
    # Obtener o crear configuración MFA mínima para mostrar estado
    mfa_enabled = False
    try:
        cfg = getattr(user, 'mfa_config', None)
        if cfg is None:
            from mfa.models import UserMfa
            cfg = UserMfa.objects.create(user=user, enabled=False, method='email', destination=user.email)
        mfa_enabled = bool(cfg.enabled)
    except Exception:
        # Si la app mfa no existe, tratamos como deshabilitado
        mfa_enabled = False

    message = None
    if request.method == 'POST':
        enable = request.POST.get('mfa_enabled') == 'on'
        method = request.POST.get('method') or 'email'
        destination = request.POST.get('destination') or request.user.email
        try:
            from mfa.models import UserMfa
            cfg, _ = UserMfa.objects.get_or_create(user=user, defaults={'enabled': False, 'method': method, 'destination': destination})
            was_enabled = bool(cfg.enabled)
            cfg.enabled = enable
            cfg.method = method
            cfg.destination = destination
            cfg.save()
            mfa_enabled = enable
            # Si se activa y antes estaba desactivado, generamos un OTP de verificación (simulado en terminal)
            if enable and not was_enabled:
                try:
                    from mfa.services import generate_otp
                    generate_otp(user, purpose='mfa_enable', method=method, destination=destination)
                except Exception:
                    pass
            message = 'Configuración actualizada.'
        except Exception:
            message = 'No se pudo actualizar la configuración de MFA.'

    return render(request, 'usuarios/security_settings.html', {'mfa_enabled': mfa_enabled, 'message': message})


@login_required
def perfil(request):
    """Mostrar la página de perfil del usuario (ajustes personales).

    Por ahora sólo renderiza la plantilla. Más adelante se puede enlazar el
    formulario de configuración de MFA y edición de datos.
    """
    # Redirigir a la vista de edición del usuario para mostrar el formulario completo
    try:
        return redirect('usuarios:usuario_edit', user_id=request.user.pk)
    except Exception:
        # Fallback: renderizar la plantilla simple si algo falla
        return render(request, 'usuarios/profile.html')


def logout_view(request):
    """
    Vista para cerrar la sesión del usuario.

    :param request: HttpRequest.
    :return: Redirección a la página de login.
    """
    logout(request)
    return redirect('landing')


@login_required
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
def asignar_rol_a_usuario(request, user_id):
    """
    Vista para asignar roles (grupos) a un usuario.

    :param request: HttpRequest.
    :param user_id: ID del usuario.
    :return: HttpResponse con el formulario de asignación o redirección.
    """
    usuario = get_object_or_404(User, pk=user_id)

    if not request.user.has_permission('roles.assign_to_user'):
        messages.error(request, 'No tienes permisos para asignar roles a usuarios.')
        return redirect('usuarios:usuarios_list')

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
def ver_usuario_roles(request, user_id):
    """Vista para ver los roles de un usuario específico"""
    usuario = get_object_or_404(User, pk=user_id)
    roles_usuario = UserRole.objects.filter(user=usuario).select_related('role')

    return render(request, "usuarios/usuario_roles.html", {
        "usuario": usuario,
        "roles_usuario": roles_usuario
    })

@login_required
def asignar_clientes_a_usuario(request, user_id):
    """
    Vista para asignar clientes a un usuario específico.

    :param request: HttpRequest
    :param user_id: ID del usuario
    :return: HttpResponse con el formulario o redirección
    """
    usuario = get_object_or_404(User, pk=user_id)
    if not request.user.has_permission('usuarios.asignar_clientes'):
        messages.error(request, 'No tienes permisos para asignar clientes a usuarios.')
        return redirect('usuarios:usuarios_list')
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
