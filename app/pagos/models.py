from django.db import models
from django.utils import timezone


class PagoPasarela(models.Model):
    """
    Modelo para registrar pagos procesados a través de la pasarela externa.
    Almacena toda la información del pago y la respuesta de la pasarela.
    """
    
    ESTADO_CHOICES = [
        ('exito', 'Éxito'),
        ('fallo', 'Fallo'),
        ('pendiente', 'Pendiente'),
    ]
    
    # Relación con transacción
    transaccion = models.ForeignKey(
        'transaccion.Transaccion',
        on_delete=models.CASCADE,
        related_name='pagos_pasarela',
        verbose_name="Transacción"
    )
    
    # Identificación del pago
    id_pago_externo = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="ID Pago Externo",
        help_text="ID único del pago en la pasarela (o UUID generado)"
    )
    
    # Información del pago
    monto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Monto"
    )
    
    metodo_pasarela = models.CharField(
        max_length=50,
        verbose_name="Método en Pasarela",
        help_text="Método: tarjeta, billetera, transferencia, cuenta_interna"
    )
    
    moneda = models.CharField(
        max_length=10,
        verbose_name="Moneda"
    )
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        verbose_name="Estado del Pago"
    )
    
    # Datos del pago (JSON)
    datos_pago = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Datos del Pago",
        help_text="Datos enviados a la pasarela"
    )
    
    # Respuesta de la pasarela (JSON)
    respuesta_pasarela = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Respuesta de Pasarela",
        help_text="Respuesta completa de la pasarela"
    )
    
    # Control de fechas
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de Actualización"
    )
    
    fecha_procesamiento = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Procesamiento"
    )
    
    # Error (si aplica)
    mensaje_error = models.TextField(
        blank=True,
        verbose_name="Mensaje de Error"
    )
    
    class Meta:
        verbose_name = "Pago de Pasarela"
        verbose_name_plural = "Pagos de Pasarela"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['id_pago_externo']),
            models.Index(fields=['transaccion', '-fecha_creacion']),
            models.Index(fields=['estado', '-fecha_creacion']),
        ]
    
    def __str__(self):
        return f"Pago {self.id_pago_externo} - Estado: {self.estado}"
    
    def es_exitoso(self):
        """Verifica si el pago fue exitoso"""
        return self.estado == 'exito'
    
    def es_fallido(self):
        """Verifica si el pago falló"""
        return self.estado == 'fallo'
    
    def es_pendiente(self):
        """Verifica si el pago está pendiente"""
        return self.estado == 'pendiente'

