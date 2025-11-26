from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
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
def descargar_factura(request, factura_uuid, formato='pdf'):
    """Descarga una factura en formato PDF o XML"""
    factura = get_object_or_404(FacturaElectronica, uuid=factura_uuid)
    
    try:
        servicio = ServicioFacturacion()
        resultado = servicio.descargar_factura(factura, formato)
        
        if resultado['success']:
            if formato == 'pdf' and factura.pdf_file:
                response = HttpResponse(factura.pdf_file.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="factura_{factura.cdc}.pdf"'
                return response
            elif formato == 'xml' and factura.xml_file:
                response = HttpResponse(factura.xml_file.read(), content_type='application/xml')
                response['Content-Disposition'] = f'attachment; filename="factura_{factura.cdc}.xml"'
                return response
            else:
                return JsonResponse({'error': 'Archivo no disponible'}, status=404)
        else:
            return JsonResponse({'error': resultado['error']}, status=400)
            
    except Exception as e:
        logger.error(f"Error al descargar factura: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def consultar_estado_factura(request, factura_uuid):
    """Consulta el estado de una factura específica"""
    factura = get_object_or_404(FacturaElectronica, uuid=factura_uuid)
    
    try:
        servicio = ServicioFacturacion()
        resultado = servicio.consultar_estado_factura(factura)
        
        if 'success' in resultado:
            return JsonResponse({
                'success': True,
                'estado': factura.estado_sifen,
                'descripcion': factura.descripcion_estado,
                'cdc': factura.cdc
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
        # Marcar que se está generando desde interfaz (no desde señal)
        transaccion._generando_factura_desde_tauser = True
        transaccion.save()
        
        servicio = ServicioFacturacion()
        resultado = servicio.generar_factura(transaccion)
        
        return JsonResponse(resultado)
        
    except Exception as e:
        logger.error(f"Error al generar factura manual: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)