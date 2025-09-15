"""
Módulo de modelos para la aplicación de clientes.
Contiene las definiciones de las clases de modelo y sus métodos.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from commons.enums import EstadoRegistroEnum


class Cliente(models.Model):
    """
    Modelo que representa un cliente en el sistema.
    Almacena información relevante como nombre, correo, etc.
    """
    estado = models.CharField(
        max_length=20,
        choices=[(e.value, e.name.title()) for e in EstadoRegistroEnum],
        default=EstadoRegistroEnum.ACTIVO.value,
        help_text="Estado del cliente (activo, eliminado, suspendido, etc.)"
    )

    SEGMENTOS = [
        ("MIN", "Minorista"),
        ("CORP", "Corporativo"),
        ("VIP", "VIP"),
    ]
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=SEGMENTOS, default="MIN")
    usuarios = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="clientes")

    def __str__(self):
        """
        Retorna la representación en cadena del cliente.
        """
        return f"{self.nombre} ({self.get_tipo_display()})"


class TasaComision(models.Model):
    """
    % de comisión por segmento (Cliente.SEGMENTOS) con vigencia (desde/hasta).
    Se evita el solapamiento de rangos por tipo_cliente cuando el registro está ACTIVO.
    """
    estado = models.CharField(
        max_length=20,
        choices=[(e.value, e.name.title()) for e in EstadoRegistroEnum],
        default=EstadoRegistroEnum.ACTIVO.value,
        help_text="Estado del registro (activo, eliminado, etc.)"
    )

    tipo_cliente = models.CharField(
        max_length=10,
        choices=Cliente.SEGMENTOS,
        help_text="Segmento al que aplica la comisión (MIN, CORP, VIP)."
    )

    porcentaje = models.DecimalField(
        max_digits=6, decimal_places=3,
        help_text="Porcentaje de comisión. Ej: 2.5 = 2,5 %."
    )

    vigente_desde = models.DateField(help_text="Inclusive")
    vigente_hasta = models.DateField(null=True, blank=True, help_text="Inclusive. Vacío = indefinido")

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tasa de comisión"
        verbose_name_plural = "Tasas de comisión"
        indexes = [
            models.Index(fields=["tipo_cliente", "vigente_desde"]),
            models.Index(fields=["estado"]),
        ]
        ordering = ["tipo_cliente", "-vigente_desde", "-id"]

    def __str__(self):
        rango = f"{self.vigente_desde:%d/%m/%Y}"
        if self.vigente_hasta:
            rango += f" - {self.vigente_hasta:%d/%m/%Y}"
        else:
            rango += " en adelante"
        return f"{self.get_tipo_cliente_display()}: {self.porcentaje}% ({rango})"

    # -------- Helpers --------
    @staticmethod
    def _max_date():
        from datetime import date
        return date(9999, 12, 31)

    def clean(self):
        # Rango lógico
        if self.vigente_hasta and self.vigente_hasta < self.vigente_desde:
            raise ValidationError("La fecha 'Hasta' no puede ser menor a 'Desde'.")

        if self.porcentaje < Decimal("0") or self.porcentaje > Decimal("100"):
            raise ValidationError("El porcentaje debe estar entre 0 y 100.")

        # Evitar solapamientos (solo contra ACTIVO)
        if self.estado == EstadoRegistroEnum.ACTIVO.value:
            qs = TasaComision.objects.filter(
                tipo_cliente=self.tipo_cliente,
                estado=EstadoRegistroEnum.ACTIVO.value,
            ).exclude(pk=self.pk)

            this_start = self.vigente_desde
            this_end = self.vigente_hasta or self._max_date()

            for other in qs:
                other_start = other.vigente_desde
                other_end = other.vigente_hasta or self._max_date()

                # solapan si: startA <= endB y startB <= endA
                if this_start <= other_end and other_start <= this_end:
                    raise ValidationError(
                        f"Solapa con otra tasa activa: {other}."
                    )

    # -------- API de consulta --------
    @classmethod
    def vigente_para_tipo(cls, tipo_cliente, fecha=None):
        """
        Devuelve la tasa vigente (o None) para un tipo de cliente en 'fecha'.
        """
        from datetime import date
        fecha = fecha or date.today()
        return (
            cls.objects.filter(
                estado=EstadoRegistroEnum.ACTIVO.value,
                tipo_cliente=tipo_cliente,
                vigente_desde__lte=fecha,
            )
            .filter(models.Q(vigente_hasta__isnull=True) | models.Q(vigente_hasta__gte=fecha))
            .order_by("-vigente_desde", "-id")
            .first()
        )

    @classmethod
    def vigente_para_cliente(cls, cliente, fecha=None):
        """
        Azúcar sintáctica usando cliente.tipo
        """
        return cls.vigente_para_tipo(cliente.tipo, fecha=fecha)
