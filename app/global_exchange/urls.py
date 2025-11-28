"""
URL configuration for global_exchange project.

Configuración de URLs para el proyecto **global_exchange**.

Incluye rutas para:

- Panel de administración de Django.
- Aplicación de usuarios.
- Página de inicio (landing page).
- Dashboard principal.
- Aplicación de clientes.
- Aplicación de exchange (tasas de cambio).
- Documentación generada por Sphinx.
- Aplicación de monedas.
- Aplicación de pagos.
- Aplicación de medios de acreditación.
"""

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.views.generic import RedirectView
from .views import health
import os

#: Lista principal de URLs del proyecto.
urlpatterns = [
    path("health/", health, name="health"),
    path("health", health, name="health"),
    
    # --- Control de Ganancias ---
    path('control_ganancias/', include('control_ganancias.urls')),
    # --- Administración ---
    path('admin/', admin.site.urls, name="admin"),

    # --- Usuarios ---
    path('usuarios/', include(('usuarios.urls', 'usuarios'), namespace='usuarios')),

    # --- Landing page ---
    path(
        '',
        __import__('global_exchange.views', fromlist=['landing_page']).landing_page,
        name='landing'
    ),

    # --- Dashboard principal ---
    path('dashboard/', lambda r: redirect('usuarios:dashboard'), name='dashboard'),

    # --- Clientes ---
    path('clientes/', include(('clientes.urls', 'clientes'), namespace='clientes')),

    # --- Documentación generada con Sphinx ---
    path("docs/", RedirectView.as_view(url="/docs/index.html", permanent=False)),
    re_path(
        r"^docs/(?P<path>.*)$",
        serve,
        {"document_root": os.path.join(settings.BASE_DIR, "docs/build/html")},
        name="documentacion",
    ),

    # --- Monedas ---
    path('monedas/', include('monedas.urls')),
    path('payments/', include('payments.urls', namespace='payments')),
    path('medios_acreditacion/', include('medios_acreditacion.urls', namespace='medios_acreditacion')),
    path('transacciones/', include('transaccion.urls')),
    # MFA endpoints (generate/verify) - used for testing OTP by terminal
    path('mfa/', include(('mfa.urls', 'mfa'), namespace='mfa')),

    # --- Tauser ---
    path('tauser/', include(('tauser.urls', 'tauser'), namespace='tauser')),

    # --- Pagos (procesamiento vía pasarela) ---
    path('pagos/', include(('pagos.urls', 'pagos'), namespace='pagos')),

    # --- Facturación Electrónica ---
    path('facturacion/', include(('facturacion.urls', 'pagos'), namespace='facturacion')),
]
