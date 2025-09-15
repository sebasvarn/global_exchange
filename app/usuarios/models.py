"""
Modelos y gestores personalizados para la aplicación de usuarios.

Define el modelo de usuario y el gestor de usuarios basado en email.
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from commons.enums import EstadoRegistroEnum

class UserManager(BaseUserManager):
    """
    Gestor de usuarios personalizado.

    Permite crear usuarios usando el email como identificador principal.
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Crea un usuario con email y contraseña.

        :param email: Correo electrónico único.
        :param password: Contraseña en texto plano.
        :param extra_fields: Campos adicionales para el usuario.
        :return: Instancia de usuario creada.
        :raises ValueError: Si no se proporciona email.
        """
        if not email:
            raise ValueError("El email es obligatorio.")

        email = self.normalize_email(email)
        extra_fields.setdefault("is_superuser", False)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """
        Crea un usuario estándar (no staff, no superuser).

        :param email: Correo electrónico único.
        :param password: Contraseña en texto plano.
        :param extra_fields: Campos adicionales para el usuario.
        :return: Instancia de usuario creada.
        """
        extra_fields.setdefault("is_staff", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, *args, **kwargs):
        """
        Bloquea la creación de superusuarios.

        :raises NotImplementedError: Siempre lanza excepción.
        """
        raise NotImplementedError("No esta permitido crear superusuarios en este sistema.")

class User(AbstractUser):
    """
    Modelo de usuario personalizado basado en email.

    El campo 'username' se elimina y se usa 'email' como identificador principal.
    """

    username = None
    email = models.EmailField(unique=True)
    estado = models.CharField(
        max_length=20,
        choices=[(e.value, e.name.title()) for e in EstadoRegistroEnum],
        default=EstadoRegistroEnum.ACTIVO.value,
        help_text="Estado del usuario (activo, eliminado, suspendido, etc.)"
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        """
        Guarda el usuario forzando siempre `is_superuser=False`.

        :param args: Argumentos posicionales.
        :param kwargs: Argumentos de palabra clave.
        """
        self.is_superuser = False
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Representación legible del usuario.

        :return: Email del usuario.
        """
        return self.email

    def has_role(self, role_name: str) -> bool:
        return self.user_roles.filter(role__name=role_name).exists()

    def has_any_role(self, *role_names) -> bool:
        return self.user_roles.filter(role__name__in=role_names).exists()

    def get_roles(self):
        # Devuelve solo los roles no eliminados
        return [ur.role for ur in self.user_roles.select_related('role').all() if ur.role.estado == EstadoRegistroEnum.ACTIVO.value]

class Role(models.Model):
    """
    Modelo que representa un rol en el sistema.
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    estado = models.CharField(
        max_length=20,
        choices=[(e.value, e.name.title()) for e in EstadoRegistroEnum],
        default=EstadoRegistroEnum.ACTIVO.value,
        help_text="Estado del rol (activo, eliminado, suspendido, etc.)"
    )

    def __str__(self):
        """
        Retorna el nombre del rol.
        """
        return self.name

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"


class UserRole(models.Model):
    """
    Modelo que representa la relación entre usuario y rol.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "role")
        verbose_name = "Rol de Usuario"
        verbose_name_plural = "Roles de Usuario"

    def __str__(self):
        """
        Retorna la relación usuario → rol en formato legible.
        """
        return f"{self.user.email} → {self.role.name}"