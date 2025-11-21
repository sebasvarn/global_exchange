"""
Servicios para procesamiento de pagos
"""
import httpx
import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import uuid4
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import PagoPasarela
from .processors import TarjetaProcessor, BilleteraProcessor, TransferenciaProcessor

logger = logging.getLogger(__name__)


# ============================================================================
# EXCEPCIONES
# ============================================================================

class PagoError(Exception):
    """Excepción base para errores de pago"""
    pass


class PasarelaNoDisponibleError(PagoError):
    """Error cuando la pasarela no está disponible"""
    pass


class ValidacionPagoError(PagoError):
    """Error de validación de datos de pago"""
    pass


# ============================================================================
# SERVICIO DE PASARELA (HTTP Client)
# ============================================================================

class PasarelaService:
    """
    Cliente HTTP para comunicarse con el simulador de pasarela de pagos.
    """
    
    def __init__(self):
        self.base_url = getattr(
            settings, 
            'PASARELA_BASE_URL', 
            'http://localhost:3001'
        )
        self.timeout = getattr(settings, 'PASARELA_TIMEOUT', 30)
        self.webhook_url = getattr(
            settings,
            'PASARELA_WEBHOOK_URL',
            'http://localhost:8000/pagos/webhook/'
        )
    
    def procesar_pago(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envía un pago a la pasarela externa.
        
        Args:
            payload: Datos del pago preparados
            
        Returns:
            dict con 'success' y 'data' o 'error'
            
        Raises:
            PasarelaNoDisponibleError: Si hay error de comunicación
        """
        try:
            logger.info(f"Enviando pago a pasarela: {payload.get('metodo')}")
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}/pago", json=payload)
                response.raise_for_status()
                
                resultado = response.json()
                logger.info(f"Respuesta OK - Estado: {resultado.get('estado')}")
                
                return {
                    'success': True,
                    'data': resultado
                }
                
        except httpx.TimeoutException:
            error_msg = "Timeout comunicándose con la pasarela"
            logger.error(error_msg)
            raise PasarelaNoDisponibleError(error_msg)
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Error HTTP {e.response.status_code}"
            logger.error(f"{error_msg}: {e.response.text}")
            raise PasarelaNoDisponibleError(error_msg)
            
        except httpx.RequestError as e:
            error_msg = f"Error de conexión: {str(e)}"
            logger.error(error_msg)
            raise PasarelaNoDisponibleError(error_msg)
            
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            logger.exception(error_msg)
            raise PasarelaNoDisponibleError(error_msg)
    
    def consultar_pago(self, id_pago: str) -> Dict[str, Any]:
        """Consulta el estado de un pago en la pasarela"""
        try:
            logger.info(f"Consultando pago: {id_pago}")
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/pago/{id_pago}")
                response.raise_for_status()
                
                return {
                    'success': True,
                    'data': response.json()
                }
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    'success': False,
                    'error': 'Pago no encontrado'
                }
            raise PasarelaNoDisponibleError(f"Error consultando pago: {e}")
            
        except Exception as e:
            logger.exception("Error consultando pago")
            raise PasarelaNoDisponibleError(str(e))
    
    def esta_disponible(self) -> bool:
        """Verifica si la pasarela está disponible"""
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/docs")
                return response.status_code == 200
        except:
            return False


# ============================================================================
# ORQUESTADOR DE PAGOS
# ============================================================================

class PaymentOrchestrator:
    """
    Orquestador principal que coordina el procesamiento de pagos.
    Usa procesadores específicos y el servicio de pasarela.
    """
    
    def __init__(self):
        self.pasarela_service = PasarelaService()
        self.processors = {
            'tarjeta': TarjetaProcessor(es_credito_local=False),
            'tarjeta_credito_local': TarjetaProcessor(es_credito_local=True),
            'billetera': BilleteraProcessor(),
            'transferencia': TransferenciaProcessor(),
        }
    
    @transaction.atomic
    def procesar_pago(
        self,
        transaccion,
        monto: Decimal,
        metodo: str,
        moneda: str = 'PYG',
        datos: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Procesa un pago a través de la pasarela externa.
        
        Args:
            transaccion: Instancia de Transaccion
            monto: Monto del pago
            metodo: Método de pago (tarjeta, billetera, transferencia)
            moneda: Código de moneda
            datos: Datos adicionales del método
            
        Returns:
            dict con 'success', 'pago' (modelo), 'error', etc.
        """
        datos = datos or {}
        
        logger.info(
            f"Procesando pago - Transacción: {transaccion.id}, "
            f"Método: {metodo}, Monto: {monto} {moneda}"
        )
        
        # Obtener procesador
        processor = self.processors.get(metodo)
        if not processor:
            return self._crear_pago_error(
                transaccion, monto, metodo, moneda, datos,
                f"Método de pago no soportado: {metodo}"
            )
        
        # Validar y preparar payload
        resultado_prep = processor.process(monto, moneda, datos)
        
        if not resultado_prep['success']:
            return self._crear_pago_error(
                transaccion, monto, metodo, moneda, datos,
                resultado_prep['error']
            )
        
        payload = resultado_prep['payload']
        
        # Agregar webhook si no está
        if not payload.get('webhook_url'):
            payload['webhook_url'] = self.pasarela_service.webhook_url
        
        # Llamar a la pasarela
        try:
            logger.info(f"Llamando a pasarela externa - Método: {metodo}")
            resultado_pasarela = self.pasarela_service.procesar_pago(payload)
            
            # Extraer datos de respuesta
            data = resultado_pasarela.get('data', {})
            id_pago_externo = data.get('id_pago', str(uuid4()))
            estado = data.get('estado', 'pendiente')
            motivo_rechazo = data.get('motivo_rechazo')
            
            # Crear registro de pago
            pago = PagoPasarela.objects.create(
                transaccion=transaccion,
                id_pago_externo=id_pago_externo,
                monto=monto,
                metodo_pasarela=metodo,
                moneda=moneda,
                estado=estado,
                mensaje_error=motivo_rechazo,
                datos_pago=payload,
                respuesta_pasarela=data,
                fecha_procesamiento=timezone.now() if estado == 'exito' else None
            )
            
            logger.info(
                f"Pago procesado - ID: {id_pago_externo}, Estado: {estado}"
            )
            
            return {
                'success': True,
                'pago': pago,
                'payment_id': id_pago_externo,
                'estado': estado,
                'method': metodo
            }
            
        except PasarelaNoDisponibleError as e:
            logger.error(f"Error de pasarela: {str(e)}")
            return self._crear_pago_error(
                transaccion, monto, metodo, moneda, datos,
                f"Pasarela no disponible: {str(e)}"
            )
            
        except Exception as e:
            logger.exception("Error inesperado procesando pago")
            return self._crear_pago_error(
                transaccion, monto, metodo, moneda, datos,
                f"Error inesperado: {str(e)}"
            )
    
    def _crear_pago_error(
        self,
        transaccion,
        monto: Decimal,
        metodo: str,
        moneda: str,
        datos: Dict[str, Any],
        mensaje_error: str
    ) -> Dict[str, Any]:
        """Crea un registro de pago fallido"""
        pago = PagoPasarela.objects.create(
            transaccion=transaccion,
            id_pago_externo=str(uuid4()),
            monto=monto,
            metodo_pasarela=metodo,
            moneda=moneda,
            estado='fallo',
            mensaje_error=mensaje_error,
            datos_pago=datos,
            respuesta_pasarela={'error': mensaje_error}
        )
        
        return {
            'success': False,
            'pago': pago,
            'error': mensaje_error,
            'error_type': 'processing_error'
        }
    
    def consultar_estado(self, id_pago: str) -> Dict[str, Any]:
        """Consulta el estado de un pago en la pasarela"""
        try:
            return self.pasarela_service.consultar_pago(id_pago)
        except PasarelaNoDisponibleError as e:
            return {
                'success': False,
                'error': str(e)
            }
