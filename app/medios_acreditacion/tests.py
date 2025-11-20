from django.test import TestCase, Client
from django.urls import reverse
from .models import MedioAcreditacion
from clientes.models import Cliente
from django.contrib.auth import get_user_model

User = get_user_model()

class MedioAcreditacionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="1234")
        self.cliente = Cliente.objects.create(nombre="Cliente Test", tipo="MIN")
        self.cliente.usuarios.add(self.user)

    def test_create_medio_cuenta_bancaria(self):
        medio = MedioAcreditacion.objects.create(
            cliente=self.cliente,
            tipo_medio="cuenta_bancaria",
            banco="Banco Test",
            numero_cuenta="123456"
        )
        self.assertIn("Banco Test", str(medio))
        self.assertEqual(medio.cliente, self.cliente)

    def test_create_medio_billetera(self):
        medio = MedioAcreditacion.objects.create(
            cliente=self.cliente,
            tipo_medio="billetera",
            proveedor_billetera="PayPal",
            billetera_email_telefono="mail@test.com"
        )
        self.assertIn("PayPal", str(medio))


class MedioAcreditacionViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="test@test.com", password="1234")
        self.cliente = Cliente.objects.create(nombre="Cliente Test", tipo="MIN")
        self.cliente.usuarios.add(self.user)
        self.client.force_login(self.user)
        self.m1 = MedioAcreditacion.objects.create(
            cliente=self.cliente,
            tipo_medio="cuenta_bancaria",
            banco="Banco Test",
            numero_cuenta="123456"
        )
        self.m2 = MedioAcreditacion.objects.create(
            cliente=self.cliente,
            tipo_medio="billetera",
            proveedor_billetera="PayPal",
            billetera_email_telefono="mail@test.com"
        )

    def test_list_medios_by_client(self):
        response = self.client.get(reverse('medios_acreditacion:medios_by_client'))
        self.assertContains(response, self.cliente.nombre)
        self.assertContains(response, "Banco Test")
        self.assertContains(response, "PayPal")


    def test_delete_view(self):
        response = self.client.post(reverse('medios_acreditacion:medioacreditacion_delete', args=[self.m1.pk]))
        self.assertEqual(MedioAcreditacion.objects.filter(pk=self.m1.pk).count(), 0)

    def test_update_view(self):
        url = reverse('medios_acreditacion:medioacreditacion_update', args=[self.m2.pk])
        response = self.client.post(url, {
            'tipo_medio': 'billetera',
            'proveedor_billetera': 'MercadoPago',
            'billetera_email_telefono': 'nuevo@gmail.com',
            'billetera_titular': 'Juan Perez',
        })
        self.m2.refresh_from_db()
        self.assertEqual(self.m2.proveedor_billetera, 'MercadoPago')
