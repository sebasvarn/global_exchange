import uuid
from django.db import models

from payments.models import PaymentMethod
from clientes.models import Cliente
from commons.enums import TipoTransaccionEnum, EstadoTransaccionEnum, TipoMovimientoEnum
from medios_acreditacion.models import MedioAcreditacion
from monedas.models import Moneda


class Transaccion(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True, blank=True)
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE,
        related_name="transacciones", verbose_name="Cliente"
    )
    moneda = models.ForeignKey(
        Moneda, on_delete=models.CASCADE,
        related_name="transacciones", verbose_name="Moneda"
    )

    tipo = models.CharField(
        max_length=10,
        choices=TipoTransaccionEnum.choices
    )
    medio_pago = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name="transacciones",
        verbose_name="Medio de Pago",
        null=True,   
        blank=True,
    )
    monto_operado = models.DecimalField(max_digits=18, decimal_places=2)
    monto_pyg = models.DecimalField(max_digits=18, decimal_places=2)
    tasa_aplicada = models.DecimalField(max_digits=18, decimal_places=4)
    comision = models.DecimalField(max_digits=18, decimal_places=2)

    estado = models.CharField(
        max_length=15,
        choices=EstadoTransaccionEnum.choices,
        default=EstadoTransaccionEnum.PENDIENTE
    )
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.id} | {self.uuid} | {self.get_tipo_display()} {self.moneda} - {self.cliente}"


class Movimiento(models.Model):
    transaccion = models.ForeignKey(
        Transaccion, on_delete=models.CASCADE,
        related_name="movimientos", null=True, verbose_name="Transacción"
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE,
        related_name="movimientos", verbose_name="Cliente"
    )
    medio = models.ForeignKey(
        MedioAcreditacion, on_delete=models.CASCADE,
        related_name="movimientos", verbose_name="Medio de Acreditación",
        null=True,
        blank=True,
    )

    tipo = models.CharField(
        max_length=10,
        choices=TipoMovimientoEnum.choices
    )
    monto = models.DecimalField(max_digits=18, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_tipo_display()} {self.monto} PYG - {self.cliente}"
