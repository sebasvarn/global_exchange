from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('methods/', views.payment_methods_by_client, name='payment_methods_by_client'),
    path('methods/create/', views.payment_method_create, name='paymentmethod_create'),
    path('methods/<int:pk>/edit/', views.payment_method_update, name='paymentmethod_update'),
    path('methods/<int:pk>/delete/', views.payment_method_delete, name='paymentmethod_delete'),
    path('comisiones/', views.comisiones_metodos_pago_list, name='comisiones_metodos_pago_list'),
    path('comisiones/<int:pk>/edit/', views.comision_metodo_pago_edit, name='comision_metodo_pago_edit'),
]
