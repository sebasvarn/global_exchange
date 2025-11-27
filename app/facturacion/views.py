from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import FacturaElectronica, ConfiguracionFacturacion
from .services import ServicioFacturacion
import logging

logger = logging.getLogger(__name__)

@login_required
def lista_facturas(request):
    """Lista todas las facturas electrónicas"""
    facturas = FacturaElectronica.objects.select_related('transaccion').all().order_by('-fecha_emision')
    
    return render(request, 'facturacion/lista_facturas.html', {
        'facturas': facturas
    })

@login_required
def descargar_factura(request, numero_factura, formato='pdf'):
    """Descarga una factura en formato PDF o XML usando número de factura"""
    # Buscar factura por número de factura
    factura = get_object_or_404(FacturaElectronica, numero_factura=numero_factura)
    
    try:
        servicio = ServicioFacturacion()
        resultado = servicio.descargar_factura(factura, formato)
        
        if resultado['success']:
            if formato == 'pdf' and factura.pdf_file:
                response = HttpResponse(factura.pdf_file.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="factura_{factura.numero_factura}.pdf"'
                return response
            elif formato == 'xml' and factura.xml_file:
                response = HttpResponse(factura.xml_file.read(), content_type='application/xml')
                response['Content-Disposition'] = f'attachment; filename="factura_{factura.numero_factura}.xml"'
                return response
            else:
                return JsonResponse({'error': 'Archivo no disponible'}, status=404)
        else:
            return JsonResponse({'error': resultado['error']}, status=400)
            
    except Exception as e:
        logger.error(f"Error al descargar factura: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def consultar_estado_factura(request, numero_factura):
    """Consulta el estado de una factura específica usando número de factura"""
    factura = get_object_or_404(FacturaElectronica, numero_factura=numero_factura)
    
    try:
        servicio = ServicioFacturacion()
        resultado = servicio.consultar_estado_factura(factura)
        
        if 'success' in resultado:
            return JsonResponse({
                'success': True,
                'estado': factura.estado_sifen,
                'descripcion': factura.descripcion_estado,
                'cdc': factura.cdc,
                'numero_factura': factura.numero_factura
            })
        else:
            return JsonResponse({'error': resultado['error']}, status=400)
            
    except Exception as e:
        logger.error(f"Error al consultar estado: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def generar_factura_manual(request, transaccion_id):
    """Endpoint para generar factura manualmente (para testing)"""
    from transaccion.models import Transaccion
    
    transaccion = get_object_or_404(Transaccion, id=transaccion_id)
    
    try:
        servicio = ServicioFacturacion()
        resultado = servicio.generar_factura(transaccion)
        
        return JsonResponse(resultado)
        
    except Exception as e:
        logger.error(f"Error al generar factura manual: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    

@login_required
def info_factura_transaccion(request, transaccion_id):
    """Obtiene información de la factura de una transacción"""
    from transaccion.models import Transaccion
    
    transaccion = get_object_or_404(Transaccion, id=transaccion_id)
    
    # Verificar permisos
    if not transaccion.cliente.usuarios.filter(id=request.user.id).exists():
        return JsonResponse({'success': False, 'error': 'No tiene permisos'}, status=403)
    
    if hasattr(transaccion, 'factura_electronica'):
        factura = transaccion.factura_electronica
        return JsonResponse({
            'success': True,
            'factura': {
                'id': factura.id,
                'numero_factura': factura.numero_factura,
                'cdc': factura.cdc,
                'estado_sifen': factura.estado_sifen,
                'desc_sifen': factura.desc_sifen,
                'error_sifen': factura.error_sifen,  
                'descripcion_estado': factura.descripcion_estado,
                'fecha_emision': factura.fecha_emision.strftime('%d/%m/%Y') if factura.fecha_emision else None,
                'fecha_aprobacion': factura.fecha_aprobacion.strftime('%d/%m/%Y %H:%M') if factura.fecha_aprobacion else None,
                'nombre_receptor': factura.nombre_receptor,
                'ruc_receptor': factura.ruc_receptor,
                'estado': factura.estado_sifen,  # Usamos estado_sifen como estado interno
            }
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'No existe factura para esta transacción'
        })

@login_required
@require_POST
def generar_factura_transaccion(request, transaccion_id):
    """Genera factura para una transacción"""
    from transaccion.models import Transaccion
    
    transaccion = get_object_or_404(Transaccion, id=transaccion_id)
    
    # Verificar permisos
    if not transaccion.cliente.usuarios.filter(id=request.user.id).exists():
        return JsonResponse({'success': False, 'error': 'No tiene permisos'}, status=403)
    
    try:
        # Obtener datos fiscales del request
        datos_fiscales = {}
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            datos_fiscales = data.get('datos_fiscales', {})
        
        # Guardar datos fiscales en la transacción
        if datos_fiscales:
            if not hasattr(transaccion, 'datos_fiscales') or not transaccion.datos_fiscales:
                transaccion.datos_fiscales = {}
            
            transaccion.datos_fiscales.update({
                'nombre': datos_fiscales.get('nombre', ''),
                'ruc': datos_fiscales.get('ruc', ''),
                'dv': datos_fiscales.get('dv', ''),
                'cedula': datos_fiscales.get('cedula', ''),
                'email': datos_fiscales.get('email', ''),
                'telefono': datos_fiscales.get('telefono', ''),
                'direccion': datos_fiscales.get('direccion', ''),
            })
            transaccion.save()
        
        servicio = ServicioFacturacion()
        resultado = servicio.generar_factura(transaccion)
        return JsonResponse(resultado)
    except Exception as e:
        logger.error(f"Error al generar factura para transacción {transaccion_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error al generar factura: {str(e)}'
        }, status=500)

@login_required
def consultar_estado_factura_transaccion(request, transaccion_id):
    """Consulta el estado de la factura de una transacción"""
    from transaccion.models import Transaccion
    
    transaccion = get_object_or_404(Transaccion, id=transaccion_id)
    
    # Verificar permisos
    if not transaccion.cliente.usuarios.filter(id=request.user.id).exists():
        return JsonResponse({'success': False, 'error': 'No tiene permisos'}, status=403)
    
    if not hasattr(transaccion, 'factura_electronica'):
        return JsonResponse({'success': False, 'error': 'No existe factura'})
    
    try:
        servicio = ServicioFacturacion()
        resultado = servicio.consultar_estado_factura(transaccion.factura_electronica)
        return JsonResponse(resultado)
    except Exception as e:
        logger.error(f"Error al consultar estado de factura {transaccion_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error al consultar estado: {str(e)}'
        }, status=500)
    

@login_required
@require_POST
def cancelar_factura_transaccion(request, transaccion_id):
    """Cancela la factura de una transacción"""
    from transaccion.models import Transaccion
    
    transaccion = get_object_or_404(Transaccion, id=transaccion_id)
    
    # Verificar permisos
    if not transaccion.cliente.usuarios.filter(id=request.user.id).exists():
        return JsonResponse({'success': False, 'error': 'No tiene permisos'}, status=403)
    
    if not hasattr(transaccion, 'factura_electronica'):
        return JsonResponse({'success': False, 'error': 'No existe factura'})
    
    try:
        servicio = ServicioFacturacion()
        resultado = servicio.cancelar_factura(transaccion.factura_electronica)
        return JsonResponse(resultado)
    except Exception as e:
        logger.error(f"Error al cancelar factura {transaccion_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error al cancelar factura: {str(e)}'
        }, status=500)


@login_required
@require_POST
def regenerar_factura_transaccion(request, transaccion_id):
    """Regenera factura para una transacción después de cancelar la anterior"""
    from transaccion.models import Transaccion
    
    transaccion = get_object_or_404(Transaccion, id=transaccion_id)
    
    # Verificar permisos
    if not transaccion.cliente.usuarios.filter(id=request.user.id).exists():
        return JsonResponse({'success': False, 'error': 'No tiene permisos'}, status=403)
    
    if not hasattr(transaccion, 'factura_electronica'):
        return JsonResponse({'success': False, 'error': 'No existe factura'})
    
    try:
        servicio = ServicioFacturacion()
        resultado = servicio.regenerar_factura(transaccion.factura_electronica, transaccion)
        return JsonResponse(resultado)
    except Exception as e:
        logger.error(f"Error al regenerar factura {transaccion_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error al regenerar factura: {str(e)}'
        }, status=500)
    