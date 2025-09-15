
from django.db import models
from clientes.models import Cliente


class PaymentMethod(models.Model):
	"""
	Modelo que representa un método de pago disponible en el sistema.

	:ivar cliente: Cliente al que pertenece el método de pago.
	:vartype cliente: Cliente
	:ivar name: Nombre del método de pago.
	:vartype name: str
	:ivar description: Descripción opcional del método de pago.
	:vartype description: str
	:ivar created_at: Fecha de creación.
	:vartype created_at: datetime
	:ivar updated_at: Fecha de última actualización.
	:vartype updated_at: datetime
	"""
	cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="metodos_pago", verbose_name="Cliente")
	PAYMENT_TYPE_CHOICES = [
		("tarjeta", "Tarjeta de Crédito"),
		("cuenta_bancaria", "Cuenta Bancaria"),
		("billetera", "Billetera Digital"),
	]
	payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, verbose_name="Tipo de Método de Pago", default="cuenta_bancaria")

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
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		"""
		Configuración de metadatos para el modelo PaymentMethod.
		"""
		verbose_name = "Método de Pago"
		verbose_name_plural = "Métodos de Pago"
		ordering = ["id"]

	def __str__(self):
		"""
		Retorna una representación legible del método de pago según su tipo y datos relevantes.
		"""
		# Mostrar tipo y datos relevantes según el tipo de método
		if self.payment_type == 'cuenta_bancaria':
			return f"Cuenta bancaria ({self.banco or ''} - {self.numero_cuenta or ''})"
		elif self.payment_type == 'billetera':
			return f"Billetera ({self.proveedor_billetera or ''} - {self.billetera_email_telefono or ''})"
		elif self.payment_type == 'tarjeta':
			return f"Tarjeta ({self.tarjeta_nombre or ''} - {self.tarjeta_numero or ''})"
		return f"Método de pago {self.pk}"
