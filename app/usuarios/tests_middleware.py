from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from usuarios.middleware import MfaRequiredMiddleware
from mfa.models import UserMfa

User = get_user_model()

class MfaMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = MfaRequiredMiddleware(lambda req: self.client.get(reverse('dashboard')))
        self.user_with_mfa = User.objects.create_user(password='password123', email='testmfa@example.com')
        UserMfa.objects.create(user=self.user_with_mfa, method='email', enabled=True)
        self.user_without_mfa = User.objects.create_user(password='password123', email='testnomfa@example.com')

    def test_unauthenticated_user_is_not_redirected(self):
        """Los usuarios no autenticados no deben ser afectados por el middleware."""
        response = self.client.get(reverse('dashboard'))
        # Si la vista está protegida, debe redirigir a login (302)
        self.assertEqual(response.status_code, 302)

    def test_user_without_mfa_can_access_protected_page(self):
        """Los usuarios sin MFA activado deben poder acceder a las páginas."""
        self.client.login(email='testnomfa@example.com', password='password123')
        response = self.client.get(reverse('dashboard'), follow=True)
        self.assertEqual(response.status_code, 200)


    def test_user_with_mfa_verified_can_access_protected_page(self):
        """Los usuarios con MFA que han verificado pueden acceder a las páginas."""
        self.client.login(email='testmfa@example.com', password='password123')
        session = self.client.session
        session['mfa_verified'] = True
        session.save()
        response = self.client.get(reverse('dashboard'), follow=True)
        self.assertEqual(response.status_code, 200)

