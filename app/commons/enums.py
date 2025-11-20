
from enum import Enum
from django.db import models
"""
Definición de enumeraciones utilizadas en la aplicación.
"""

class TipoMedioAcreditacionEnum(Enum):
	CUENTA_BANCARIA = "cuenta_bancaria"
	BILLETERA = "billetera"



class EstadoRegistroEnum(Enum):
	ACTIVO = "activo"
	ELIMINADO = "eliminado"
	SUSPENDIDO = "suspendido"

# Enum para tipos de pago
class PaymentTypeEnum(Enum):
	TARJETA = "tarjeta"
	CUENTA_BANCARIA = "cuenta_bancaria"
	BILLETERA = "billetera"
	CHEQUE = "cheque"


class TipoMovimientoEnum(models.TextChoices):
    DEBITO = "debito", "Débito"
    CREDITO = "credito", "Crédito"

class TipoTransaccionEnum(models.TextChoices):
    COMPRA = "compra", "Compra"
    VENTA = "venta", "Venta"

class EstadoTransaccionEnum(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    PAGADA = "pagada", "Pagada"
    ANULADA = "anulada", "Anulada"
    CANCELADA = "cancelada", "Cancelada"