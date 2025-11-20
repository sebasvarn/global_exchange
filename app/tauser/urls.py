from django.urls import path
from . import views

app_name = 'tauser'

urlpatterns = [
    path('tramitar-transacciones/', views.tramitar_transacciones, name='tramitar_transacciones'),
    path('nuevo/', views.nuevo_tauser, name='nuevo_tauser'),
    path('lista/', views.lista_tausers, name='lista_tausers'),
    path('editar-estado/<int:tauser_id>/', views.editar_estado_tauser, name='editar_estado_tauser'),
    path('asignar_stock/', views.asignar_stock_tauser, name='asignar_stock_tauser'),
    path('ver-stock/<int:tauser_id>/', views.ver_stock_tauser, name='ver_stock_tauser'),
]