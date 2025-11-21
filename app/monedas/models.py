"""
Modelos de la aplicación 'monedas'.

Contiene los modelos principales para gestión de monedas y tasas de cambio:

- Moneda: representa las monedas operables en el sistema.
  - Debe existir exactamente una moneda base (es_base=True, siempre 'PYG').
  - El código se normaliza a ISO 4217 (mayúsculas).
  - Soporta soft delete y auditoría de creación/actualización.

- TasaCambio: registro de compra/venta por moneda.
  - Mantiene histórica de cotizaciones.
  - Solo puede existir una tasa activa por moneda.
  - Calcula variación respecto a la tasa previa.
  - Incluye auditoría de fuente, base y timestamp.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models import Max
import datetime
# Validador de código ISO 4217
ISO4217 = RegexValidator(
    regex=r'^[A-Z]{3}$',
    message='Usá un código ISO 4217 de 3 letras mayúsculas (ej.: PYG, USD, BRL).'
)


class MonedaManager(models.Manager):
    """
    Manager personalizado para Moneda.

    - get_queryset(): retorna solo monedas activas.
    - all_with_inactive(): retorna todas las monedas, incluyendo inactivas.
    """

    def get_queryset(self):
        return super().get_queryset().filter(activa=True)

    def all_with_inactive(self):
        return super().get_queryset()

class PrecioBaseComision(models.Model):
    """
    Modelo para almacenar precio base y comisiones por moneda registrada.
    """
    moneda = models.ForeignKey('Moneda', on_delete=models.CASCADE, related_name='precios_comisiones')
    precio_base = models.DecimalField('Precio base', max_digits=12, decimal_places=2)
    comision_compra = models.DecimalField('Comisión de compra', max_digits=10, decimal_places=2)
    comision_venta = models.DecimalField('Comisión de venta', max_digits=10, decimal_places=2)
    fecha_creacion = models.DateTimeField('Fecha de creación', auto_now_add=True)
    fecha_actualizacion = models.DateTimeField('Última actualización', auto_now=True)

    class Meta:
        verbose_name = 'Precio base y comisión'
        verbose_name_plural = 'Precios base y comisiones'
        unique_together = ('moneda',)

    def __str__(self):
        return f'{self.moneda.codigo} - Base: {self.precio_base} | Compra: {self.comision_compra}% | Venta: {self.comision_venta}%'

class Moneda(models.Model):
    """
    Modelo que representa una moneda operable.

    Atributos:
        - codigo: Código ISO 4217 de la moneda.
        - nombre: Nombre completo.
        - simbolo: Símbolo de la moneda.
        - decimales: Cantidad de decimales permitidos.
        - activa: Indica si la moneda está activa.
        - es_base: Indica si es la moneda base del sistema (siempre 'PYG').
        - creado / actualizado: auditoría de creación y modificación.
    """

    codigo = models.CharField('Código ISO', max_length=3, unique=True, validators=[ISO4217],
                              help_text='Ej.: PYG, USD, BRL')
    nombre = models.CharField('Nombre', max_length=80)
    simbolo = models.CharField('Símbolo', max_length=5, default='₲')
    decimales = models.PositiveSmallIntegerField('Decimales', default=0,
                                                 validators=[MinValueValidator(0), MaxValueValidator(6)])
    activa = models.BooleanField('Activa', default=True)
    es_base = models.BooleanField('¿Es moneda base?', default=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    objects = MonedaManager()

    class Meta:
        ordering = ['-es_base', 'codigo']
        verbose_name = 'Moneda'
        verbose_name_plural = 'Monedas'
        constraints = [
            models.UniqueConstraint(fields=['es_base'],
                                    condition=models.Q(es_base=True),
                                    name='uniq_moneda_base_global'),
        ]

    def clean(self):
        """
        Validaciones antes de guardar:
        - Normaliza el código a mayúsculas.
        - Solo 'PYG' puede ser moneda base.
        """
        if self.codigo:
            self.codigo = self.codigo.upper()

        if self.es_base and self.codigo != 'PYG':
            raise ValidationError('Solo la moneda PYG puede ser moneda base del sistema.')

    def save(self, *args, **kwargs):
        """
        Guarda la moneda asegurando:
        - Única moneda base PYG.
        - Integridad del campo es_base.
        """
        if self.codigo == 'PYG':
            self.es_base = True
            Moneda.objects.all_with_inactive().exclude(pk=self.pk).update(es_base=False)

        if self.es_base and self.codigo != 'PYG':
            self.es_base = False

        super().save(*args, **kwargs)

    def delete(self, soft_delete=True, *args, **kwargs):
        """
        Soft delete por defecto.
        Hard delete solo si no es PYG.
        """
        if soft_delete:
            self.activa = False
            self.save()
        else:
            if self.codigo == 'PYG':
                raise ValidationError('No se puede eliminar la moneda base PYG.')
            super().delete(*args, **kwargs)

    def __str__(self):
        estado = " (inactiva)" if not self.activa else ""
        return f'{self.codigo} - {self.nombre}{estado}'


class TasaCambio(models.Model):
    @classmethod
    def ultimas_por_dia(cls, moneda, desde, hasta=None):
        """
        Devuelve la última cotización de cada día para una moneda y rango de fechas.
        - moneda: instancia de Moneda
        - desde: fecha inicial (datetime o date)
        - hasta: fecha final (datetime o date, opcional)
        """
        if hasta is None:
            hasta = datetime.date.today()
        qs = cls.objects.filter(
            moneda=moneda,
            fecha_creacion__date__gte=desde,
            fecha_creacion__date__lte=hasta
        )
        diarios = qs.values('fecha_creacion__date').annotate(
            last_id=Max('id')
        ).order_by('fecha_creacion__date')
        ids = [d['last_id'] for d in diarios]
        return cls.objects.filter(id__in=ids).order_by('fecha_creacion')
    """
    Modelo de cotización por moneda.

    - Permite múltiples registros históricos.
    - Mantiene única tasa activa por moneda.
    - Calcula variación respecto a la tasa anterior.
    - Campos de auditoría: base, fuente, timestamp.
    """

    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, related_name='tasas')
    compra = models.DecimalField('Compra', max_digits=12, decimal_places=2)
    venta = models.DecimalField('Venta', max_digits=12, decimal_places=2)
    variacion = models.DecimalField('Variación %', max_digits=7, decimal_places=2, default=0,
                                    editable=False)

    base_codigo = models.CharField('Base de cotización', max_length=3, validators=[ISO4217], default='PYG')
    fuente = models.CharField('Fuente', max_length=120, blank=True, help_text='Ej: Banco Central, API Externa, Manual')
    ts_fuente = models.DateTimeField('Timestamp (fuente)', null=True, blank=True)

    fecha_creacion = models.DateTimeField('Fecha de creación', auto_now_add=True)
    fecha_actualizacion = models.DateTimeField('Última actualización', auto_now=True)
    activa = models.BooleanField('¿Cotización activa?', default=True)
    es_automatica = models.BooleanField('¿Cargada automáticamente?', default=False)

    class Meta:
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['moneda', 'activa', '-fecha_creacion']),
            models.Index(fields=['moneda', 'ts_fuente']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['moneda'], condition=models.Q(activa=True),
                                    name='uniq_tasa_activa_por_moneda'),
            models.UniqueConstraint(fields=['moneda', 'ts_fuente', 'fuente'],
                                    name='uniq_tasa_moneda_ts_fuente'),
        ]

    def clean(self):
        """
        Validaciones antes de guardar la tasa:
        - No se puede crear tasa para moneda base PYG.
        - Compra y venta deben ser mayores a cero.
        - Venta >= compra.
        """
        if self.moneda and self.moneda.es_base:
            raise ValidationError('No se puede cargar tasa de cambio para la moneda base (PYG).')
        if self.compra <= 0 or self.venta <= 0:
            raise ValidationError('Los valores de compra y venta deben ser mayores a cero.')
        if self.venta < self.compra:
            raise ValidationError('El precio de venta no puede ser menor al precio de compra.')
        self.base_codigo = 'PYG'

    def _tasa_previa(self):
        """Retorna la tasa anterior para calcular variación porcentual."""
        qs = TasaCambio.objects.filter(moneda=self.moneda)
        if self.ts_fuente:
            qs = qs.filter(
                models.Q(ts_fuente__lt=self.ts_fuente) |
                models.Q(ts_fuente__isnull=True, fecha_creacion__lt=self.fecha_creacion)
            )
        else:
            qs = qs.filter(fecha_creacion__lt=self.fecha_creacion)
        return qs.order_by('-ts_fuente', '-fecha_creacion').first()

    def calcular_variacion(self):
        """Calcula la variación % respecto a la tasa previa."""
        prev = (
            TasaCambio.objects.filter(moneda=self.moneda)
            .order_by('-ts_fuente', '-fecha_creacion')
            .first()
        )
        if not prev:
            return Decimal('0.00')
        if prev.compra > 0:
            v = ((self.compra - prev.compra) / prev.compra) * 100
            return v.quantize(Decimal('0.01'))
        return Decimal('0.00')

    def save(self, *args, **kwargs):
        """
        Guarda la tasa de cambio asegurando:
        - Única tasa activa por moneda.
        - Cálculo de variación.
        - Integridad de PYG como base.
        """
        if self.moneda and self.moneda.es_base:
            raise ValidationError('No se puede guardar tasa para PYG.')
        self.base_codigo = 'PYG'

        is_new = self.pk is None

        if is_new:
            self.variacion = self.calcular_variacion()

        with transaction.atomic():
            if is_new and self.activa:
                self.activa = False
                super().save(*args, **kwargs)

                (TasaCambio.objects
                 .select_for_update()
                 .filter(moneda=self.moneda, activa=True)
                 .exclude(pk=self.pk)
                 .update(activa=False))

                self.activa = True
                super().save(update_fields=['activa'])

            else:
                if self.activa:
                    (TasaCambio.objects
                     .select_for_update()
                     .filter(moneda=self.moneda, activa=True)
                     .exclude(pk=self.pk)
                     .update(activa=False))
                super().save(*args, **kwargs)
