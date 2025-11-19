from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Cliente, TasaComision, LimiteClienteTipo
from commons.enums import EstadoRegistroEnum
from usuarios.decorators import role_required
from .forms import AsignarUsuariosAClienteForm, ClienteForm, TasaComisionForm, LimiteClienteTipoForm


# --- Límites por tipo de cliente ---
def limites_tipo_list(request):
    items = LimiteClienteTipo.objects.all().order_by('tipo_cliente')
    return render(request, "clientes/limites_tipo_list.html", {"items": items})
    
def limite_tipo_edit(request, pk):
    obj = get_object_or_404(LimiteClienteTipo, pk=pk)
    form = LimiteClienteTipoForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        return redirect("clientes:limites_tipo_list")
    return render(request, "clientes/limite_tipo_form.html", {"form": form, "obj": obj})



@login_required
def clientes_list(request):
    """
    Muestra la lista de clientes registrados. Permite filtrar clientes eliminados lógicamente.

    Verifica si el usuario tiene el permiso 'clientes.list'. Si no lo tiene,
    redirige al dashboard y muestra un mensaje de error.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP de Django.

    Returns:
        HttpResponse: Renderiza la plantilla 'clientes/clientes_list.html' con
                      la lista de clientes activos o todos los clientes si se
                      indica 'show_deleted=1'.
    """
    if not request.user.has_permission('clientes.list'):
        messages.error(request, 'No tienes permisos para ver la lista de clientes.')
        return redirect('usuarios:dashboard')

    show_deleted = request.GET.get('show_deleted', '0') == '1'
    clientes = Cliente.objects.all()
    if not show_deleted:
        clientes = clientes.filter(estado=EstadoRegistroEnum.ACTIVO.value)
    clientes = clientes.order_by("-id")

    return render(request, "clientes/clientes_list.html", {"clientes": clientes, "show_deleted": show_deleted})


@login_required
def cliente_create(request):
    """
    Crea un nuevo cliente utilizando el formulario ClienteForm.

    Si el formulario es válido, guarda el cliente y redirige a la lista de clientes.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP con los datos del formulario.

    Returns:
        HttpResponse: Renderiza la plantilla 'clientes/cliente_form.html' con el formulario,
                      o redirige a la lista de clientes tras creación exitosa.
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
def cliente_edit(request, cliente_id):
    """
    Edita un cliente existente identificado por cliente_id.

    Si el formulario es válido, actualiza el cliente y redirige a la lista de clientes.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP.
        cliente_id (int): ID del cliente a editar.

    Returns:
        HttpResponse: Renderiza la plantilla 'clientes/cliente_form.html' con el formulario
                      de edición o redirige a la lista de clientes tras guardar cambios.
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
def cliente_delete(request, cliente_id):
    """
    Elimina lógicamente un cliente cambiando su estado a ELIMINADO.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP.
        cliente_id (int): ID del cliente a eliminar.

    Returns:
        HttpResponse: Renderiza plantilla de confirmación o redirige a la lista
                      de clientes tras eliminación lógica.
    """
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    if request.method == "POST":
        cliente.estado = EstadoRegistroEnum.ELIMINADO.value
        cliente.save()
        messages.success(request, "Cliente eliminado lógicamente.")
        return redirect("clientes:clientes_list")
    return render(request, "clientes/cliente_delete_confirm.html", {"cliente": cliente})


@login_required
def cliente_restore(request, cliente_id):
    """
    Restaura un cliente eliminado cambiando su estado a ACTIVO.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP.
        cliente_id (int): ID del cliente a restaurar.

    Returns:
        HttpResponse: Renderiza plantilla de confirmación o redirige a la lista
                      de clientes tras restauración.
    """
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    if request.method == "POST":
        cliente.estado = EstadoRegistroEnum.ACTIVO.value
        cliente.save()
        messages.success(request, "Cliente restaurado correctamente.")
        return redirect("clientes:clientes_list")
    return render(request, "clientes/cliente_restore_confirm.html", {"cliente": cliente})


@login_required
def seleccionar_cliente(request, cliente_id):
    """
    Selecciona un cliente activo y lo guarda en la sesión para que el usuario opere con él.

    Verifica el permiso 'clientes.seleccionar'.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP.
        cliente_id (int): ID del cliente a seleccionar.

    Returns:
        HttpResponse: Redirige al dashboard tras la selección del cliente.
    """
    if not request.user.has_permission('clientes.seleccionar'):
        messages.error(request, "No tienes permiso para seleccionar cliente.")
        return redirect("dashboard")

    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")

    cliente = get_object_or_404(Cliente, pk=cliente_id, usuarios=request.user)
    request.session["cliente_activo"] = cliente.id
    messages.success(request, f"Ahora estás operando como cliente: {cliente.nombre} ({cliente.get_tipo_display()})")
    return redirect("usuarios:dashboard")


