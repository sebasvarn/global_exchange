"""
 Pruebas unitarias de usuarios
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Role, User, UserRole
from .forms import RegistroForm, UserCreateForm, RoleForm
from commons.enums import EstadoRegistroEnum

class UserModelTest(TestCase):
    """
    Pruebas unitarias para el modelo User.
    """
    def test_create_user(self):
        """
        Verifica que se pueda crear un usuario y que no sea superusuario por defecto.
        """
        user = User.objects.create_user(email="user1@example.com", password="pass12345")
        self.assertEqual(user.email, "user1@example.com")
        self.assertFalse(user.is_superuser)

    def test_user_str(self):
        """
        Verifica la representación en string del usuario.
        """
        user = User.objects.create_user(email="user2@example.com", password="pass12345")
        self.assertEqual(str(user), "user2@example.com")

class RoleModelTest(TestCase):
    """
    Pruebas unitarias para el modelo Role.
    """
    def test_create_role(self):
        """
        Verifica que se pueda crear un rol y su representación en string.
        """
        role = Role.objects.create(name="Admin", description="Administrador")
        self.assertEqual(str(role), "Admin")

class UserRoleModelTest(TestCase):
    """
    Pruebas unitarias para el modelo UserRole.
    """
    def setUp(self):
        """
        Configura un usuario y un rol de prueba para los tests de UserRole.
        """
        self.user = User.objects.create_user(email="user3@example.com", password="pass12345")
        self.role = Role.objects.create(name="Editor", description="Puede editar")

    def test_user_role_str(self):
        """
        Verifica la representación en string de la relación usuario-rol.
        """
        user_role = UserRole.objects.create(user=self.user, role=self.role)
        self.assertEqual(str(user_role), f"{self.user.email} → {self.role.name}")

class RegistroFormTest(TestCase):
    """
    Pruebas unitarias para el formulario de registro de usuario.
    """
    def test_valid_form(self):
        """
        Verifica que el formulario sea válido con datos correctos.
        """
        data = {
            "email": "nuevo@example.com",
            "password1": "pass12345",
            "password2": "pass12345"
        }
        form = RegistroForm(data)
        self.assertTrue(form.is_valid())

    def test_invalid_email(self):
        """
        Verifica que el formulario sea inválido si el email ya existe.
        """
        User.objects.create_user(email="existe@example.com", password="pass12345")
        data = {
            "email": "existe@example.com",
            "password1": "pass12345",
            "password2": "pass12345"
        }
        form = RegistroForm(data)
        self.assertFalse(form.is_valid())

    def test_passwords_do_not_match(self):
        """
        Verifica que el formulario sea inválido si las contraseñas no coinciden.
        """
        data = {
            "email": "nuevo2@example.com",
            "password1": "pass12345",
            "password2": "diferente"
        }
        form = RegistroForm(data)
        self.assertFalse(form.is_valid())

class UserCreateFormTest(TestCase):
    """
    Pruebas unitarias para el formulario de creación de usuario.
    """
    def test_valid_user_create_form(self):
        """
        Verifica que el formulario sea válido con datos correctos.
        """
        data = {
            "email": "admin@example.com",
            "is_active": True,
            "password1": "pass12345",
            "password2": "pass12345"
        }
        form = UserCreateForm(data)
        self.assertTrue(form.is_valid())

    def test_invalid_user_create_form(self):
        """
        Verifica que el formulario sea inválido si falta el email.
        """
        data = {
            "email": "",
            "is_active": True,
            "password1": "pass12345",
            "password2": "pass12345"
        }
        form = UserCreateForm(data)
        self.assertFalse(form.is_valid())

class RoleFormTest(TestCase):
    """
    Pruebas unitarias para el formulario de rol.
    """
    def test_valid_role_form(self):
        """
        Verifica que el formulario de rol sea válido con datos correctos.
        """
        data = {"name": "Supervisor", "description": "Supervisa usuarios"}
        form = RoleForm(data)
        self.assertTrue(form.is_valid())

    def test_invalid_role_form(self):
        """
        Verifica que el formulario de rol sea inválido si falta el nombre.
        """
        data = {"name": "", "description": "Sin nombre"}
        form = RoleForm(data)
        self.assertFalse(form.is_valid())

class UsuariosViewsTest(TestCase):
    """
    Pruebas unitarias para las vistas de usuarios.
    """
    def setUp(self):
        """
        Configura un usuario, rol y cliente de prueba para los tests de vistas de usuarios.
        """
        self.user = User.objects.create_user(email="viewuser@example.com", password="testpass123", is_active=True)
        self.client = Client()
        self.client.force_login(self.user)
        self.role = Role.objects.create(name="Admin", description="Administrador")
        UserRole.objects.create(user=self.user, role=self.role)

    def test_usuarios_list_view(self):
        """
        Verifica que la vista de lista de usuarios responda correctamente y muestre el usuario creado.
        """
        url = reverse("usuarios:usuarios_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.email)

    def test_usuario_create_view(self):
        """
        Verifica que la vista de creación de usuario funcione y cree un nuevo usuario.
        """
        url = reverse("usuarios:usuario_create")
        data = {
            "email": "nuevoadmin@example.com",
            "is_active": True,
            "password1": "pass12345",
            "password2": "pass12345"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email="nuevoadmin@example.com").exists())

    def test_usuario_edit_view(self):
        """
        Verifica que la vista de edición de usuario funcione y actualice el email del usuario.
        """
        url = reverse("usuarios:usuario_edit", args=[self.user.id])
        data = {"email": "editado@example.com", "is_active": True, "password": ""}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "editado@example.com")

    def test_usuario_delete_view(self):
        """
        Verifica que la vista de eliminación de usuario funcione y cambie el estado del usuario a eliminado.
        """
        url = reverse("usuarios:usuario_delete", args=[self.user.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.user.estado, EstadoRegistroEnum.ELIMINADO.value)
