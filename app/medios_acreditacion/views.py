"""
Vistas de la aplicación Medios de Acreditación.

Contiene funciones para:
- Listar medios por cliente
- Crear, editar y eliminar medios de acreditación
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import MedioAcreditacion
from .forms import MedioAcreditacionForm
from clientes.models import Cliente
from commons.enums import EstadoRegistroEnum


def medios_by_client(request):
    """
    Lista los clientes activos del usuario y sus medios de acreditación asociados.

    :param request: HttpRequest
    :return: HttpResponse con la plantilla de listado de medios por cliente
    """
    clientes = Cliente.objects.filter(
        usuarios=request.user,
        estado=EstadoRegistroEnum.ACTIVO.value
    )
    return render(
        request,
        'medios_acreditacion/medios_by_client.html',
        {'clientes': clientes}
    )


def medioacreditacion_delete(request, pk):
    """
    Elimina un medio de acreditación existente.

    :param request: HttpRequest
    :param pk: ID del medio de acreditación a eliminar
    :return: HttpResponse con confirmación de eliminación o redirección al listado
    """
    medio = get_object_or_404(MedioAcreditacion, pk=pk)
    if request.method == 'POST':
        medio.delete()
        messages.success(request, 'Medio de acreditación eliminado exitosamente.')
        return redirect('medios_acreditacion:medios_by_client')
    return render(
        request,
        'medios_acreditacion/medioacreditacion_confirm_delete.html',
        {'medio': medio}
    )


def medioacreditacion_create(request):
    """
    Crea un nuevo medio de acreditación para un cliente específico.

    :param request: HttpRequest
    :return: HttpResponse con el formulario de creación o redirección al listado
    """
    cliente_id = request.GET.get('cliente')
    if request.method == 'POST' and not cliente_id:
        cliente_id = request.POST.get('cliente_id')
    cliente = None
    if cliente_id:
        try:
            cliente = Cliente.objects.get(pk=cliente_id, usuarios=request.user)
        except Cliente.DoesNotExist:
            cliente = None

    if request.method == 'POST':
        form = MedioAcreditacionForm(request.POST)
        if form.is_valid() and cliente:
            medio = form.save(commit=False)
            medio.cliente = cliente
            medio.save()
            messages.success(request, 'Medio de acreditación creado exitosamente.')
            return redirect('medios_acreditacion:medios_by_client')
    else:
        form = MedioAcreditacionForm()

    return render(
        request,
        'medios_acreditacion/medioacreditacion_form.html',
        {'form': form, 'cliente': cliente}
    )


def medioacreditacion_update(request, pk):
    """
    Edita un medio de acreditación existente.

    :param request: HttpRequest
    :param pk: ID del medio de acreditación a editar
    :return: HttpResponse con el formulario de edición o redirección al listado
    """
    medio = get_object_or_404(MedioAcreditacion, pk=pk)
    cliente = medio.cliente

    if request.method == 'POST':
        form = MedioAcreditacionForm(request.POST, instance=medio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medio de acreditación actualizado exitosamente.')
            return redirect('medios_acreditacion:medios_by_client')
    else:
        form = MedioAcreditacionForm(instance=medio)

    return render(
        request,
        'medios_acreditacion/medioacreditacion_form.html',
        {'form': form, 'medio': medio, 'cliente': cliente}
    )


@require_GET
def medios_por_cliente_api(request):
    """
    API endpoint que devuelve los medios de acreditación asociados a un cliente en formato JSON.

    Usado para cargar dinámicamente las cuentas de cobro en el formulario de VENTA.

    Args:
        request (HttpRequest): Solicitud HTTP GET, requiere parámetro 'cliente_id'.

    Returns:
        JsonResponse: Lista de medios de acreditación del cliente, o error si no existe.
    """
    cliente_id = request.GET.get("cliente_id")
    if not cliente_id:
        return JsonResponse({"error": "Falta cliente_id"}, status=400)
    
    try:
        cliente = Cliente.objects.get(pk=int(cliente_id))
    except (Cliente.DoesNotExist, ValueError):
        return JsonResponse({"error": "Cliente no encontrado"}, status=404)
    
    medios = MedioAcreditacion.objects.filter(cliente=cliente)
    medios_list = [
        {
            "id": m.id,
            "tipo": m.tipo,
            "descripcion": str(m),  # Usa el __str__ del modelo
            "banco": getattr(m, 'banco', ''),
            "numero_cuenta": getattr(m, 'numero_cuenta', ''),
        }
        for m in medios
    ]
    
    return JsonResponse({"medios": medios_list})
