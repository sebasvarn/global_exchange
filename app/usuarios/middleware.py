from django.urls import reverse
from django.shortcuts import redirect
from django.conf import settings

class MfaRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_urls = [
            reverse('usuarios:login'),
            reverse('usuarios:login_verify'),
            reverse('usuarios:logout'),
            # Agrega aquí otras URLs que no requieran MFA, como la de registro si la tuvieras
        ]
        # También puedes exentar URLs que empiecen con un prefijo, como /admin/
        self.exempt_prefixes = ('/admin/',)


    def __call__(self, request):
        # No aplicar el middleware para URLs exentas
        if request.path_info in self.exempt_urls or request.path_info.startswith(self.exempt_prefixes):
            return self.get_response(request)

        # Si el usuario está autenticado pero no ha verificado MFA en la sesión
        if request.user.is_authenticated and not request.session.get('mfa_verified', False):
            # Y si el usuario tiene MFA habilitado en su perfil
            has_mfa_enabled = hasattr(request.user, 'user_mfa_profile') and request.user.user_mfa_profile.is_enabled

            if has_mfa_enabled:
                # Redirigir a la página de verificación de MFA
                return redirect(reverse('usuarios:login_verify'))

        return self.get_response(request)
