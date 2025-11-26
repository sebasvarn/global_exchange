from django.db import models
from transaccion.models import Transaccion
import uuid

class ConfiguracionFacturacion(models.Model):
    """Configuración global para facturación electrónica"""
    ruc_emisor = models.CharField(max_length=20, verbose_name="RUC Emisor")
    dv_emisor = models.CharField(max_length=2, verbose_name="DV Emisor")
    nombre_emisor = models.CharField(max_length=300, verbose_name="Razón Social Emisor")
    direccion_emisor = models.CharField(max_length=300, verbose_name="Dirección Emisor")
    numero_casa = models.CharField(max_length=10, verbose_name="Número de Casa")
    departamento_emisor = models.CharField(max_length=3, default='1', verbose_name="Código Departamento")
    descripcion_departamento = models.CharField(max_length=100, default='CAPITAL', verbose_name="Descripción Departamento")
    ciudad_emisor = models.CharField(max_length=3, default='1', verbose_name="Código Ciudad")
    descripcion_ciudad = models.CharField(max_length=100, default='ASUNCION (DISTRITO)', verbose_name="Descripción Ciudad")
    telefono_emisor = models.CharField(max_length=50, blank=True, verbose_name="Teléfono Emisor")
    email_emisor = models.EmailField(verbose_name="Email Emisor")
    numero_timbrado = models.CharField(max_length=20, verbose_name="Número de Timbrado")
    fecha_inicio_timbrado = models.DateField(verbose_name="Fecha Inicio Timbrado")
    
    # Configuración SQL Proxy
    sql_proxy_url = models.URLField(default='http://sql-proxy01:5000', verbose_name="URL SQL Proxy")
    
    activo = models.BooleanField(default=True, verbose_name="Configuración Activa")
    
    class Meta:
        verbose_name = "Configuración de Facturación"
        verbose_name_plural = "Configuraciones de Facturación"
    
    def __str__(self):
        return f"Configuración {self.nombre_emisor} - {self.ruc_emisor}"

class FacturaElectronica(models.Model):
    ESTADOS_SIFEN = [
        ('PENDIENTE', 'Pendiente'),
        ('PROCESANDO', 'Procesando'),
        ('APROBADO', 'Aprobado'),
        ('APROBADO_OBS', 'Aprobado con Observación'),
        ('RECHAZADO', 'Rechazado'),
        ('ERROR', 'Error'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    transaccion = models.OneToOneField(
        Transaccion,
        on_delete=models.CASCADE,
        related_name='factura_electronica',
        verbose_name="Transacción"
    )
    
    # Datos del DE
    cdc = models.CharField(max_length=200, unique=True, verbose_name="Código de Control")
    id_de = models.BigIntegerField(null=True, blank=True, verbose_name="ID Documento Electrónico")
    numero_factura = models.CharField(max_length=50, blank=True, verbose_name="Número de Factura")
    
    # Estados
    estado_sifen = models.CharField(
        max_length=20, 
        choices=ESTADOS_SIFEN, 
        default='PENDIENTE',
        verbose_name="Estado SIFEN"
    )
    
    # Fechas
    fecha_emision = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Emisión")
    fecha_aprobacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Aprobación SIFEN")
    fecha_consulta = models.DateTimeField(null=True, blank=True, verbose_name="Fecha Última Consulta")
    
    # Archivos
    xml_file = models.FileField(upload_to='facturas/xml/', null=True, blank=True, verbose_name="Archivo XML")
    pdf_file = models.FileField(upload_to='facturas/pdf/', null=True, blank=True, verbose_name="Archivo PDF")
    
    # Logs y errores
    descripcion_estado = models.TextField(blank=True, verbose_name="Descripción del Estado")
    error_message = models.TextField(blank=True, verbose_name="Mensaje de Error")
    intentos_consulta = models.IntegerField(default=0, verbose_name="Intentos de Consulta")
    
    # Metadata
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Factura Electrónica"
        verbose_name_plural = "Facturas Electrónicas"
        ordering = ['-fecha_emision']
        indexes = [
            models.Index(fields=['cdc']),
            models.Index(fields=['estado_sifen']),
            models.Index(fields=['fecha_emision']),
        ]

    def __str__(self):
        return f"Factura {self.cdc or 'Pendiente'} - {self.transaccion.codigo_verificacion}"

    @property
    def esta_aprobada(self):
        return self.estado_sifen in ['APROBADO', 'APROBADO_OBS']

    @property
    def puede_descargar(self):
        return self.esta_aprobada and (self.xml_file or self.pdf_file)