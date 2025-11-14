"""
Módulo de modelos para la aplicación de clientes.

Contiene las definiciones de los modelos Cliente y TasaComision,
junto con sus métodos auxiliares y validaciones.
"""

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.db.models import Sum, Case, When, F
from commons.enums import EstadoRegistroEnum


class Cliente(models.Model):
    """
    Modelo que representa un cliente en el sistema.

    Almacena información del cliente como nombre, tipo de segmento y
    los usuarios asociados.

    Attributes:
        estado (CharField): Estado actual del cliente (activo, eliminado, etc.).
        SEGMENTOS (list): Segmentos posibles del cliente (MIN, CORP, VIP).
        nombre (CharField): Nombre del cliente.
        tipo (CharField): Segmento del cliente.
        usuarios (ManyToManyField): Usuarios asociados al cliente.
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

        Returns:
            str: Nombre del cliente con el segmento entre paréntesis.
        """
        return f"{self.nombre} ({self.get_tipo_display()})"

    def get_balance(self, moneda):
        from transaccion.models import Movimiento
        result = Movimiento.objects.filter(
            cliente=self, moneda=moneda
        ).aggregate(
            balance=Sum(
                Case(
                    When(tipo="CREDITO", then=F("monto")),
                    When(tipo="DEBITO", then=F("monto") * -1),
                )
            )
        )
        return result["balance"] or 0

# =========================
# Límites por tipo de cliente
# =========================
class LimiteClienteTipo(models.Model):
    """Límites diarios y mensuales en PYG por tipo de cliente (minorista, corporativo, vip)."""
    TIPO_CHOICES = [
        ("minorista", "Minorista"),
        ("corporativo", "Corporativo"),
        ("vip", "VIP"),
    ]
    tipo_cliente = models.CharField(max_length=20, choices=TIPO_CHOICES, unique=True)
    limite_diario = models.DecimalField(max_digits=18, decimal_places=2)
    limite_mensual = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        return f"{self.get_tipo_cliente_display()} (Diario: {self.limite_diario}, Mensual: {self.limite_mensual})"


