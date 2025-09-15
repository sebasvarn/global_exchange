from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Cliente, TasaComision
from commons.enums import EstadoRegistroEnum
from .forms import AsignarUsuariosAClienteForm, ClienteForm, TasaComisionForm
from usuarios.decorators import role_required

@login_required
@role_required("Admin")
def clientes_list(request):
    """
    Vista que muestra la lista de clientes registrados.
    Args:
        request: HttpRequest
    Returns:
        HttpResponse con la lista de clientes.
    """
        # Filtro para mostrar/ocultar eliminados
    show_deleted = request.GET.get('show_deleted', '0') == '1'

    # Consulta base
    clientes = Cliente.objects.all()
    if not show_deleted:
        clientes = clientes.filter(estado=EstadoRegistroEnum.ACTIVO.value)
    clientes = clientes.order_by("-id")
    return render(request, "clientes/clientes_list.html", {"clientes": clientes, "show_deleted": show_deleted})

@login_required
@role_required("Admin")
def cliente_create(request):
    """
    Vista para crear un nuevo cliente.
    Args:
        request: HttpRequest
    Returns:
        HttpResponse con el formulario o redirección.
    """
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente creado exitosamente.")
            return redirect("clientes:clientes_list")
    else:
        form = ClienteForm()
    return render(request, "clientes/cliente_form.html", {"form": form})

@login_required
@role_required("Admin")
def cliente_edit(request, cliente_id):
    """
    Vista para editar un cliente existente.
    Args:
        request: HttpRequest
        cliente_id: ID del cliente a editar.
    Returns:
        HttpResponse con el formulario de edición o redirección.
    """
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente actualizado.")
            return redirect("clientes:clientes_list")
    else:
        form = ClienteForm(instance=cliente)
    return render(request, "clientes/cliente_form.html", {"form": form, "cliente": cliente})

@login_required
@role_required("Admin")
def cliente_delete(request, cliente_id):
    """
    Vista para eliminar un cliente.
    Args:
        request: HttpRequest
        cliente_id: ID del cliente a eliminar.
    Returns:
        HttpResponse con la confirmación de eliminación.
    """
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    if request.method == "POST":
        cliente.estado = EstadoRegistroEnum.ELIMINADO.value
        cliente.save()
        messages.success(request, "Cliente eliminado lógicamente.")
        return redirect("clientes:clientes_list")
    return render(request, "clientes/cliente_delete_confirm.html", {"cliente": cliente})

@login_required
@role_required("Admin")
def cliente_restore(request, cliente_id):
    """
    Vista para restaurar un cliente eliminado lógicamente.
    """
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    if request.method == "POST":
        cliente.estado = EstadoRegistroEnum.ACTIVO.value
        cliente.save()
        messages.success(request, "Cliente restaurado correctamente.")
        return redirect("clientes:clientes_list")
    return render(request, "clientes/cliente_restore_confirm.html", {"cliente": cliente})

@login_required
@role_required("Admin")
def seleccionar_cliente(request, cliente_id):
    """
    Vista para seleccionar un cliente activo.
    Args:
        request: HttpRequest
        cliente_id: ID del cliente a seleccionar.
    Returns:
        HttpResponse redirigiendo al dashboard.
    """
    cliente = get_object_or_404(Cliente, pk=cliente_id, usuarios=request.user)
    request.session["cliente_activo"] = cliente.id
    messages.success(request, f"Ahora estás operando como cliente: {cliente.nombre}")
    return redirect("dashboard")

@login_required
@role_required("Admin")
def asignar_usuarios_a_cliente(request, cliente_id):
    """
    Vista para asignar usuarios a un cliente.
    Args:
        request: HttpRequest
        cliente_id: ID del cliente al que se asignarán usuarios.
    Returns:
        HttpResponse con el formulario o redirección.
    """
    cliente= get_object_or_404(Cliente, pk=cliente_id)
    if request.method == "POST":
        form = AsignarUsuariosAClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, f"Usuarios asignados al cliente: {cliente.nombre}.")
            return redirect("clientes:clientes_list")
    else:
        form = AsignarUsuariosAClienteForm(instance=cliente)
    return render(request, "clientes/asignar_usuarios_a_cliente.html", {"form": form, "cliente": cliente})


# ------- Listado -------
@login_required
@role_required("Admin")
def comisiones_list(request):
    show_deleted = request.GET.get("show_deleted", "0") == "1"
    qs = TasaComision.objects.all().order_by("tipo_cliente", "-vigente_desde", "-id")
    if not show_deleted:
        qs = qs.filter(estado=EstadoRegistroEnum.ACTIVO.value)
    return render(request, "clientes/comisiones_list.html", {"items": qs, "show_deleted": show_deleted})

# ------- Crear -------
@login_required
@role_required("Admin")
def comision_create(request):
    if request.method == "POST":
        form = TasaComisionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Tasa de comisión creada.")
            return redirect("clientes:comisiones_list")
    else:
        form = TasaComisionForm()
    return render(request, "clientes/comision_form.html", {"form": form})

# ------- Editar -------
@login_required
@role_required("Admin")
def comision_edit(request, pk):
    obj = get_object_or_404(TasaComision, pk=pk)
    if request.method == "POST":
        form = TasaComisionForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Tasa de comisión actualizada.")
            return redirect("clientes:comisiones_list")
    else:
        form = TasaComisionForm(instance=obj)
    return render(request, "clientes/comision_form.html", {"form": form, "obj": obj})

# ------- Eliminar lógico -------
@login_required
@role_required("Admin")
def comision_delete(request, pk):
    obj = get_object_or_404(TasaComision, pk=pk)
    if request.method == "POST":
        obj.estado = EstadoRegistroEnum.ELIMINADO.value
        obj.save()
        messages.success(request, "Tasa de comisión eliminada lógicamente.")
        return redirect("clientes:comisiones_list")
    return render(request, "clientes/comision_delete_confirm.html", {"obj": obj})

# ------- Restaurar -------
@login_required
@role_required("Admin")
def comision_restore(request, pk):
    obj = get_object_or_404(TasaComision, pk=pk)
    if request.method == "POST":
        obj.estado = EstadoRegistroEnum.ACTIVO.value
        obj.save()
        messages.success(request, "Tasa de comisión restaurada.")
        return redirect("clientes:comisiones_list")
    return render(request, "clientes/comision_restore_confirm.html", {"obj": obj})
