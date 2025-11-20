from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
import uuid


class UserMfa(models.Model):
    """Configuración de MFA por usuario."""
    METHOD_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mfa_config')
    enabled = models.BooleanField(default=False)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='email')
    destination = models.CharField(max_length=255, blank=True, null=True, help_text='Email o teléfono donde enviar OTP (opcional).')

    def __str__(self):
        return f"MFA {self.user.email} - {'enabled' if self.enabled else 'disabled'}"


class MfaOtp(models.Model):
    """Registro de códigos OTP emitidos (simulación)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mfa_otps')
    purpose = models.CharField(max_length=50, help_text='Propósito del OTP, ej: transaction_debit, login')
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)
    used = models.BooleanField(default=False)
    method = models.CharField(max_length=10, default='email')
    destination = models.CharField(max_length=255, blank=True, null=True)
    context = models.JSONField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'purpose', 'created_at'])]

    def set_code(self, raw_code: str):
        self.code_hash = make_password(raw_code)

    def verify_code(self, raw_code: str) -> bool:
        if self.used:
            return False
        return check_password(raw_code, self.code_hash)

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
