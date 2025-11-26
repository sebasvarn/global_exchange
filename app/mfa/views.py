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


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from transaccion.models import Transaccion
from transaccion.services import confirmar_transaccion
from .forms import OTPForm
from .services import verify_otp as verify_otp_service

@login_required
def verify_otp(request):
    purpose = request.session.get('mfa_purpose')
    context = request.session.get('mfa_context', {})

    if not purpose:
        messages.error(request, "No se encontró un propósito de MFA en la sesión.")
        return redirect('usuarios:dashboard')

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                is_valid, _ = verify_otp_service(request.user, purpose, code)
                if is_valid:
                    # Limpiar la sesión de MFA
                    del request.session['mfa_purpose']
                    if 'mfa_context' in request.session:
                        del request.session['mfa_context']

                    # Lógica específica según el propósito
                    if purpose == 'tauser_confirm_transaction':
                        tx_code = context.get('transaction_code')
                        if tx_code:
                            try:
                                tx = Transaccion.objects.get(codigo_verificacion=tx_code)
                                confirmar_transaccion(tx)
                                messages.success(request, f"Transacción #{tx.id} confirmada correctamente.")
                                return redirect('tauser:tramitar_transacciones')
                            except Transaccion.DoesNotExist:
                                messages.error(request, "La transacción a confirmar no fue encontrada.")
                            except Exception as e:
                                messages.error(request, f"Error al confirmar la transacción: {e}")
                        else:
                            messages.error(request, "No se encontró el código de la transacción en el contexto de MFA.")
                        return redirect('tauser:tramitar_transacciones')

                    # Redirección por defecto si no hay un manejo específico
                    messages.success(request, "Verificación completada con éxito.")
                    return redirect('usuarios:dashboard')

            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = OTPForm()

    return render(request, 'verify_otp.html', {'form': form})

@csrf_exempt
@login_required
@require_POST
def verify_tauser_transaction_otp(request):
    try:
        data = json.loads(request.body)
        code = data.get('code')
        purpose = data.get('purpose')

        if not code or not purpose:
            return JsonResponse({'ok': False, 'error': 'Faltan parámetros.'}, status=400)

        is_valid, _ = verify_otp_service(request.user, purpose, code)
        
        if is_valid:
            # Marcar el propósito de MFA como verificado en la sesión
            request.session[f'mfa_verified_{purpose}'] = True
            return JsonResponse({'ok': True, 'message': "Verificación exitosa."})
        else:
            # This case is handled by verify_otp_service raising an exception, but as a fallback:
            return JsonResponse({'ok': False, 'error': 'Código de verificación inválido.'}, status=400)

    except ValidationError as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error en verify_tauser_transaction_otp: {e}")
        return JsonResponse({'ok': False, 'error': 'Ocurrió un error inesperado.'}, status=500)

