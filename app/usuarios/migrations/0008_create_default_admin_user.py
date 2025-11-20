from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_default_admin_user(apps, schema_editor):
    User = apps.get_model('usuarios', 'User')
    Role = apps.get_model('usuarios', 'Role')
    UserRole = apps.get_model('usuarios', 'UserRole')

    # Datos del usuario admin por defecto
    email = "admin@gmail.com"
    password = make_password("12345678")  # Cambia la contraseña luego

    # Crear usuario si no existe
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"password": password, "estado": "activo"}
    )

    # Obtener el rol Admin
    admin_role = Role.objects.get(name="Admin")

    # Asignar el rol Admin si no lo tiene
    UserRole.objects.get_or_create(user=user, role=admin_role)

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0007_create_default_roles"),
    ]

    operations = [
        migrations.RunPython(create_default_admin_user),
    ]
