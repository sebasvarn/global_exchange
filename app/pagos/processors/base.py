"""
Procesador base abstracto para métodos de pago
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class PaymentProcessor(ABC):
    """
    Clase base para procesadores de pago.
    Cada método de pago implementa su propia lógica.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def validate(self, datos: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Valida los datos del pago.
        
        Returns:
            tuple: (es_valido, mensaje_error)
        """
        pass
    
    @abstractmethod
    def prepare_payload(
        self, 
        monto: Decimal, 
        moneda: str, 
        datos: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepara el payload para enviar a la pasarela.
        
        Returns:
            dict: Payload preparado
        """
        pass
    
    @abstractmethod
    def get_method_name(self) -> str:
        """Retorna el nombre del método para la pasarela"""
        pass
    
    def process(
        self, 
        monto: Decimal, 
        moneda: str, 
        datos: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Procesa el pago: validación + preparación.
        
        Returns:
            dict con 'success', 'payload' o 'error'
        """
        # Validar
        es_valido, mensaje_error = self.validate(datos)
        if not es_valido:
            self.logger.warning(f"Validación fallida: {mensaje_error}")
            return {
                'success': False,
                'error': mensaje_error,
                'error_type': 'validation_error'
            }
        
        # Preparar payload
        try:
            payload = self.prepare_payload(monto, moneda, datos)
            self.logger.info(f"Payload preparado: {self.get_method_name()}")
            return {
                'success': True,
                'payload': payload,
                'method': self.get_method_name()
            }
        except Exception as e:
            self.logger.exception("Error preparando payload")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'preparation_error'
            }
