
from monedas.models import Moneda
from django.db import models
from django.utils import timezone

class TauserStock(models.Model):
	tauser = models.ForeignKey('Tauser', on_delete=models.CASCADE, related_name='stocks')
	denominacion = models.ForeignKey('Denominacion', on_delete=models.CASCADE, related_name='stocks')
	quantity = models.IntegerField('Cantidad', default=0)

	class Meta:
		unique_together = ('tauser', 'denominacion')
		verbose_name = 'Stock de TAUser'
		verbose_name_plural = 'Stock de TAUsers'

	def __str__(self):
		return f"{self.tauser.nombre} - {self.denominacion}: {self.quantity}"
        
class Denominacion(models.Model):
	BILL = 'bill'
	COIN = 'coin'
	TYPE_CHOICES = [
		(BILL, 'Billete'),
		(COIN, 'Moneda'),
	]

	moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, related_name='denominaciones')
	value = models.DecimalField('Valor', max_digits=12, decimal_places=2)
	type = models.CharField('Tipo', max_length=10, choices=TYPE_CHOICES)

	class Meta:
		unique_together = ('moneda', 'value', 'type')
		verbose_name = 'Denominación'
		verbose_name_plural = 'Denominaciones'

	def __str__(self):
		return f"{self.moneda.codigo} {self.value} → {'billete' if self.type == self.BILL else 'moneda'}"


class Tauser(models.Model):
	nombre = models.CharField(max_length=50, unique=True, editable=False)
	ubicacion = models.CharField(max_length=100)
	fecha_alta = models.DateTimeField(default=timezone.now, editable=False)
	ESTADOS = [
		("activo", "Activo"),
		("inactivo", "Inactivo"),
		("suspendido", "Suspendido"),
	]
	estado = models.CharField(max_length=20, choices=ESTADOS, default="activo")

	def save(self, *args, **kwargs):
		if not self.pk and not self.nombre:
			# Autogenerar nombre tipo "Tauser 1", "Tauser 2", ...
			ultimo = Tauser.objects.order_by('-id').first()
			numero = 1 if not ultimo else ultimo.id + 1
			self.nombre = f"Tauser {numero}"
		super().save(*args, **kwargs)

	def __str__(self):
		return self.nombre
