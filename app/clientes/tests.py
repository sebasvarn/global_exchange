"""
 Pruebas unitarias de clientes
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Cliente
from .forms import ClienteForm, AsignarUsuariosAClienteForm

User = get_user_model()

class ClienteModelTest(TestCase):
	"""
	Pruebas unitarias para el modelo Cliente.
	"""
	def setUp(self):
		"""
		Configura un usuario y un cliente de prueba para los tests del modelo Cliente.
		"""
		self.user = User.objects.create_user(email="testuser@example.com", password="testpass123")
		self.cliente = Cliente.objects.create(nombre="Empresa X", tipo="CORP")
		self.cliente.usuarios.add(self.user)

	def test_cliente_str(self):
		"""
		Verifica la representación en string del cliente.
		"""
		self.assertEqual(str(self.cliente), "Empresa X (Corporativo)")

	def test_cliente_segmentos(self):
		"""
		Verifica que el tipo de cliente esté en los segmentos definidos.
		"""
		self.assertIn(self.cliente.tipo, dict(Cliente.SEGMENTOS))

	def test_cliente_usuarios(self):
		"""
		Verifica que el usuario esté asociado al cliente.
		"""
		self.assertIn(self.user, self.cliente.usuarios.all())


class ClienteFormTest(TestCase):
	"""
	Pruebas unitarias para el formulario ClienteForm.
	"""
	def setUp(self):
		"""
		Configura un usuario de prueba para los tests del formulario ClienteForm.
		"""
		self.user = User.objects.create_user(email="formuser@example.com", password="testpass123")

	def test_cliente_form_valid(self):
		"""
		Verifica que el formulario sea válido con datos correctos.
		"""
		data = {"nombre": "Empresa Y", "tipo": "VIP", "usuarios": [self.user.id]}
		form = ClienteForm(data)
		self.assertTrue(form.is_valid())

	def test_cliente_form_invalid(self):
		"""
		Verifica que el formulario sea inválido si falta el nombre.
		"""
		data = {"nombre": "", "tipo": "VIP"}
		form = ClienteForm(data)
		self.assertFalse(form.is_valid())


class AsignarUsuariosAClienteFormTest(TestCase):
	"""
	Pruebas unitarias para el formulario AsignarUsuariosAClienteForm.
	"""
	def setUp(self):
		"""
		Configura un usuario y un cliente de prueba para los tests del formulario AsignarUsuariosAClienteForm.
		"""
		self.user = User.objects.create_user(email="asignaruser@example.com", password="testpass123")
		self.cliente = Cliente.objects.create(nombre="Empresa Z", tipo="MIN")

	def test_asignar_usuarios_form(self):
		"""
		Verifica que el formulario sea válido al asignar usuarios a un cliente.
		"""
		data = {"usuarios": [self.user.id]}
		form = AsignarUsuariosAClienteForm(data, instance=self.cliente)
		self.assertTrue(form.is_valid())


class ClienteViewsTest(TestCase):
	"""
	Pruebas unitarias para las vistas de clientes.
	"""
	def setUp(self):
		"""
		Configura un usuario, rol y cliente de prueba para los tests de vistas de clientes.
		"""
		self.user = User.objects.create_user(email="viewuser@example.com", password="testpass123")
		self.user.is_staff = True
		self.user.save()
		# Crear rol Admin y asociarlo al usuario
		from usuarios.models import Role, UserRole
		self.role = Role.objects.create(name="Admin", description="Administrador")
		UserRole.objects.create(user=self.user, role=self.role)
		self.client.force_login(self.user)
		self.cliente = Cliente.objects.create(nombre="Empresa W", tipo="MIN")
		self.cliente.usuarios.add(self.user)

	def test_clientes_list_view(self):
		"""
		Verifica que la vista de lista de clientes responda correctamente y muestre el cliente creado.
		"""
		url = reverse("clientes:clientes_list")
		response = self.client.get(url)
		# Si la vista requiere login y rol, puede redirigir a login (302)
		if response.status_code == 302:
			self.fail("Redirigido, verifica permisos o login en la vista.")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Empresa W")

	def test_cliente_create_view(self):
		"""
		Verifica que la vista de creación de cliente funcione y cree un nuevo cliente.
		"""
		url = reverse("clientes:cliente_create")
		data = {"nombre": "Empresa Nueva", "tipo": "VIP", "usuarios": [self.user.id]}
		response = self.client.post(url, data)
		self.assertEqual(response.status_code, 302)  # Redirige tras crear
		self.assertTrue(Cliente.objects.filter(nombre="Empresa Nueva").exists())

	def test_cliente_edit_view(self):
		"""
		Verifica que la vista de edición de cliente funcione y actualice el nombre del cliente.
		"""
		url = reverse("clientes:cliente_edit", args=[self.cliente.id])
		data = {"nombre": "Empresa Editada", "tipo": "CORP", "usuarios": [self.user.id]}
		response = self.client.post(url, data)
		self.assertEqual(response.status_code, 302)
		self.cliente.refresh_from_db()
		self.assertEqual(self.cliente.nombre, "Empresa Editada")

	def test_cliente_delete_view(self):
		"""
		Verifica que la vista de eliminación de cliente funcione y cambie el estado del cliente a eliminado.
		"""
		url = reverse("clientes:cliente_delete", args=[self.cliente.id])
		response = self.client.post(url)
		self.assertEqual(response.status_code, 302)
		self.cliente.refresh_from_db()
		self.cliente.refresh_from_db()
		from commons.enums import EstadoRegistroEnum
		self.assertEqual(self.cliente.estado, EstadoRegistroEnum.ELIMINADO.value)
