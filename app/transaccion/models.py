import uuid
import random
import string
from django.db import models

from tauser.models import Tauser
from payments.models import PaymentMethod
from clientes.models import Cliente
from commons.enums import TipoTransaccionEnum, EstadoTransaccionEnum, TipoMovimientoEnum
from medios_acreditacion.models import MedioAcreditacion
from monedas.models import Moneda


def generar_codigo_verificacion():
    """
    Genera un código alfanumérico de 6 caracteres (mayúsculas y números).
    Ejemplo: A3B7K9, X5M2P8, etc.
    """
    caracteres = string.ascii_uppercase + string.digits
    return ''.join(random.choice(caracteres) for _ in range(6))


class Transaccion(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True, blank=True)
    
    # Código de verificación amigable para el usuario (ej: "A3B7K9")
    codigo_verificacion = models.CharField(
        max_length=10,
        unique=True,
        default=generar_codigo_verificacion,
        editable=False,
        verbose_name="Código de Verificación"
    )
    
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
    medio_cobro = models.ForeignKey(
        MedioAcreditacion,
        on_delete=models.PROTECT,
        related_name="transacciones",
        verbose_name="Medio de Cobro",
        null=True,
        blank=True,
    )
    tauser = models.ForeignKey(
        Tauser,
        on_delete=models.PROTECT,
        related_name="transacciones",
        verbose_name="Tauser",
        null=True,
        blank=True,
    )
    monto_operado = models.DecimalField(max_digits=18, decimal_places=2)
    monto_pyg = models.DecimalField(max_digits=18, decimal_places=2)
    tasa_aplicada = models.DecimalField(max_digits=18, decimal_places=4)
    comision = models.DecimalField(max_digits=18, decimal_places=2)

    ganancia = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Ganancia",
        help_text="Ganancia obtenida en la transacción (comisión + spread + otros)."
    )

    estado = models.CharField(
        max_length=15,
        choices=EstadoTransaccionEnum.choices,
        default=EstadoTransaccionEnum.PENDIENTE
    )
    fecha = models.DateTimeField(auto_now_add=True)
    
    # Campos para gestión de pagos y expiración
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")
    fecha_expiracion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Expiración")
    fecha_pago = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Pago")

    class Meta:
        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=['codigo_verificacion']),
            models.Index(fields=['estado', 'fecha']),
            models.Index(fields=['cliente', 'fecha']),
        ]

    def __str__(self):
        return f"#{self.id} | {self.codigo_verificacion} | {self.get_tipo_display()} {self.moneda} - {self.cliente}"
    

    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para asegurar que siempre tenga un código único y calcular ganancia al marcar como pagada.
        """
        if not self.codigo_verificacion:
            self.codigo_verificacion = generar_codigo_verificacion()
            # Asegurar que sea único
            while Transaccion.objects.filter(codigo_verificacion=self.codigo_verificacion).exists():
                self.codigo_verificacion = generar_codigo_verificacion()

        # Calcular ganancia si el estado es PAGADA o COMPLETADA
        from commons.enums import EstadoTransaccionEnum
        if self.estado in [EstadoTransaccionEnum.PAGADA, EstadoTransaccionEnum.COMPLETADA]:
            # La ganancia es monto_operado * comision (comision como factor, ej: 0.05 para 5%)
            self.ganancia = float(self.monto_operado) * float(self.comision) if self.comision else 0
        else:
            self.ganancia = None

        super().save(*args, **kwargs)
    
    def esta_expirada(self):
        """
        Verifica si la transacción ha expirado.
        """
        from django.utils import timezone
        if self.fecha_expiracion and timezone.now() > self.fecha_expiracion:
            return True
        return False
    
    def get_tiempo_restante(self):
        """
        Retorna el tiempo restante hasta la expiración en minutos.
        """
        from django.utils import timezone
        if not self.fecha_expiracion:
            return None
        delta = self.fecha_expiracion - timezone.now()
        return max(0, int(delta.total_seconds() / 60))
    
    def verificar_cambio_cotizacion(self):
        """
        Verifica si la cotización ha cambiado desde que se creó la transacción.
        Retorna un diccionario con:
        - ha_cambiado (bool): True si cambió la cotización
        - monto_pyg_original (Decimal): Monto PYG original
        - monto_pyg_nuevo (Decimal): Monto PYG recalculado
        - tasa_original (Decimal): Tasa aplicada originalmente
        - tasa_nueva (Decimal): Tasa actual
        - diferencia_pyg (Decimal): Diferencia en PYG
        - diferencia_porcentaje (Decimal): Diferencia porcentual
        """
        from transaccion.services import calcular_transaccion
        from decimal import Decimal
        
        # Recalcular con la cotización actual
        calculo_nuevo = calcular_transaccion(
            cliente=self.cliente,
            tipo=self.tipo,
            moneda=self.moneda,
            monto_operado=self.monto_operado,
            medio_pago=self.medio_pago,
        )
        
        monto_pyg_original = Decimal(str(self.monto_pyg))
        monto_pyg_nuevo = Decimal(str(calculo_nuevo['monto_pyg']))
        tasa_original = Decimal(str(self.tasa_aplicada))
        tasa_nueva = Decimal(str(calculo_nuevo['tasa_aplicada']))
        
        diferencia_pyg = monto_pyg_nuevo - monto_pyg_original
        diferencia_porcentaje = Decimal('0')
        if monto_pyg_original > 0:
            diferencia_porcentaje = (diferencia_pyg / monto_pyg_original) * Decimal('100')
        
        # Considerar que hay cambio si la diferencia es mayor a 1 PYG (para evitar diferencias por redondeo)
        ha_cambiado = abs(diferencia_pyg) > Decimal('1')
        
        return {
            'ha_cambiado': ha_cambiado,
            'monto_pyg_original': monto_pyg_original,
            'monto_pyg_nuevo': monto_pyg_nuevo,
            'tasa_original': tasa_original,
            'tasa_nueva': tasa_nueva,
            'diferencia_pyg': diferencia_pyg,
            'diferencia_porcentaje': diferencia_porcentaje,
            'calculo_completo': calculo_nuevo,
        }


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
