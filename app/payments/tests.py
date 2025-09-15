

from django.test import TestCase, Client
from django.urls import reverse
from .models import PaymentMethod
from clientes.models import Cliente
from django.contrib.auth import get_user_model

User = get_user_model()

class PaymentMethodModelTest(TestCase):
	"""
	Pruebas unitarias para el modelo PaymentMethod.
	"""
	def setUp(self):
		self.user = User.objects.create_user(email="test@test.com", password="1234")
		self.cliente = Cliente.objects.create(nombre="Cliente Test", tipo="MIN")
		self.cliente.usuarios.add(self.user)

	def test_create_payment_method_cuenta_bancaria(self):
		pm = PaymentMethod.objects.create(
			cliente=self.cliente,
			payment_type="cuenta_bancaria",
			banco="Banco Test",
			numero_cuenta="123456"
		)
		self.assertIn("Banco Test", str(pm))
		self.assertEqual(pm.cliente, self.cliente)

	def test_create_payment_method_billetera(self):
		pm = PaymentMethod.objects.create(
			cliente=self.cliente,
			payment_type="billetera",
			proveedor_billetera="PayPal",
			billetera_email_telefono="mail@test.com"
		)
		self.assertIn("PayPal", str(pm))

	def test_create_payment_method_tarjeta(self):
		pm = PaymentMethod.objects.create(
			cliente=self.cliente,
			payment_type="tarjeta",
			tarjeta_nombre="Test User",
			tarjeta_numero="4111111111111111"
		)
		self.assertIn("Test User", str(pm))


class PaymentMethodViewsTest(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(email="test@test.com", password="1234")
		self.cliente = Cliente.objects.create(nombre="Cliente Test", tipo="MIN")
		self.cliente.usuarios.add(self.user)
		self.client.login(email="test@test.com", password="1234")
		self.pm1 = PaymentMethod.objects.create(
			cliente=self.cliente,
			payment_type="cuenta_bancaria",
			banco="Banco Test",
			numero_cuenta="123456"
		)
		self.pm2 = PaymentMethod.objects.create(
			cliente=self.cliente,
			payment_type="billetera",
			proveedor_billetera="PayPal",
			billetera_email_telefono="mail@test.com"
		)

	def test_list_methods_by_client(self):
		response = self.client.get(reverse('payments:payment_methods_by_client'))
		self.assertContains(response, self.cliente.nombre)
		self.assertContains(response, "Banco Test")
		self.assertContains(response, "PayPal")

	def test_create_payment_method_view(self):
		url = reverse('payments:paymentmethod_create') + f'?cliente={self.cliente.id}'
		response = self.client.post(url, {
			'payment_type': 'tarjeta',
			'tarjeta_nombre': 'Test User',
			'tarjeta_numero': '4111111111111111',
			'tarjeta_vencimiento': '12/30',
			'tarjeta_cvv': '123',
		})
		self.assertEqual(PaymentMethod.objects.filter(tarjeta_nombre='Test User').count(), 1)

	def test_delete_view(self):
		response = self.client.post(reverse('payments:paymentmethod_delete', args=[self.pm1.pk]))
		self.assertEqual(PaymentMethod.objects.filter(pk=self.pm1.pk).count(), 0)

	def test_update_view(self):
		url = reverse('payments:paymentmethod_update', args=[self.pm2.pk])
		response = self.client.post(url, {
			'payment_type': 'billetera',
			'proveedor_billetera': 'MercadoPago',
			'billetera_email_telefono': 'nuevo@mail.com',
		})
		self.pm2.refresh_from_db()
		self.assertEqual(self.pm2.proveedor_billetera, 'MercadoPago')
