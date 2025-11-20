
from django.db import models
from clientes.models import Cliente
from commons.enums import PaymentTypeEnum

class ComisionMetodoPago(models.Model):
    """
    Tabla de comisiones por tipo de método de pago.
    """
    TIPO_METODO_CHOICES = [
        ("tarjeta", "Tarjeta de crédito"),
        ("transferencia", "Transferencia"),
        ("billetera", "Billetera")
    ]
    tipo_metodo = models.CharField(max_length=20, choices=TIPO_METODO_CHOICES, unique=True)
    porcentaje_comision = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Porcentaje de comisión (ej: 5.00)")

    def __str__(self):
        return f"{self.get_tipo_metodo_display()} - {self.porcentaje_comision}%"

    class Meta:
        verbose_name = "Comisión por método de pago"
        verbose_name_plural = "Comisiones por método de pago"

class PaymentMethod(models.Model):
    """
    Modelo que representa un método de pago disponible en el sistema.
    """
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="metodos_pago", verbose_name="Cliente")
    PAYMENT_TYPE_CHOICES = [(e.value, e.name.replace('_', ' ').title()) for e in PaymentTypeEnum]
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, verbose_name="Tipo de Método de Pago", default=PaymentTypeEnum.CUENTA_BANCARIA.value)

    #TODO unificar modelos a uno generico

    # Campos para Cuenta Bancaria
    titular_cuenta = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nombre del titular")
    tipo_cuenta = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tipo de cuenta")
    banco = models.CharField(max_length=100, blank=True, null=True, verbose_name="Banco")
    numero_cuenta = models.CharField(max_length=50, blank=True, null=True, verbose_name="Número de cuenta o IBAN")

    # Campos para Billetera Digital
    proveedor_billetera = models.CharField(max_length=100, blank=True, null=True, verbose_name="Proveedor de billetera")
    billetera_email_telefono = models.CharField(max_length=100, blank=True, null=True, verbose_name="Email o teléfono asociado")
    billetera_titular = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nombre del titular billetera")
    # Campos para Tarjeta de Crédito
    tarjeta_nombre = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nombre en tarjeta")
    tarjeta_numero = models.CharField(max_length=20, blank=True, null=True, verbose_name="Número de tarjeta")
    tarjeta_vencimiento = models.CharField(max_length=7, blank=True, null=True, verbose_name="Fecha de vencimiento")
    tarjeta_cvv = models.CharField(max_length=4, blank=True, null=True, verbose_name="CVV/CVC")
    tarjeta_marca = models.CharField(max_length=20, blank=True, null=True, verbose_name="Marca de tarjeta")

    # Campos para Cheque
    cheque_numero = models.CharField(max_length=20, blank=True, null=True, verbose_name="Número de cheque")
    cheque_banco = models.CharField(max_length=100, blank=True, null=True, verbose_name="Banco")
    cheque_cuenta = models.CharField(max_length=50, blank=True, null=True, verbose_name="Cuenta")
    cheque_orden = models.CharField(max_length=200, blank=True, null=True, verbose_name="Orden (Casa Matriz, dirección incluida)")
    cheque_beneficiario = models.CharField(max_length=100, blank=True, null=True, verbose_name="Beneficiario")
    cheque_monto = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="Monto")
    cheque_moneda = models.CharField(max_length=10, blank=True, null=True, verbose_name="Moneda")
    cheque_fecha_emision = models.DateField(blank=True, null=True, verbose_name="Fecha de emisión")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"
        ordering = ["id"]

    def __str__(self):
        if self.payment_type == PaymentTypeEnum.CUENTA_BANCARIA.value:
            return f"Cuenta bancaria ({self.banco or ''} - {self.numero_cuenta or ''})"
        elif self.payment_type == PaymentTypeEnum.BILLETERA.value:
            return f"Billetera ({self.proveedor_billetera or ''} - {self.billetera_email_telefono or ''})"
        elif self.payment_type == PaymentTypeEnum.TARJETA.value:
            return f"Tarjeta ({self.tarjeta_nombre or ''} - {self.tarjeta_numero or ''})"
        elif self.payment_type == PaymentTypeEnum.CHEQUE.value:
            return f"Cheque ({self.cheque_banco or ''} - {self.cheque_cuenta or ''} - N° {self.cheque_numero or ''})"
        return f"Método de pago {self.pk}"
