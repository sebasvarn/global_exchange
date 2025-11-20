from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
import json

from .services import generate_otp, verify_otp
import logging
import sys

logger = logging.getLogger(__name__)

User = get_user_model()


@require_POST
def generate_otp_view(request):
    """
    POST: {"email": "user@example.com", "purpose": "transaction_debit"}
    Genera un OTP para el usuario y lo imprime en terminal.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"error": "invalid_json"}, status=400)

    email = data.get('email')
    purpose = data.get('purpose')
    if not email or not purpose:
        return JsonResponse({"error": "missing_parameters"}, status=400)

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return JsonResponse({"error": "user_not_found"}, status=404)

    try:
        logger.info(f"generate_otp_view called for email={email} purpose={purpose}")
        otp = generate_otp(user, purpose)
        # best-effort flush in case stdout is buffered in this environment
        try:
            sys.stdout.flush()
        except Exception:
            pass
        # compute remaining ttl from model expires_at
        now = timezone.now()
        ttl_seconds = max(int((otp.expires_at - now).total_seconds()), 0) if getattr(otp, 'expires_at', None) else None
        return JsonResponse({"ok": True, "otp_id": str(otp.id), "ttl_seconds": ttl_seconds})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def verify_otp_view(request):
    """
    POST: {"email": "user@example.com", "purpose": "transaction_debit", "code": "123456"}
    Verifica el OTP y devuelve estado.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"error": "invalid_json"}, status=400)

    email = data.get('email')
    purpose = data.get('purpose')
    code = data.get('code')
    if not email or not purpose or not code:
        return JsonResponse({"error": "missing_parameters"}, status=400)

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return JsonResponse({"error": "user_not_found"}, status=404)

    try:
        ok, otp = verify_otp(user, purpose, code)
        return JsonResponse({"ok": True, "otp_id": str(otp.id)})
    except ValidationError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
