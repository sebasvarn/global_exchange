from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import Moneda, TasaCambio
from decimal import Decimal

class MonedaModelTest(TestCase):
    """Pruebas unitarias para el modelo Moneda."""

    def setUp(self):
        self.moneda_base, _ = Moneda.objects.get_or_create(codigo='PYG', defaults={'nombre': 'Guaraní', 'es_base': True})
        self.moneda_usd, _ = Moneda.objects.get_or_create(codigo='USD', defaults={'nombre': 'Dólar'})

    def test_str_method(self):
        self.assertIn('PYG', str(self.moneda_base))
        self.assertIn('USD', str(self.moneda_usd))

    def test_unique_base_moneda(self):
        otra_base, _ = Moneda.objects.get_or_create(codigo='EUR', defaults={'nombre': 'Euro', 'es_base': True})
        self.moneda_base.refresh_from_db()
        # Solo PYG puede ser base, EUR no será base
        self.assertTrue(self.moneda_base.es_base)
        self.assertFalse(otra_base.es_base)

    def test_soft_delete(self):
        self.moneda_usd.delete()
        self.moneda_usd.refresh_from_db()
        self.assertFalse(self.moneda_usd.activa)

class TasaCambioModelTest(TestCase):
    """Pruebas unitarias para el modelo TasaCambio."""

    def setUp(self):
        self.moneda_usd, _ = Moneda.objects.get_or_create(codigo='USD', defaults={'nombre': 'Dólar'})
        self.tasa1 = TasaCambio.objects.create(
            moneda=self.moneda_usd,
            compra=7000,
            venta=7200,
            activa=True
        )

    def test_variacion_calculo(self):
        tasa2 = TasaCambio.objects.create(
            moneda=self.moneda_usd,
            compra=7100,
            venta=7300,
            activa=True
        )
        self.assertAlmostEqual(tasa2.variacion, Decimal('1.43'), places=2)

class MonedaViewsTest(TestCase):
    """Pruebas de vistas para la app monedas."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(email="test@monedas.com", password="testpass123", is_staff=True)
        self.client = Client()
        self.client.force_login(self.user)
        self.moneda_base, _ = Moneda.objects.get_or_create(codigo='PYG', defaults={'nombre': 'Guaraní', 'es_base': True})
        self.moneda_usd, _ = Moneda.objects.get_or_create(codigo='USD', defaults={'nombre': 'Dólar'})

    def test_monedas_list_view(self):
        response = self.client.get(reverse('monedas:monedas_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PYG')
        self.assertContains(response, 'USD')

    def test_moneda_create_view(self):
        response = self.client.post(reverse('monedas:moneda_create'), {
            'codigo': 'EUR',
            'nombre': 'Euro',
            'simbolo': '€',
            'decimales': 2,
            'activa': True
        })
        self.assertEqual(Moneda.objects.filter(codigo='EUR').count(), 1)

    def test_moneda_edit_view(self):
        response = self.client.post(reverse('monedas:moneda_edit', args=[self.moneda_usd.id]), {
            'codigo': 'USD',
            'nombre': 'Dólar Actualizado',
            'simbolo': '$',
            'decimales': 2,
            'activa': True
        })
        self.moneda_usd.refresh_from_db()
        self.assertEqual(self.moneda_usd.nombre, 'Dólar Actualizado')

    def test_moneda_delete_view(self):
        response = self.client.post(reverse('monedas:moneda_delete', args=[self.moneda_usd.id]))
        self.moneda_usd.refresh_from_db()
        self.assertFalse(self.moneda_usd.activa)

class TasaCambioViewsTest(TestCase):
    """Pruebas de vistas CRUD para TasaCambio y endpoints JSON."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(email="test@tasas.com", password="testpass123", is_staff=True)
        self.client = Client()
        self.client.force_login(self.user)
        self.moneda_usd, _ = Moneda.objects.get_or_create(codigo='USD', defaults={'nombre': 'Dólar'})
        # Limpiar tasas previas para evitar acumulación
        from .models import TasaCambio
        TasaCambio.objects.filter(moneda=self.moneda_usd).delete()
        self.tasa = TasaCambio.objects.create(moneda=self.moneda_usd, compra=7000, venta=7200, activa=True)

    def test_tasas_list_view(self):
        response = self.client.get(reverse('monedas:tasas_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'USD')

    def test_tasa_create_view(self):
        from datetime import timedelta
        ts_nuevo = (timezone.now() + timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M')
        response = self.client.post(reverse('monedas:tasa_create'), {
            'moneda': self.moneda_usd.id,
            'compra': 7100,
            'venta': 7300,
            'fuente': 'Banco Test',
            'ts_fuente': ts_nuevo,
            'activa': True
        })
        total = TasaCambio.objects.filter(moneda=self.moneda_usd).count()
        activas = TasaCambio.objects.filter(moneda=self.moneda_usd, activa=True).count()
        self.assertEqual(total, 1)
        self.assertEqual(activas, 1)

    def test_tasa_edit_view(self):
        response = self.client.post(reverse('monedas:tasa_edit', args=[self.tasa.id]), {
            'moneda': self.moneda_usd.id,
            'compra': 7050,
            'venta': 7250,
            'fuente': 'Banco Edit',
            'ts_fuente': timezone.now(),
            'activa': True
        })
        self.tasa.refresh_from_db()
        self.assertEqual(self.tasa.compra, Decimal('7050'))

    def test_tasa_delete_view(self):
        response = self.client.post(reverse('monedas:tasa_delete', args=[self.tasa.id]))
        self.assertFalse(TasaCambio.objects.filter(pk=self.tasa.id).exists())

    def test_cotizaciones_json_endpoint(self):
        response = self.client.get(reverse('monedas:cotizaciones_json'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('cotizaciones', response.json())

    def test_tasas_comisiones_json_endpoint(self):
        response = self.client.get(reverse('monedas:tasas_comisiones_json'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('tasas', response.json())
