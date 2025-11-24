"""
Procesador para pagos con billetera electrónica
"""
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from .base import PaymentProcessor


class BilleteraProcessor(PaymentProcessor):
    """Procesador para billeteras electrónicas"""
    
    def validate(self, datos: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Valida que tenga número de billetera o teléfono"""
        numero_billetera = (
            datos.get('numero_billetera') or 
            datos.get('telefono') or 
            datos.get('numero_telefono')
        )
        
        if not numero_billetera:
            return False, "Número de billetera o teléfono requerido"
        
        numero_limpio = str(numero_billetera).replace(' ', '').replace('-', '')
        
        if len(numero_limpio) < 6:
            return False, "Número muy corto (mínimo 6 caracteres)"
        
        return True, None
    
    def prepare_payload(
        self, 
        monto: Decimal, 
        moneda: str, 
        datos: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepara payload con datos de billetera"""
        numero_billetera = (
            datos.get('numero_billetera') or 
            datos.get('telefono') or 
            datos.get('numero_telefono')
        )
        
        return {
            'monto': float(monto),
            'metodo': self.get_method_name(),
            'moneda': moneda,
            'numero_billetera': str(numero_billetera),
            'escenario': datos.get('escenario', 'exito'),
            'webhook_url': datos.get('webhook_url')
        }
    
    def get_method_name(self) -> str:
        return 'billetera'
