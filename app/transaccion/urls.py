from django.urls import path
from . import views

app_name = "transacciones"

urlpatterns = [
    path("", views.transacciones_list, name="transacciones_list"),
    path("nueva/", views.transaccion_create, name="transaccion_create"),  # Mantener por compatibilidad
    path("compra/", views.compra_moneda, name="compra_moneda"),
    path("venta/", views.venta_moneda, name="venta_moneda"),
    path("<int:pk>/confirmar/", views.confirmar_view, name="confirmar"),
    path("<int:pk>/cancelar/", views.cancelar_view, name="cancelar"),
    path("calcular/", views.calcular_api, name="calcular_api"),

    path("<int:pk>/pago/tarjeta/", views.iniciar_pago_tarjeta, name="iniciar_pago_tarjeta"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("pagos/success/", views.pago_success, name="pago_success"),
    path("pagos/cancel/", views.pago_cancel, name="pago_cancel"),
    path("terminal/", views.tramitar_transaccion_terminal, name="tramitar_terminal"),

    path("medios-pago-por-cliente/", views.medios_pago_por_cliente, name="medios_pago_por_cliente"),
    path("medios-acreditacion-por-cliente/", views.medios_acreditacion_por_cliente, name="medios_acreditacion_por_cliente"),

    path("validar-stock-tauser/", views.validar_stock_tauser, name="validar_stock_tauser"),
    path("vincular-tauser/", views.vincular_tauser, name="vincular_tauser"),

    path("<int:pk>/pago/simplesipap/", views.marcar_pagada_simple, name="pago_simplesipap"),


]
