"""
URLs de la app 'monedas'.
- CRUD de Moneda
- Tablero de tasas (dashboard_tasas)
"""

from django.urls import path
from . import views

app_name = 'monedas'

urlpatterns = [
    path('evolucion_tasas_json/', views.evolucion_tasas_json, name='evolucion_tasas_json'),
    path('', views.monedas_list, name='monedas_list'),
    path('nueva/', views.moneda_create, name='moneda_create'),
    path('editar/<int:moneda_id>/', views.moneda_edit, name='moneda_edit'),
    path('eliminar/<int:moneda_id>/', views.moneda_delete, name='moneda_delete'),
    path('inactivas/', views.monedas_inactivas, name='monedas_inactivas'),

    # Tasas de cambio
    path('tasas_comisiones/', views.tasas_comisiones_json, name='tasas_comisiones_json'),
    path('cotizaciones_json/', views.cotizaciones_json, name='cotizaciones_json'),
    path('tasas/', views.tasas_list, name='tasas_list'),
    path('tasas/nueva/', views.tasa_create, name='tasa_create'),
    path('tasas/<int:tasa_id>/editar/', views.tasa_edit, name='tasa_edit'),
    path('tasas/<int:tasa_id>/eliminar/', views.tasa_delete, name='tasa_delete'),
    path('tasas/<int:tasa_id>/activar/', views.tasa_marcar_activa, name='tasa_marcar_activa'),

    # Precios base y comisiones
    path('precios_base_comision_json/', views.precios_base_comision_json, name='precios_base_comision_json'),
    path('precios-comisiones/', views.precios_comisiones_list, name='precios_comisiones_list'),
    path('precios-comisiones/nuevo/', views.precio_comision_create, name='precio_comision_create'),
    path('precios-comisiones/<int:pk>/editar/', views.precio_comision_edit, name='precio_comision_edit'),
]
