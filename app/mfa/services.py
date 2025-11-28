"""Servicios para generar y verificar OTPs (simulación por terminal)."""
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import MfaOtp, UserMfa
from django.db import transaction
import random
import logging
import sys

logger = logging.getLogger(__name__)


def _random_numeric_code(length=6):
    start = 10 ** (length - 1)
    end = (10 ** length) - 1
    return str(random.randint(start, end))


def _send_otp_by_email(user, raw_code, purpose, expires_at, destination):
    """Envia el código OTP por correo electrónico."""
    try:
        subject = f"Tu código de verificación para {purpose}"
        context = {
            'user': user,
            'raw_code': raw_code,
            'purpose': purpose,
            'expires_at': expires_at,
        }
        body = render_to_string('mfa/email/otp_body.txt', context)

        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destination],
            fail_silently=False,
        )
        logger.info(f"OTP enviado por email a {destination} para el usuario {user.email}")
    except Exception as e:
        logger.error(f"Error al enviar email de OTP a {destination} para el usuario {user.email}: {e}")
        # Consider raising the exception if email failure should stop the process
        # For now, just logging the error.

def generate_otp(user, purpose, method=None, destination=None, length=6, ttl_seconds=None, context=None, max_attempts=None):
    """
    Genera y persiste un OTP para un usuario, aplicando rate limiting y enviando el código por el método configurado.

    Args:
        user (User): Usuario para el que se genera el OTP.
        purpose (str): Propósito del OTP (ej: 'login', 'transacción').
        method (str, optional): Método de envío ('email', 'sms').
        destination (str, optional): Destino del OTP (email o teléfono).
        length (int, optional): Longitud del código OTP.
        ttl_seconds (int, optional): Tiempo de vida del OTP en segundos.
        context (dict, optional): Contexto adicional para el OTP.
        max_attempts (int, optional): Máximo de intentos permitidos.

    Returns:
        MfaOtp: Instancia creada del OTP.

    Raises:
        ValidationError: Si se supera el límite de reenvíos o el usuario está bloqueado.
    """
    # --- Rate Limiting para Reenvíos ---
    resend_limit = getattr(settings, 'MFA_RESEND_LIMIT', 3)
    block_ttl = getattr(settings, 'MFA_RESEND_BLOCK_TTL', 900)
    
    # Claves para la caché
    block_key = f'mfa:block:{user.pk}:{purpose}'
    count_key = f'mfa:resend_count:{user.pk}:{purpose}'

    # 1. Comprobar si el usuario está bloqueado
    if cache.get(block_key):
        block_ttl_remaining = cache.ttl(block_key)
        raise ValidationError(f"Has solicitado demasiados códigos. Inténtalo de nuevo en {block_ttl_remaining // 60} minutos y {block_ttl_remaining % 60} segundos.")

    # 2. Comprobar el contador de reenvíos
    resend_count = cache.get(count_key, 0)
    if resend_count >= resend_limit:
        # Bloquear al usuario y lanzar error
        cache.set(block_key, True, timeout=block_ttl)
        cache.delete(count_key) # Limpiar el contador una vez que se bloquea
        raise ValidationError(f"Has superado el límite de reenvíos. Inténtalo de nuevo en {block_ttl // 60} minutos.")

    # Incrementar el contador de reenvíos (con un TTL igual al del bloqueo para que expire)
    cache.set(count_key, resend_count + 1, timeout=block_ttl)
    
    # --- Fin de Rate Limiting ---

    # Determinar método y destino desde la configuración del usuario si no se especifica
    if method is None or destination is None:
        try:
            user_mfa_config = user.mfa_config
            if method is None:
                method = user_mfa_config.method
            if destination is None:
                destination = user_mfa_config.destination or user.email
        except UserMfa.DoesNotExist:
            method = method or 'sms' # Default a SMS (terminal) si no hay config
            destination = destination or user.email

    # Aplicar valores por defecto desde settings si no se proveen
    if ttl_seconds is None:
        ttl_seconds = getattr(settings, 'MFA_DEFAULT_TTL_SECONDS', 300)
    if max_attempts is None:
        max_attempts = getattr(settings, 'MFA_MAX_ATTEMPTS', 5)

    raw_code = _random_numeric_code(length=length)
    expires_at = timezone.now() + timedelta(seconds=ttl_seconds)

    with transaction.atomic():
        otp = MfaOtp.objects.create(
            user=user,
            purpose=purpose,
            expires_at=expires_at,
            attempts=0,
            max_attempts=max_attempts,
            method=method,
            destination=destination,
            context=context or {},
            code_hash=''
        )
        otp.set_code(raw_code)
        otp.save(update_fields=['code_hash'])

    # --- Punto de Decisión: Enviar por email o mostrar en terminal ---
    if method == 'email':
        _send_otp_by_email(user, raw_code, purpose, expires_at, destination)
    else: # Para 'sms' o cualquier otro método, usar la simulación por terminal
        logger.info('=' * 60)
        logger.info(f'OTP (simulación para método "{method}") generado para user={user.email} purpose={purpose}')
        logger.warning(f'Código: {raw_code}')
        logger.info('=' * 60)
        # Imprimir en terminal para visibilidad en desarrollo
        print('=' * 60, file=sys.stderr)
        print(f'----- SIMULACIÓN DE ENVÍO MFA ({method.upper()}) -----', file=sys.stderr)
        print(f"Usuario: {user.email}", file=sys.stderr)
        print(f"Código: {raw_code}", file=sys.stderr)
        print(f"Destino: {destination}", file=sys.stderr)
        print('=' * 60, file=sys.stderr)
        sys.stderr.flush()

    # Imprimir siempre en consola si estamos en modo DEBUG (desarrollo)
    if settings.DEBUG:
        print('\n' + '=' * 60, file=sys.stderr)
        print(f'MFA CODE (DEBUG MODE)', file=sys.stderr)
        print(f'Usuario: {user.email}', file=sys.stderr)
        print(f'Propósito: {purpose}', file=sys.stderr)
        print(f'Método: {method}', file=sys.stderr)
        print(f'Destino: {destination}', file=sys.stderr)
        print(f'CÓDIGO: {raw_code}', file=sys.stderr)
        print(f'Expira: {expires_at.strftime("%H:%M:%S")}', file=sys.stderr)
        print('=' * 60 + '\n', file=sys.stderr)
        sys.stderr.flush()

    return otp


