from django.test import TestCase
from django.contrib.auth import get_user_model
from .services import generate_otp, verify_otp
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.cache import cache
import time

User = get_user_model()

class MfaServicesLogicTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='mfa_test@example.com', password='pass')

    def test_generate_and_verify_otp_invalid_code(self):
        otp = generate_otp(self.user, purpose='login', ttl_seconds=10)
        # Verificar que un código incorrecto no valida
        with self.assertRaises(ValidationError):
            verify_otp(self.user, 'login', '000000')

    def test_expired_otp(self):
        otp = generate_otp(self.user, purpose='login', ttl_seconds=1)
        time.sleep(2)
        with self.assertRaises(ValidationError):
            verify_otp(self.user, 'login', '000000')

