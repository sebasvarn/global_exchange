
from django.test import TestCase
from unittest.mock import patch, MagicMock
from .utils import obtener_datos_transaccion
from .views import tramitar_transacciones, nuevo_tauser, lista_tausers

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
