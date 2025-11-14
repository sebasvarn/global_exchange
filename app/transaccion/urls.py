from django.urls import path
from . import views

app_name = "transacciones"

urlpatterns = [
    path("", views.transacciones_list, name="transacciones_list"),
    path("nueva/", views.transaccion_create, name="transaccion_create"),
    path("<int:pk>/confirmar/", views.confirmar_view, name="confirmar"),
    path("<int:pk>/cancelar/", views.cancelar_view, name="cancelar"),
    path("calcular/", views.calcular_api, name="calcular_api"),

    path("<int:pk>/pago/tarjeta/", views.iniciar_pago_tarjeta, name="iniciar_pago_tarjeta"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("pagos/success/", views.pago_success, name="pago_success"),
    path("pagos/cancel/", views.pago_cancel, name="pago_cancel"),
    path("terminal/", views.tramitar_transaccion_terminal, name="tramitar_terminal"),

    path("medios-pago-por-cliente/", views.medios_pago_por_cliente, name="medios_pago_por_cliente"),

]
