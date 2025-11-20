from django.test import TestCase, Client
from django.urls import reverse
from .models import PaymentMethod
from commons.enums import PaymentTypeEnum
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
			payment_type=PaymentTypeEnum.CUENTA_BANCARIA.value,
			banco="Banco Test",
			numero_cuenta="123456"
		)
		self.assertIn("Banco Test", str(pm))
		self.assertIn("123456", str(pm))
		self.assertEqual(pm.cliente, self.cliente)

	def test_create_payment_method_billetera(self):
		pm = PaymentMethod.objects.create(
			cliente=self.cliente,
			payment_type=PaymentTypeEnum.BILLETERA.value,
			proveedor_billetera="PayPal",
			billetera_email_telefono="mail@test.com"
		)
		self.assertIn("PayPal", str(pm))
		self.assertIn("mail@test.com", str(pm))

	def test_create_payment_method_tarjeta(self):
		pm = PaymentMethod.objects.create(
			cliente=self.cliente,
			payment_type=PaymentTypeEnum.TARJETA.value,
			tarjeta_nombre="Test User",
			tarjeta_numero="4111111111111111"
		)
		self.assertIn("Test User", str(pm))
		self.assertIn("4111111111111111", str(pm))

	def test_str_cheque(self):
		pm = PaymentMethod.objects.create(
			cliente=self.cliente,
			payment_type=PaymentTypeEnum.CHEQUE.value,
			cheque_banco="BancoCheque",
			cheque_cuenta="987654",
			cheque_numero="5555"
		)
		self.assertIn("BancoCheque", str(pm))
		self.assertIn("987654", str(pm))
		self.assertIn("5555", str(pm))


class PaymentMethodViewsTest(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(email="test@test.com", password="1234")
		self.cliente = Cliente.objects.create(nombre="Cliente Test", tipo="MIN")
		self.cliente.usuarios.add(self.user)
		self.client.force_login(self.user)
		self.pm1 = PaymentMethod.objects.create(
			cliente=self.cliente,
			payment_type=PaymentTypeEnum.CUENTA_BANCARIA.value,
			banco="Banco Test",
			numero_cuenta="123456"
		)
		self.pm2 = PaymentMethod.objects.create(
			cliente=self.cliente,
			payment_type=PaymentTypeEnum.BILLETERA.value,
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
			'payment_type': PaymentTypeEnum.TARJETA.value,
			'tarjeta_nombre': 'Test User',
			'tarjeta_numero': '4111111111111111',
			'tarjeta_vencimiento': '2030-12',
			'tarjeta_cvv': '123',
			'tarjeta_marca': 'Visa',
		})
		self.assertEqual(PaymentMethod.objects.filter(tarjeta_nombre='Test User').count(), 1)

	def test_delete_view(self):
		response = self.client.post(reverse('payments:paymentmethod_delete', args=[self.pm1.pk]))
		self.assertEqual(PaymentMethod.objects.filter(pk=self.pm1.pk).count(), 0)

	def test_update_view(self):
		url = reverse('payments:paymentmethod_update', args=[self.pm2.pk])
		response = self.client.post(url, {
			'payment_type': PaymentTypeEnum.BILLETERA.value,
			'proveedor_billetera': 'MercadoPago',
			'billetera_email_telefono': 'nuevo@gmail.com',
			'billetera_titular': 'Juan Perez',
		})
		self.pm2.refresh_from_db()
		self.assertEqual(self.pm2.proveedor_billetera, 'MercadoPago')
