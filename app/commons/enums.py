"""
Definición de enumeraciones utilizadas en la aplicación.
"""
from enum import Enum


class EstadoRegistroEnum(Enum):
	ACTIVO = "activo"
	ELIMINADO = "eliminado"
	SUSPENDIDO = "suspendido"
