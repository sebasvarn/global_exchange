"""
Procesador para pagos con transferencia bancaria
"""
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from .base import PaymentProcessor


class TransferenciaProcessor(PaymentProcessor):
    """Procesador para transferencias bancarias"""
    
    def validate(self, datos: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Valida que tenga número de comprobante"""
        numero_comprobante = datos.get('numero_comprobante')
        
        if not numero_comprobante:
            return False, "Número de comprobante requerido"
        
        if len(str(numero_comprobante)) < 6:
            return False, "Número de comprobante muy corto"
        
        return True, None
    
    def prepare_payload(
        self, 
        monto: Decimal, 
        moneda: str, 
        datos: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepara payload con datos de transferencia"""
        return {
            'monto': float(monto),
            'metodo': self.get_method_name(),
            'moneda': moneda,
            'numero_comprobante': str(datos.get('numero_comprobante', '')),
            'escenario': datos.get('escenario', 'exito'),
            'webhook_url': datos.get('webhook_url')
        }
    
    def get_method_name(self) -> str:
        return 'transferencia'
