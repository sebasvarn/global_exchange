
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
    Modelo que representa un método de pago GUARDADO en el sistema.
    Solo incluye métodos que se almacenan: CUENTA_BANCARIA y BILLETERA.
    
    TARJETA: Se procesa directamente con Stripe (no se guarda en DB por seguridad).
    CHEQUE: No se utiliza en el sistema.
    """
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="metodos_pago", verbose_name="Cliente")
    PAYMENT_TYPE_CHOICES = [(e.value, e.name.replace('_', ' ').title()) for e in PaymentTypeEnum]
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, verbose_name="Tipo de Método de Pago", default=PaymentTypeEnum.CUENTA_BANCARIA.value)

    # Campos para Cuenta Bancaria
    titular_cuenta = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nombre del titular")
    tipo_cuenta = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tipo de cuenta")
    banco = models.CharField(max_length=100, blank=True, null=True, verbose_name="Banco")
    numero_cuenta = models.CharField(max_length=50, blank=True, null=True, verbose_name="Número de cuenta o IBAN")

    # Campos para Billetera Digital
    proveedor_billetera = models.CharField(max_length=100, blank=True, null=True, verbose_name="Proveedor de billetera")
    billetera_email_telefono = models.CharField(max_length=100, blank=True, null=True, verbose_name="Email o teléfono asociado")
    billetera_titular = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nombre del titular billetera")

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
        return f"Método de pago {self.pk}"
    
    def puede_usar_sipap(self):
        """
        Determina si este método de pago puede procesarse a través de SIPAP.
        Todos los métodos guardados (BILLETERA y CUENTA_BANCARIA) usan SIPAP.
        """
        return self.payment_type in [
            PaymentTypeEnum.BILLETERA.value,
            PaymentTypeEnum.CUENTA_BANCARIA.value,
        ]
    
    def get_metodo_sipap(self):
        """
        Mapea el tipo de PaymentMethod al método esperado por SIPAP.
        
        Returns:
            str: Nombre del método para SIPAP ('billetera', 'transferencia')
            None: Si no puede procesarse por SIPAP
        """
        if not self.puede_usar_sipap():
            return None
        
        mapping = {
            PaymentTypeEnum.BILLETERA.value: 'billetera',
            PaymentTypeEnum.CUENTA_BANCARIA.value: 'transferencia',
        }
        
        return mapping.get(self.payment_type)
    
    def get_datos_sipap(self):
        """
        Extrae los datos necesarios para enviar a SIPAP según el tipo de método.
        
        Returns:
            dict: Datos formateados para SIPAP
        """
        if not self.puede_usar_sipap():
            return {}
        
        if self.payment_type == PaymentTypeEnum.BILLETERA.value:
            # SIPAP valida: si últimos 2 dígitos son primos → rechaza
            return {
                'numero_billetera': self.billetera_email_telefono or '',
            }
        
        elif self.payment_type == PaymentTypeEnum.CUENTA_BANCARIA.value:
            # SIPAP valida: si contiene "000" o < 6 caracteres → rechaza
            # Generamos comprobante único basado en cuenta + timestamp
            import hashlib
            from datetime import datetime
            
            cuenta = self.numero_cuenta or 'CUENTA'
            data = f"{cuenta}{datetime.now().timestamp()}"
            comprobante_hash = hashlib.md5(data.encode()).hexdigest()[:10].upper()
            comprobante = f"TRF{comprobante_hash}"
            
            return {
                'numero_comprobante': comprobante,
            }
        
        return {}