def verify_otp(user, purpose, raw_code, context_match=None):
    """
    Verifica el código OTP más reciente para un usuario y propósito.

    Args:
        user (User): Usuario que verifica el OTP.
        purpose (str): Propósito del OTP.
        raw_code (str): Código OTP ingresado por el usuario.
        context_match (dict, optional): Contexto a validar contra el OTP guardado.

    Returns:
        tuple: (True, otp) si es válido.

    Raises:
        ValidationError: Si el OTP no es válido, está expirado, o no corresponde al contexto.
    """
    otps = MfaOtp.objects.filter(user=user, purpose=purpose, used=False).order_by('-created_at')
    if not otps.exists():
        raise ValidationError('No OTP disponible. Generá uno primero.')

    otp = otps.first()

    # Matchar contexto si se proporcionó
    if context_match and otp.context:
        for k, v in context_match.items():
            if otp.context.get(k) != v:
                raise ValidationError('OTP no corresponde al contexto esperado.')

    if otp.is_expired():
        raise ValidationError('OTP expirado.')

    if otp.attempts >= otp.max_attempts:
        raise ValidationError('Máximo de intentos alcanzado para este OTP.')

    # incrementar intentos y verificar
    otp.attempts += 1
    otp.save(update_fields=['attempts'])

    if otp.verify_code(raw_code):
        otp.used = True
        otp.save(update_fields=['used'])
        # Limpiar el contador de reenvíos si la verificación es exitosa
        count_key = f'mfa:resend_count:{user.pk}:{purpose}'
        cache.delete(count_key)
        return True, otp

    raise ValidationError('Código OTP inválido.')
