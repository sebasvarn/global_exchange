"""
Procesador para pagos con tarjeta
"""
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from .base import PaymentProcessor


class TarjetaProcessor(PaymentProcessor):
    """Procesador para tarjetas de débito y crédito local"""
    
    def __init__(self, es_credito_local: bool = False):
        super().__init__()
        self.es_credito_local = es_credito_local
    
    def validate(self, datos: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Valida que tenga número de tarjeta válido"""
        numero_tarjeta = datos.get('numero_tarjeta')
        
        if not numero_tarjeta:
            return False, "Número de tarjeta requerido"
        
        # Limpiar espacios y guiones
        numero_limpio = str(numero_tarjeta).replace(' ', '').replace('-', '')
        
        if len(numero_limpio) < 13 or len(numero_limpio) > 19:
            return False, "Número de tarjeta inválido"
        
        if not numero_limpio.isdigit():
            return False, "Número de tarjeta debe contener solo dígitos"
        
        return True, None
    
    def prepare_payload(
        self, 
        monto: Decimal, 
        moneda: str, 
        datos: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepara payload con datos de tarjeta"""
        numero_tarjeta = str(datos.get('numero_tarjeta', ''))
        numero_limpio = numero_tarjeta.replace(' ', '').replace('-', '')
        
        return {
            'monto': float(monto),
            'metodo': self.get_method_name(),
            'moneda': moneda,
            'numero_tarjeta': numero_limpio,
            'escenario': datos.get('escenario', 'exito'),
            'webhook_url': datos.get('webhook_url')
        }
    
    def get_method_name(self) -> str:
        return 'tarjeta_credito_local' if self.es_credito_local else 'tarjeta'
