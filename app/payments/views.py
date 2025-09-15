
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from .models import PaymentMethod
from .forms import PaymentMethodForm
from clientes.models import Cliente
from commons.enums import EstadoRegistroEnum


def payment_methods_by_client(request):
	"""
	Vista que muestra tarjetas/cuadraditos de cada cliente vinculado al usuario,
	con sus métodos de pago y acciones de añadir, editar y eliminar.

	:param request: HttpRequest
	:return: HttpResponse con la vista de métodos de pago por cliente
	"""
	clientes = Cliente.objects.filter(usuarios=request.user, estado=EstadoRegistroEnum.ACTIVO.value)
	return render(request, 'payments/payment_methods_by_client.html', {'clientes': clientes})
def payment_method_delete(request, pk):
	"""
	Vista para eliminar un método de pago (eliminación real).

	:param request: HttpRequest
	:param pk: ID del método de pago
	:return: HttpResponse de confirmación de borrado
	"""
	method = get_object_or_404(PaymentMethod, pk=pk)
	if request.method == 'POST':
		method.delete()
		messages.success(request, 'Método de pago eliminado exitosamente.')
		return redirect('payments:payment_methods_by_client')
	return render(request, 'payments/paymentmethod_confirm_delete.html', {'method': method})

def payment_method_create(request):
	"""
	Vista para crear un nuevo método de pago.

	:param request: HttpRequest
	:return: HttpResponse con el formulario de creación
	"""
	cliente_id = request.GET.get('cliente')
	cliente = None
	if cliente_id:
		try:
			cliente = Cliente.objects.get(pk=cliente_id, usuarios=request.user)
		except Cliente.DoesNotExist:
			cliente = None
	if request.method == 'POST':
		form = PaymentMethodForm(request.POST)
		if form.is_valid() and cliente:
			metodo = form.save(commit=False)
			metodo.cliente = cliente
			metodo.save()
			messages.success(request, 'Método de pago creado exitosamente.')
			return redirect('payments:payment_methods_by_client')
	else:
		form = PaymentMethodForm()
	return render(request, 'payments/paymentmethod_form.html', {'form': form, 'cliente': cliente})

def payment_method_update(request, pk):
	"""
	Vista para editar un método de pago existente.

	:param request: HttpRequest
	:param pk: ID del método de pago
	:return: HttpResponse con el formulario de edición
	"""
	method = get_object_or_404(PaymentMethod, pk=pk)
	cliente = method.cliente
	if request.method == 'POST':
		form = PaymentMethodForm(request.POST, instance=method)
		if form.is_valid():
			form.save()
			messages.success(request, 'Método de pago actualizado exitosamente.')
			return redirect('payments:payment_methods_by_client')
	else:
		form = PaymentMethodForm(instance=method)
	return render(request, 'payments/paymentmethod_form.html', {'form': form, 'method': method, 'cliente': cliente})

