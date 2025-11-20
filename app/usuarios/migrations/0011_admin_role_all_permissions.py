from django.db import migrations

def assign_all_permissions_to_admin(apps, schema_editor):
    Role = apps.get_model('usuarios', 'Role')
    Permission = apps.get_model('usuarios', 'Permission')
    User = apps.get_model('usuarios', 'User')
    UserRole = apps.get_model('usuarios', 'UserRole')

    # Obtener el rol Admin
    try:
        admin_role = Role.objects.get(name="Admin")
    except Role.DoesNotExist:
        return

    # Asignar todos los permisos al rol Admin
    all_permissions = Permission.objects.all()
    admin_role.permissions.set(all_permissions)
    admin_role.save()

    # Asegurar que el usuario admin tenga el rol Admin
    user = User.objects.filter(email="admin@gmail.com").first()
    if user:
        UserRole.objects.get_or_create(user=user, role=admin_role)

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0010_auto_add_project_permissions"),
    ]

    operations = [
        migrations.RunPython(assign_all_permissions_to_admin),
    ]