@login_required
def asignar_usuarios_a_cliente(request, cliente_id):
    """
    Asigna usuarios a un cliente mediante el formulario AsignarUsuariosAClienteForm.

    Verifica el permiso 'clientes.asignar_usuarios'.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP.
        cliente_id (int): ID del cliente al que se asignarán usuarios.

    Returns:
        HttpResponse: Renderiza la plantilla de asignación o redirige a la lista
                      de clientes tras la asignación.
    """
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    if not request.user.has_permission('clientes.asignar_usuarios'):
        messages.error(request, 'No tienes permisos para asignar usuarios a clientes.')
        return redirect('clientes:clientes_list')

    if request.method == "POST":
        form = AsignarUsuariosAClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, f"Usuarios asignados al cliente: {cliente.nombre}.")
            return redirect("clientes:clientes_list")
    else:
        form = AsignarUsuariosAClienteForm(instance=cliente)
    return render(request, "clientes/asignar_usuarios_a_cliente.html", {"form": form, "cliente": cliente})


# ------- Comisiones -------

@login_required
def comisiones_list(request):
    """
    Muestra la lista de tasas de comisión, con opción de filtrar eliminadas lógicamente.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla 'clientes/comisiones_list.html' con
                      las tasas de comisión.
    """
    show_deleted = request.GET.get("show_deleted", "0") == "1"
    qs = TasaComision.objects.all().order_by("tipo_cliente", "-vigente_desde", "-id")
    if not show_deleted:
        qs = qs.filter(estado=EstadoRegistroEnum.ACTIVO.value)
    return render(request, "clientes/comisiones_list.html", {"items": qs, "show_deleted": show_deleted})


@login_required
def comision_create(request):
    """
    Crea una nueva tasa de comisión mediante TasaComisionForm.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla de formulario o redirige a la lista
                      de comisiones tras creación exitosa.
    """
    if request.method == "POST":
        form = TasaComisionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Tasa de descuento creada.")
            return redirect("clientes:comisiones_list")
    else:
        form = TasaComisionForm()
    return render(request, "clientes/comision_form.html", {"form": form})


@login_required
def comision_edit(request, pk):
    """
    Edita una tasa de comisión existente identificada por pk.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP.
        pk (int): ID de la tasa de comisión.

    Returns:
        HttpResponse: Renderiza la plantilla de edición o redirige a la lista
                      de comisiones tras guardar cambios.
    """
    obj = get_object_or_404(TasaComision, pk=pk)
    if request.method == "POST":
        form = TasaComisionForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Tasa de descuento actualizada.")
            return redirect("clientes:comisiones_list")
    else:
        form = TasaComisionForm(instance=obj)
    return render(request, "clientes/comision_form.html", {"form": form, "obj": obj})


@login_required
def comision_delete(request, pk):
    """
    Elimina lógicamente una tasa de comisión cambiando su estado a ELIMINADO.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP.
        pk (int): ID de la tasa de comisión a eliminar.

    Returns:
        HttpResponse: Renderiza plantilla de confirmación o redirige a la lista
                      de comisiones tras eliminación lógica.
    """
    obj = get_object_or_404(TasaComision, pk=pk)
    if request.method == "POST":
        obj.estado = EstadoRegistroEnum.ELIMINADO.value
        obj.save()
        messages.success(request, "Tasa de descuento eliminada lógicamente.")
        return redirect("clientes:comisiones_list")
    return render(request, "clientes/comision_delete_confirm.html", {"obj": obj})


@login_required
def comision_restore(request, pk):
    """
    Restaura una tasa de comisión eliminada cambiando su estado a ACTIVO.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP.
        pk (int): ID de la tasa de comisión a restaurar.

    Returns:
        HttpResponse: Renderiza plantilla de confirmación o redirige a la lista
                      de comisiones tras restauración.
    """
    obj = get_object_or_404(TasaComision, pk=pk)
    if request.method == "POST":
        obj.estado = EstadoRegistroEnum.ACTIVO.value
        obj.save()
        messages.success(request, "Tasa de descuento restaurada.")
        return redirect("clientes:comisiones_list")
    return render(request, "clientes/comision_restore_confirm.html", {"obj": obj})
