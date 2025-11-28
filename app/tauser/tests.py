from django.test import TestCase
from unittest.mock import patch, MagicMock
from .utils import obtener_datos_transaccion
from .views import tramitar_transacciones, nuevo_tauser, lista_tausers
from decimal import Decimal
from .models import Tauser, Denominacion, TauserStock
from monedas.models import Moneda
from .services import validar_stock_tauser_para_transaccion
from django.urls import reverse
from django.test import Client

class TauserUtilsTests(TestCase):
	@patch('tauser.utils.Transaccion')
	@patch('tauser.utils.calcular_transaccion')
	def test_obtener_datos_transaccion_ok(self, mock_calcular, mock_transaccion):
		mock_tx = MagicMock()
		mock_tx.tipo = 'COMPRA'
		mock_tx.moneda.codigo = 'USD'
		mock_tx.tasa_aplicada = 100
		mock_tx.cliente = 'cliente1'
		mock_tx.tipo = 'COMPRA'
		mock_tx.moneda = MagicMock()
		mock_tx.moneda.codigo = 'USD'
		mock_tx.monto_operado = 500
		mock_transaccion.objects.select_related.return_value.get.return_value = mock_tx
		mock_calcular.return_value = {'tasa_aplicada': 101}
		res = obtener_datos_transaccion(1)
		self.assertEqual(res['tipo'], 'COMPRA')
		self.assertEqual(res['moneda']['codigo'], 'USD')
		self.assertEqual(res['tasa'], 100)
		self.assertEqual(res['tasa_recalculada'], 101)

	@patch('tauser.utils.Transaccion')
	def test_obtener_datos_transaccion_not_found(self, mock_transaccion):
		mock_transaccion.objects.select_related.return_value.get.side_effect = Exception()
		res = None
		try:
			res = obtener_datos_transaccion(999)
		except Exception:
			res = None
		self.assertIsNone(res)

class ValidarStockTauserTests(TestCase):
    def setUp(self):
        self.moneda, _ = Moneda.objects.get_or_create(codigo='USD', defaults={'nombre': 'Dólar', 'simbolo': '$', 'decimales': 2})
        self.tauser = Tauser.objects.create(ubicacion='Sucursal 1')
        self.den_100, _ = Denominacion.objects.get_or_create(moneda=self.moneda, value=Decimal('100'), type=Denominacion.BILL)
        self.den_50, _ = Denominacion.objects.get_or_create(moneda=self.moneda, value=Decimal('50'), type=Denominacion.BILL)
        TauserStock.objects.create(tauser=self.tauser, denominacion=self.den_100, quantity=2)  # 200
        TauserStock.objects.create(tauser=self.tauser, denominacion=self.den_50, quantity=1)   # 50

    def test_stock_suficiente(self):
        res = validar_stock_tauser_para_transaccion(self.tauser.id, Decimal('150'), self.moneda.id)
        self.assertTrue(res['ok'])
        self.assertEqual(res['faltante'], Decimal('0'))
        self.assertIn((Decimal('100'), 1), res['entregado'])
        self.assertIn((Decimal('50'), 1), res['entregado'])

    def test_stock_insuficiente(self):
        res = validar_stock_tauser_para_transaccion(self.tauser.id, Decimal('300'), self.moneda.id)
        self.assertFalse(res['ok'])
        self.assertEqual(res['faltante'], Decimal('50'))

    def test_tauser_no_encontrado(self):
        res = validar_stock_tauser_para_transaccion(999, Decimal('100'), self.moneda.id)
        self.assertFalse(res['ok'])
        self.assertIn('Tauser no encontrado', res['mensaje'])

    def test_moneda_no_encontrada(self):
        res = validar_stock_tauser_para_transaccion(self.tauser.id, Decimal('100'), 999)
        self.assertFalse(res['ok'])
        self.assertIn('Moneda no encontrada', res['mensaje'])

class TauserViewsSimpleTests(TestCase):
    def setUp(self):
        self.tauser = Tauser.objects.create(ubicacion='Sucursal test')
        self.client = Client()

    def test_lista_tausers_get(self):
        url = reverse('tauser:lista_tausers')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('tausers', response.context)

    def test_nuevo_tauser_get(self):
        url = reverse('tauser:nuevo_tauser')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_nuevo_tauser_post(self):
        url = reverse('tauser:nuevo_tauser')
        data = {'ubicacion': 'Sucursal nueva', 'estado': 'activo'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('mensaje', response.context)
        self.assertTrue(Tauser.objects.filter(ubicacion='Sucursal nueva').exists())
