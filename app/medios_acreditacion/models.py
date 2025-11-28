from django.db import models
from clientes.models import Cliente
from commons.enums import TipoMedioAcreditacionEnum

class MedioAcreditacion(models.Model):
    """
    Representa un medio de acreditación asociado a un cliente.

    Existen dos tipos de medios de acreditación:
    1. Cuenta bancaria: incluye titular, tipo de cuenta, banco y número de cuenta/IBAN.
    2. Billetera digital: incluye proveedor, email o teléfono y titular de la billetera.

    :attr cliente: Cliente al que pertenece el medio de acreditación.
    :type cliente: Cliente
    :attr tipo_medio: Tipo de medio de acreditación (CUENTA_BANCARIA o BILLETERA).
    :type tipo_medio: str
    :attr titular_cuenta: Nombre del titular (solo si es cuenta bancaria).
    :type titular_cuenta: str, opcional
    :attr tipo_cuenta: Tipo de cuenta (solo si es cuenta bancaria).
    :type tipo_cuenta: str, opcional
    :attr banco: Nombre del banco (solo si es cuenta bancaria).
    :type banco: str, opcional
    :attr numero_cuenta: Número de cuenta o IBAN (solo si es cuenta bancaria).
    :type numero_cuenta: str, opcional
    :attr proveedor_billetera: Nombre del proveedor de la billetera digital (solo si tipo_billetera).
    :type proveedor_billetera: str, opcional
    :attr billetera_email_telefono: Email o teléfono asociado a la billetera (solo si tipo_billetera).
    :type billetera_email_telefono: str, opcional
    :attr billetera_titular: Nombre del titular de la billetera (solo si tipo_billetera).
    :type billetera_titular: str, opcional
    :attr created_at: Fecha de creación del registro.
    :type created_at: datetime
    :attr updated_at: Fecha de última actualización del registro.
    :type updated_at: datetime
    """

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="medios_acreditacion",
        verbose_name="Cliente"
    )

    TIPO_MEDIO_CHOICES = [(e.value, e.name.replace('_', ' ').title()) for e in TipoMedioAcreditacionEnum]
    tipo_medio = models.CharField(
        max_length=20,
        choices=TIPO_MEDIO_CHOICES,
        verbose_name="Tipo de Medio de Acreditación",
        default=TipoMedioAcreditacionEnum.CUENTA_BANCARIA.value
    )

    #TODO unificar modelos a uno generico con payments

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
        """
        Configuración adicional del modelo MedioAcreditacion.

        :var verbose_name: Nombre legible en singular para el admin.
        :var verbose_name_plural: Nombre legible en plural para el admin.
        :var ordering: Orden por defecto de los registros.
        """
        verbose_name = "Medio de Acreditación"
        verbose_name_plural = "Medios de Acreditación"
        ordering = ["id"]

    def __str__(self):
        """
        Devuelve una representación en cadena del medio de acreditación,
        dependiendo de su tipo.

        :returns: Descripción del medio de acreditación.
        :rtype: str
        """
        if self.tipo_medio == TipoMedioAcreditacionEnum.CUENTA_BANCARIA.value:
            return f"Cuenta bancaria ({self.banco or ''} - {self.numero_cuenta or ''})"
        elif self.tipo_medio == TipoMedioAcreditacionEnum.BILLETERA.value:
            return f"Billetera ({self.proveedor_billetera or ''} - {self.billetera_email_telefono or ''})"
        elif self.tipo_medio == TipoMedioAcreditacionEnum.EFECTIVO.value:
            return "Efectivo"
        elif self.tipo_medio == TipoMedioAcreditacionEnum.TARJETA.value:
            return "Tarjeta"
        return f"Medio de acreditación {self.pk}"

    @property
    def payment_type(self):
        """
        Compatibilidad con PaymentMethod: retorna el tipo de medio.
        Permite usar la misma lógica en templates para ambos modelos.
        """
        return self.tipo_medio

    @classmethod
    def get_metodo_sistema(cls, tipo_metodo):
        """
        Obtiene o crea un medio de acreditación del sistema (efectivo o tarjeta).
        Estos métodos pertenecen a un cliente especial llamado "Sistema"
        y se reutilizan para todas las transacciones de VENTA.
        
        Args:
            tipo_metodo: 'efectivo' o 'tarjeta'
        
        Returns:
            MedioAcreditacion: El método de cobro del sistema
        """
        # Obtener o crear cliente sistema
        cliente_sistema, created = Cliente.objects.get_or_create(
            nombre='Sistema',
            defaults={
                'tipo': 'CORP',
                'estado': 'activo',
            }
        )
        
        # Obtener o crear el medio de acreditación
        if tipo_metodo == 'efectivo':
            metodo, created = cls.objects.get_or_create(
                tipo_medio=TipoMedioAcreditacionEnum.EFECTIVO.value,
                cliente=cliente_sistema,
                defaults={
                    'titular_cuenta': 'Sistema - Efectivo',
                    'banco': 'Caja',
                    'numero_cuenta': 'EFECTIVO',
                }
            )
        elif tipo_metodo == 'tarjeta':
            metodo, created = cls.objects.get_or_create(
                tipo_medio=TipoMedioAcreditacionEnum.TARJETA.value,
                cliente=cliente_sistema,
                defaults={
                    'titular_cuenta': 'Sistema - Tarjeta',
                    'banco': 'Stripe',
                    'numero_cuenta': 'STRIPE',
                }
            )
        else:
            raise ValueError(f"Tipo de método no válido para sistema: {tipo_metodo}")
        
        return metodo
