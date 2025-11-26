from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json
import logging

from .models import PagoPasarela
from .services import PaymentOrchestrator

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_pago(request):
    """
    Endpoint para recibir notificaciones de la pasarela.
    La pasarela llama este endpoint cuando el estado de un pago cambia.
    """
    try:
        payload = json.loads(request.body)
        logger.info(f"Webhook recibido: {payload}")
        
        id_pago = payload.get('id_pago')
        nuevo_estado = payload.get('estado')
        
        if not id_pago or not nuevo_estado:
            return JsonResponse({
                'success': False,
                'error': 'Datos incompletos'
            }, status=400)
        
        # Buscar el pago
        try:
            pago = PagoPasarela.objects.get(id_pago_externo=id_pago)
        except PagoPasarela.DoesNotExist:
            logger.warning(f"Pago no encontrado: {id_pago}")
            return JsonResponse({
                'success': False,
                'error': 'Pago no encontrado'
            }, status=404)
        
        # Actualizar estado si cambió
        if pago.estado != nuevo_estado:
            pago.estado = nuevo_estado
            pago.respuesta_pasarela = payload
            
            if nuevo_estado == 'exito' and not pago.fecha_procesamiento:
                pago.fecha_procesamiento = timezone.now()
            
            pago.save()
            logger.info(f"Pago {id_pago} actualizado a estado: {nuevo_estado}")
            
            # Actualizar estado de la transacción relacionada si el pago fue exitoso
            if nuevo_estado == 'exito' and pago.transaccion:
                from commons.enums import EstadoTransaccionEnum
                transaccion = pago.transaccion
                if transaccion.estado != EstadoTransaccionEnum.PAGADA:
                    transaccion.estado = EstadoTransaccionEnum.PAGADA
                    transaccion.save()
                    logger.info(f"Transacción {transaccion.id} marcada como PAGADA y ganancia recalculada.")
        
        return JsonResponse({
            'success': True,
            'message': 'Webhook procesado'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
    
    except Exception as e:
        logger.exception("Error procesando webhook")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def consultar_estado_pago(request, id_pago_externo):
    """
    Consulta el estado actual de un pago en la pasarela.
    """
    try:
        # Buscar el pago local
        pago = get_object_or_404(PagoPasarela, id_pago_externo=id_pago_externo)
        
        # Verificar permisos (el cliente debe ser dueño de la transacción)
        if hasattr(request.user, 'cliente'):
            if pago.transaccion.cliente != request.user.cliente:
                return JsonResponse({
                    'success': False,
                    'error': 'No tienes permiso para ver este pago'
                }, status=403)
        
        # Consultar estado en la pasarela
        orchestrator = PaymentOrchestrator()
        resultado = orchestrator.consultar_estado(id_pago_externo)
        
        if resultado['success']:
            data = resultado['data']
            nuevo_estado = data.get('estado')
            
            # Actualizar si cambió
            if nuevo_estado and nuevo_estado != pago.estado:
                pago.estado = nuevo_estado
                pago.respuesta_pasarela = data
                pago.save()
            
            return JsonResponse({
                'success': True,
                'pago': {
                    'id_pago_externo': pago.id_pago_externo,
                    'estado': pago.estado,
                    'monto': str(pago.monto),
                    'moneda': pago.moneda,
                    'metodo': pago.metodo_pasarela,
                    'fecha_creacion': pago.fecha_creacion.isoformat(),
                    'mensaje_error': pago.mensaje_error
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': resultado.get('error', 'Error consultando pasarela')
            }, status=500)
            
    except Exception as e:
        logger.exception("Error consultando estado de pago")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

