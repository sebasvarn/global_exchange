from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard_ganancias'),
    path('reporte-transacciones/', views.reporte_transacciones, name='reporte_transacciones'),
]