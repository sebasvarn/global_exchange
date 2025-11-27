from django.shortcuts import render, get_object_or_404
from .models import Tauser, TauserStockMovimiento
from monedas.models import Moneda

def movimientos_tauser(request, tauser_id):
    tauser = get_object_or_404(Tauser, id=tauser_id)
    movimientos = TauserStockMovimiento.objects.filter(tauser=tauser).select_related('denominacion', 'denominacion__moneda', 'transaccion').order_by('-fecha')
    monedas = Moneda.objects.all()
    moneda_codigo = request.GET.get('moneda', '')
    if moneda_codigo:
        movimientos = movimientos.filter(denominacion__moneda__codigo=moneda_codigo)
    return render(request, 'tauser/movimientos_tauser.html', {
        'tauser': tauser,
        'movimientos': movimientos,
        'monedas': monedas,
        'moneda_codigo': moneda_codigo,
    })
