from django.urls import path
from . import views

app_name = 'facturacion'

urlpatterns = [
    path('descargar/<uuid:factura_uuid>/<str:formato>/', 
         views.descargar_factura, name='descargar_factura'),
    path('estado/<uuid:factura_uuid>/', 
         views.consultar_estado, name='consultar_estado'),
]