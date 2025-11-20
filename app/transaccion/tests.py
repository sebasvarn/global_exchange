"""
Pruebas unitarias de transacciones
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.urls import reverse

from clientes.models import Cliente, LimitePYG, LimiteMoneda
from monedas.models import Moneda
from payments.models import PaymentMethod
from transaccion.models import Transaccion, Movimiento
from transaccion.forms import TransaccionForm
from transaccion.services import (
    crear_transaccion,
    cancelar_transaccion,
    confirmar_transaccion,
    validate_limits,
)
from commons.enums import (
    TipoTransaccionEnum,
    EstadoTransaccionEnum,
    PaymentTypeEnum,
    TipoMovimientoEnum,
)


class TransaccionModelTest(TestCase):
    """
    Pruebas unitarias para el modelo Transaccion.
    """
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre="Cliente Test", tipo="MIN")
        self.moneda = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.payment = PaymentMethod.objects.create(
            cliente=self.cliente,
            payment_type=PaymentTypeEnum.CUENTA_BANCARIA.value,
            banco="Test Bank",
            numero_cuenta="12345"
        )
        self.transaccion = Transaccion.objects.create(
            cliente=self.cliente,
            moneda=self.moneda,
            tipo=TipoTransaccionEnum.COMPRA,
            monto_operado=Decimal("100"),
            monto_pyg=Decimal("730000"),
            tasa_aplicada=Decimal("7300"),
            comision=Decimal("50"),
            medio_pago=self.payment,
            estado=EstadoTransaccionEnum.PENDIENTE,
        )

    def test_transaccion_str(self):
        """
        Verifica la representación en string de una transacción.
        """
        self.assertIn("Compra", str(self.transaccion))
        self.assertIn("USD", str(self.transaccion))


class LimitValidationTest(TestCase):
    """
    Pruebas de validaciones de límites.
    """
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre="Cliente Limite", tipo="MIN")
        self.moneda = Moneda.objects.create(codigo="USD", nombre="Dólar")

    def test_excede_limite_pyg(self):
        LimitePYG.objects.create(cliente=self.cliente, max_por_operacion=Decimal("1000"))
        with self.assertRaises(ValidationError):
            validate_limits(self.cliente, self.moneda, Decimal("50"), Decimal("2000"))

    def test_excede_limite_moneda(self):
        LimiteMoneda.objects.create(cliente=self.cliente, moneda=self.moneda, max_por_operacion=Decimal("100"))
        with self.assertRaises(ValidationError):
            validate_limits(self.cliente, self.moneda, Decimal("200"), Decimal("1400000"))

    def test_error_excede_limite_pyg_forzado(self):
        """
        Límite por operación = 5.000 PYG.
        Probar con 1.400.000 PYG -> debe FALLAR (ValidationError).
        """
        LimitePYG.objects.create(cliente=self.cliente, max_por_operacion=Decimal("5000"))
        # El valor de moneda (200 USD) no afecta este chequeo; el que dispara es monto_pyg
        with self.assertRaisesMessage(ValidationError, "excede el límite por operación"):
            validate_limits(self.cliente, self.moneda, Decimal("200"), Decimal("1400000"))

    def test_ok_no_excede_limite_pyg(self):
        """
        Caso válido: subir el límite o bajar el monto_pyg para que NO falle.
        """
        LimitePYG.objects.create(cliente=self.cliente, max_por_operacion=Decimal("2000000"))
        LimiteMoneda.objects.create(cliente=self.cliente, moneda=self.moneda, max_por_operacion=Decimal("500"))
        # 1.400.000 PYG <= 2.000.000 PYG -> NO debe lanzar error
        try:
            validate_limits(self.cliente, self.moneda, Decimal("200"), Decimal("1400000"))
        except ValidationError:
            self.fail("La validación no debería fallar")

class ServiceFunctionsTest(TestCase):
    """
    Pruebas para las funciones de servicio de transacciones.
    """
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre="Cliente Servicios", tipo="MIN")
        self.moneda = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.payment = PaymentMethod.objects.create(
            cliente=self.cliente,
            payment_type=PaymentTypeEnum.CUENTA_BANCARIA.value,
            banco="Bank",
            numero_cuenta="999"
        )
        self.transaccion = Transaccion.objects.create(
            cliente=self.cliente,
            moneda=self.moneda,
            tipo=TipoTransaccionEnum.COMPRA,
            monto_operado=Decimal("100"),
            monto_pyg=Decimal("730000"),
            tasa_aplicada=Decimal("7300"),
            comision=Decimal("50"),
            medio_pago=self.payment,
            estado=EstadoTransaccionEnum.PENDIENTE,
        )

    def test_cancelar_transaccion(self):
        cancelar_transaccion(self.transaccion)
        self.transaccion.refresh_from_db()
        self.assertEqual(self.transaccion.estado, EstadoTransaccionEnum.CANCELADA)

    def test_confirmar_transaccion_crea_movimiento(self):
        confirmar_transaccion(self.transaccion)
        mov = Movimiento.objects.get(transaccion=self.transaccion)
        self.assertEqual(mov.tipo, TipoMovimientoEnum.DEBITO)
        self.assertEqual(mov.cliente, self.cliente)


class TransaccionFormTest(TestCase):
    """
    Pruebas unitarias para el formulario de transacción.
    """
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre="Cliente Form", tipo="MIN")
        self.moneda = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.payment = PaymentMethod.objects.create(
            cliente=self.cliente,
            payment_type=PaymentTypeEnum.CUENTA_BANCARIA.value,
            banco="FormBank",
            numero_cuenta="123"
        )

    def test_valid_form(self):
        data = {
            "cliente": self.cliente.id,
            "tipo": TipoTransaccionEnum.COMPRA,
            "moneda": self.moneda.id,
            "monto_operado": "100",
            "medio_pago": self.payment.id,
        }
        form = TransaccionForm(data)
        self.assertTrue(form.is_valid())

    def test_invalid_form_missing_fields(self):
        data = {
            "cliente": self.cliente.id,
            "tipo": "",
            "moneda": self.moneda.id,
            "monto_operado": "",
        }
        form = TransaccionForm(data)
        self.assertFalse(form.is_valid())


class TransaccionViewsTest(TestCase):
    """
    Pruebas unitarias para las vistas de transacciones.
    """
    def setUp(self):
        self.client_http = Client()
        self.cliente = Cliente.objects.create(nombre="Cliente Vista", tipo="MIN")
        self.moneda = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.payment = PaymentMethod.objects.create(
            cliente=self.cliente,
            payment_type=PaymentTypeEnum.CUENTA_BANCARIA.value,
            banco="Bank",
            numero_cuenta="12345"
        )

    def test_transacciones_list_view(self):
        url = reverse("transacciones:transacciones_list")
        response = self.client_http.get(url)
        self.assertEqual(response.status_code, 200)

    def test_transaccion_create_view_post(self):
        url = reverse("transacciones:transaccion_create")
        data = {
            "cliente": self.cliente.id,
            "tipo": TipoTransaccionEnum.COMPRA,
            "moneda": self.moneda.id,
            "monto_operado": "100",
            "medio_pago": self.payment.id,
        }
        response = self.client_http.post(url, data)
        self.assertIn(response.status_code, [200, 302]) 
