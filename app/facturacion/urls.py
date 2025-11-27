from django.urls import path
from . import views

app_name = 'facturacion'

urlpatterns = [
    # Cambiar de UUID a número de factura
    path('descargar/<str:numero_factura>/<str:formato>/', 
         views.descargar_factura, name='descargar_factura'),
    path('estado/<str:numero_factura>/', 
         views.consultar_estado_factura, name='consultar_estado'),
    
    # Mantener endpoints por transacción
    path('info/<int:transaccion_id>/', views.info_factura_transaccion, name='info_factura_transaccion'),
    path('generar/<int:transaccion_id>/', views.generar_factura_transaccion, name='generar_factura_transaccion'),
    path('consultar-estado/<int:transaccion_id>/', views.consultar_estado_factura_transaccion, name='consultar_estado_factura_transaccion'),
    
    # Endpoints adicionales
    path('lista/', views.lista_facturas, name='lista_facturas'),
    path('generar-manual/<int:transaccion_id>/', views.generar_factura_manual, name='generar_factura_manual'),

    path('cancelar/<int:transaccion_id>/', views.cancelar_factura_transaccion, name='cancelar_factura_transaccion'),
    path('regenerar/<int:transaccion_id>/', views.regenerar_factura_transaccion, name='regenerar_factura_transaccion'),
]