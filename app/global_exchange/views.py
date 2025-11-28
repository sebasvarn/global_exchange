from django.http import JsonResponse
from django.shortcuts import render, redirect
from decimal import Decimal
import os
import json
import requests
from django.conf import settings
from monedas.models import TasaCambio

def landing_page(request):
    """
    Vista de la página de inicio del sistema.

    Esta función controla la vista principal del proyecto. 
    Si el usuario ya está autenticado, se lo redirige al dashboard. 
    En caso contrario, se muestran las tasas de cambio activas más recientes.

    :param request: Objeto HttpRequest de Django que contiene la información de la petición.
    :type request: django.http.HttpRequest

    :returns: Renderiza la plantilla ``landing.html`` con el contexto de tasas de cambio o redirige al dashboard si el usuario está autenticado.
    :rtype: django.http.HttpResponse

    **Contexto disponible en la plantilla:**

    - ``tasas``: Lista de diccionarios con información de cada tasa activa.
        - ``moneda_codigo`` (str): Código de la moneda.
        - ``moneda_nombre`` (str): Nombre de la moneda.
        - ``compra`` (Decimal): Valor de compra de la moneda.
        - ``venta`` (Decimal): Valor de venta de la moneda.
        - ``variacion`` (Decimal): Variación porcentual de la tasa.
        - ``fuente`` (str): Fuente de la información de la tasa.
        - ``fecha_creacion`` (datetime): Fecha y hora de creación de la tasa.
        - ``estado`` (str): Estado de la tasa ("Activa" o "Inactiva").
    - ``ultima_actualizacion_tasas``: Fecha de la última tasa registrada en el sistema, o ``None`` si no hay registros.

    **Ejemplo de uso:**

    .. code-block:: python

        from django.test import RequestFactory
        from global_exchange.views import landing_page

        request = RequestFactory().get("/")
        response = landing_page(request)
        print(response.status_code)  # 200 si renderiza la plantilla correctamente
    """
    # Si está autenticado, redirigir al dashboard
    if request.user.is_authenticated:
        return redirect('usuarios:dashboard')

    # Obtener las tasas activas del sistema (últimas por moneda)
    tasas_qs = (
        TasaCambio.objects.select_related('moneda')
        .filter(activa=True)
        .order_by('moneda__codigo')
    )

    tasas_obj = []
    for t in tasas_qs:
        tasas_obj.append({
            'moneda_codigo': t.moneda.codigo,
            'moneda_nombre': t.moneda.nombre,
            'compra': t.compra,
            'venta': t.venta,
            'variacion': t.variacion,
            'fuente': t.fuente,
            'fecha_creacion': t.fecha_creacion,
            'estado': 'Activa' if t.activa else 'Inactiva',
        })

    # Obtener la última fecha de actualización de tasas
    ultima_actualizacion_tasas = None
    if tasas_obj:
        ultima_actualizacion_tasas = max(t['fecha_creacion'] for t in tasas_obj)

    # Contexto para la plantilla
    context = {
        'tasas': tasas_obj,
        'ultima_actualizacion_tasas': ultima_actualizacion_tasas
    }

    return render(request, "landing.html", context)


def health(request):
    return JsonResponse({"status": "ok"})
