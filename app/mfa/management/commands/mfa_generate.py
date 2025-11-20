from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from mfa.services import generate_otp

User = get_user_model()


class Command(BaseCommand):
    help = 'Genera un OTP para un usuario (simulación por terminal).'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email del usuario')
        parser.add_argument('--purpose', type=str, default='login', help='Propósito del OTP (ej: login,transaction_debit)')
        parser.add_argument('--ttl', type=int, default=300, help='TTL en segundos')

    def handle(self, *args, **options):
        email = options['email']
        purpose = options['purpose']
        ttl = options['ttl']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f'Usuario no encontrado: {email}')

        otp = generate_otp(user, purpose=purpose, ttl_seconds=ttl)
        self.stdout.write(self.style.SUCCESS(f'OTP generado para {email} (id={otp.id})'))
