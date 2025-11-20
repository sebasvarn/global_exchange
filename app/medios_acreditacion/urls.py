"""
URLs de la aplicación 'medios_acreditacion'.

Define las rutas disponibles para la gestión de medios de acreditación:

- medios/: Listado de medios por cliente
- medios/create/: Crear un nuevo medio de acreditación
- medios/<pk>/edit/: Editar un medio existente
- medios/<pk>/delete/: Eliminar un medio existente
"""

from django.urls import path
from . import views

app_name = 'medios_acreditacion'

urlpatterns = [
    # Lista los medios de acreditación asociados a un cliente
    path('medios/', views.medios_by_client, name='medios_by_client'),

    # Crear un nuevo medio de acreditación
    path('medios/create/', views.medioacreditacion_create, name='medioacreditacion_create'),

    # Editar un medio de acreditación existente
    path('medios/<int:pk>/edit/', views.medioacreditacion_update, name='medioacreditacion_update'),

    # Eliminar un medio de acreditación existente
    path('medios/<int:pk>/delete/', views.medioacreditacion_delete, name='medioacreditacion_delete'),
]
