"""
Vistas (FBV) de 'monedas'.

Incluye:
- Listado, creación, edición y eliminación de Moneda.
- Tablero de tasas de cambio ('tasa_cambio'): muestra la última cotización por
  moneda si existe en BD; si no, usa un mock estático y valida la base reportada
  por la fuente vs la base del sistema.
"""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .forms import MonedaForm
from .models import Moneda, TasaCambio


@login_required
def monedas_list(request):

    monedas = Moneda.objects.all().order_by('-es_base', 'codigo')
    return render(request, 'monedas/monedas_list.html', {'monedas': monedas})


@login_required
@transaction.atomic
def moneda_create(request):

    if request.method == 'POST':
        form = MonedaForm(request.POST)
        if form.is_valid():
            obj = form.save()
            if obj.es_base:
                Moneda.objects.exclude(pk=obj.pk).update(es_base=False)
            messages.success(request, 'Moneda creada exitosamente.')
            return redirect('monedas:monedas_list')
    else:
        form = MonedaForm()
    return render(request, 'monedas/moneda_form.html', {'form': form})


@login_required
@transaction.atomic
def moneda_edit(request, moneda_id):

    moneda = get_object_or_404(Moneda, pk=moneda_id)
    if request.method == 'POST':
        form = MonedaForm(request.POST, instance=moneda)
        if form.is_valid():
            obj = form.save()
            if obj.es_base:
                Moneda.objects.exclude(pk=obj.pk).update(es_base=False)
            messages.success(request, 'Moneda actualizada.')
            return redirect('monedas:monedas_list')
    else:
        form = MonedaForm(instance=moneda)
    return render(request, 'monedas/moneda_form.html', {'form': form, 'moneda': moneda})


@login_required
def moneda_delete(request, moneda_id):

    moneda = get_object_or_404(Moneda, pk=moneda_id)
    if request.method == 'POST':
        if moneda.es_base:
            messages.error(request, 'No podés eliminar la moneda base. Asigná otra base primero.')
            return redirect('monedas:monedas_list')
        moneda.delete()
        messages.success(request, 'Moneda eliminada.')
        return redirect('monedas:monedas_list')
    return render(request, 'monedas/moneda_delete_confirm.html', {'moneda': moneda})


@login_required
def tasa_cambio(request):
    """
    Tablero de tasas:
    - Si hay datos en BD: toma la última 'activa' por moneda (robusto en cualquier DB).
    - Si no hay datos: usa un mock estático y valida la base reportada vs base del sistema.
    """
    # Moneda base del sistema
    base = Moneda.objects.filter(es_base=True).first()
    system_base = base.codigo if base else None

    # 1) Intentamos sacar las últimas tasas por moneda desde BD (robusto para cualquier DB)
    ultimas = {}
    for t in TasaCambio.objects.select_related('moneda').filter(moneda__activa=True, activa=True).order_by('moneda__codigo', '-fecha_actualizacion'):
        if t.moneda.codigo not in ultimas:
            ultimas[t.moneda.codigo] = t
    tasas = list(ultimas.values())

    # 2) Si no hay en BD, usamos datos estáticos (mock)
    api_base = None
    ultima_actualizacion = None

    if not tasas:
        demo = [
            {
                "currency": "USD",
                "buy": "7300.00",
                "sell": "7400.00",
                "base_currency": "PYG",
                "source": "Banco Central del Paraguay",
                "timestamp": "2025-09-13T22:15:00Z"
            },
            {
                "currency": "EUR",
                "buy": "8000.00",
                "sell": "8200.00",
                "base_currency": "PYG",
                "source": "Banco Central del Paraguay",
                "timestamp": "2025-09-13T22:15:00Z"
            },
        ]

        # Validación de base (todas las entradas deberían traer la misma)
        if demo:
            api_base = demo[0].get('base_currency')
            # Si alguna difiere, lo avisamos
            if any(d.get('base_currency') != api_base for d in demo):
                messages.warning(request, 'La base de la API no es consistente en las entradas recibidas.')

            if system_base and api_base and api_base != system_base:
                messages.warning(
                    request,
                    f'La API informa base {api_base}, pero el sistema usa {system_base}. Mostrando datos sin persistir.'
                )

        # Mapeamos a objetos similares a TasaCambio para la tabla (sin tocar BD)
        # Reutilizamos monedas existentes si están creadas; si no, armamos placeholder
        monedas_map = {m.codigo: m for m in Moneda.objects.all()}
        tasas = []
        for d in demo:
            m = monedas_map.get(d['currency'])
            if not m:
                # Placeholder “ligero” con interfaz mínima usada en la template
                class _M: pass
                m = _M()
                m.codigo = d['currency']
                m.nombre = ''
                m.simbolo = '$'
                m.decimales = 0

            class _T: pass
            t = _T()
            t.moneda = m
            t.compra = Decimal(d['buy'])
            t.venta  = Decimal(d['sell'])
            t.variacion = Decimal('0')
            tasas.append(t)

        # Última actualización a partir del mock
        try:
            ultima_actualizacion = max(d['timestamp'] for d in demo)
        except Exception:
            ultima_actualizacion = timezone.now()
    else:
        # Hay datos en BD → base de API opcional (si guardaste base_codigo)
        # Tomamos última actualización real de la BD
        ultima_actualizacion = max(t.fecha_actualizacion for t in tasas)
        # Si guardaste base_codigo/fuente/ts_fuente en el modelo, podés exponerlos en la UI
        api_base = next((t.base_codigo for t in tasas if getattr(t, 'base_codigo', None)), None)
        if system_base and api_base and api_base != system_base:
            messages.warning(
                request,
                f'Las tasas en BD fueron cargadas con base {api_base}, distinta a la base del sistema {system_base}.'
            )

    return render(request, 'monedas/tasa_cambio.html', {
        'tasas': tasas,
        'ultima_actualizacion': ultima_actualizacion,
        'system_base': system_base,
        'api_base': api_base,
    })