class TasaComision(models.Model):
    """
    Modelo que representa la tasa de descuento por segmento de cliente.

    Permite definir un porcentaje de descuento con fechas de vigencia.
    Se valida que no existan solapamientos en los rangos de vigencia para
    un mismo tipo de cliente cuando el registro está activo.

    Attributes:
        estado (CharField): Estado del registro (activo, eliminado, etc.).
        tipo_cliente (CharField): Segmento del cliente al que aplica el descuento.
        porcentaje (DecimalField): Porcentaje de descuento (0 a 100).
        vigente_desde (DateField): Fecha de inicio de vigencia.
        vigente_hasta (DateField): Fecha de fin de vigencia (opcional).
        creado_en (DateTimeField): Fecha de creación del registro.
        actualizado_en (DateTimeField): Fecha de última actualización.
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
        help_text="Segmento al que aplica el descuento (MIN, CORP, VIP)."
    )

    porcentaje = models.DecimalField(
        max_digits=6, decimal_places=3,
        help_text="Porcentaje de descuento. Ej: 2.5 = 2,5 %."
    )

    vigente_desde = models.DateField(help_text="Inclusive")
    vigente_hasta = models.DateField(null=True, blank=True, help_text="Inclusive. Vacío = indefinido")

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        """
        Configuración de metadatos del modelo TasaComision.

        Attributes:
            verbose_name (str): Nombre legible en singular.
            verbose_name_plural (str): Nombre legible en plural.
            indexes (list): Índices para optimizar consultas.
            ordering (list): Orden por defecto en las consultas.
        """
        verbose_name = "Tasa de descuento"
        verbose_name_plural = "Tasas de descuento"
        indexes = [
            models.Index(fields=["tipo_cliente", "vigente_desde"]),
            models.Index(fields=["estado"]),
        ]
        ordering = ["tipo_cliente", "-vigente_desde", "-id"]

    def __str__(self):
        """
        Retorna la representación en cadena de la tasa de comisión.

        Returns:
            str: Texto con el tipo de cliente, porcentaje y rango de vigencia.
        """
        rango = f"{self.vigente_desde:%d/%m/%Y}"
        if self.vigente_hasta:
            rango += f" - {self.vigente_hasta:%d/%m/%Y}"
        else:
            rango += " en adelante"
        return f"{self.get_tipo_cliente_display()}: {self.porcentaje}% desc. ({rango})"

    # -------- Helpers --------
    @staticmethod
    def _max_date():
        """
        Devuelve la fecha máxima posible usada como infinito lógico.

        Returns:
            date: Fecha 31/12/9999.
        """
        from datetime import date
        return date(9999, 12, 31)

    @property
    def factor_descuento(self) -> Decimal:
        """
        Calcula el factor multiplicativo a aplicar sobre un monto.

        Example:
            2.5% -> 0.975

        Returns:
            Decimal: Factor de descuento.
        """
        return Decimal("1") - (self.porcentaje / Decimal("100"))

    def aplicar_descuento(self, monto: Decimal) -> Decimal:
        """
        Aplica el descuento al monto recibido.

        Args:
            monto (Decimal): Monto original.

        Returns:
            Decimal: Monto con descuento aplicado.
        """
        return (monto * self.factor_descuento).quantize(monto.as_tuple().exponent)

    def clean(self):
        """
        Valida que el registro sea consistente:
        - Que las fechas tengan lógica (desde <= hasta).
        - Que el porcentaje esté entre 0 y 100.
        - Que no existan solapamientos con otras tasas activas.

        Raises:
            ValidationError: Si alguna validación falla.
        """
        # Rango lógico
        if self.vigente_hasta and self.vigente_hasta < self.vigente_desde:
            raise ValidationError("La fecha 'Hasta' no puede ser menor a 'Desde'.")

        if self.porcentaje < Decimal("0") or self.porcentaje > Decimal("100"):
            raise ValidationError("El porcentaje de descuento debe estar entre 0 y 100.")

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

                if this_start <= other_end and other_start <= this_end:
                    raise ValidationError(
                        f"Solapa con otra tasa activa: {other}."
                    )

    # -------- API de consulta --------
    @classmethod
    def vigente_para_tipo(cls, tipo_cliente, fecha=None):
        """
        Obtiene la tasa de descuento vigente para un tipo de cliente.

        Args:
            tipo_cliente (str): Segmento del cliente.
            fecha (date, optional): Fecha de referencia. Defaults to hoy.

        Returns:
            TasaComision | None: Objeto de tasa de comisión vigente o None.
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
        Obtiene la tasa vigente para un cliente específico.

        Azúcar sintáctica que usa el campo ``cliente.tipo``.

        Args:
            cliente (Cliente): Instancia de Cliente.
            fecha (date, optional): Fecha de referencia. Defaults to hoy.

        Returns:
            TasaComision | None: Objeto de tasa de comisión vigente o None.
        """
        return cls.vigente_para_tipo(cliente.tipo, fecha=fecha)

class LimitePYG(models.Model):
    """
    Máximo permitido por operación en PYG para un cliente.
    (Manténlo simple al inicio: límite por operación. Si luego querés
     diario/mensual, agregamos campos opcionales.)
    """
    cliente = models.OneToOneField("clientes.Cliente", on_delete=models.CASCADE)
    max_por_operacion = models.DecimalField(max_digits=18, decimal_places=2)
    max_mensual = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Limite PYG {self.cliente}: {self.max_por_operacion}"


class LimiteMoneda(models.Model):
    """
    Límites por MONEDA EXTRANJERA para el cliente.
    Por ahora: por operación mensual
    """
    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.CASCADE)
    moneda = models.ForeignKey("monedas.Moneda", on_delete=models.CASCADE)
    max_por_operacion = models.DecimalField(max_digits=18, decimal_places=2)  # p.ej. 5,000 USD

    max_mensual = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ("cliente", "moneda")

    def __str__(self):
        return f"Limite {self.cliente} - {self.moneda}"