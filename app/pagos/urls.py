"""
URLs para procesamiento de pagos
"""
from django.urls import path
from . import views

app_name = 'pagos'

urlpatterns = [
    # Webhook para notificaciones de la pasarela
    path('webhook/', views.webhook_pago, name='webhook_pago'),
    
    # Consultar estado de un pago
    path('consultar/<str:id_pago_externo>/', views.consultar_estado_pago, name='consultar_estado'),
]
