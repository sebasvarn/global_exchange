"""
URL configuration for global_exchange project.

Configuración de URLs para el proyecto global_exchange.

Incluye rutas para:
- Panel de administración
- Aplicación de usuarios
- Redirección a login
- Documentación generada por Sphinx

"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.views.generic import RedirectView
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),
    path('', lambda r: redirect('usuarios:login'), name='login'),
    path('dashboard/', lambda r: redirect('usuarios:dashboard'), name='dashboard'),
    path('clientes/', include('clientes.urls', namespace='clientes')),
    path('exchange/', include('exchange.urls', namespace='exchange')),
    path("docs/", RedirectView.as_view(url="/docs/index.html", permanent=False)),
    re_path(
        r"^docs/(?P<path>.*)$",
        serve,
        {"document_root": os.path.join(settings.BASE_DIR, "docs/build/html")},
        name="documentacion",
    ),
    path('monedas/', include('monedas.urls')),
    path('payments/', include('payments.urls', namespace='payments')),
]
