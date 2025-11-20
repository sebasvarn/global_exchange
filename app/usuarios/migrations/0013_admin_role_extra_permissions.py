from django.db import migrations

def assign_extra_permissions_to_admin(apps, schema_editor):
    Role = apps.get_model('usuarios', 'Role')
    Permission = apps.get_model('usuarios', 'Permission')
    User = apps.get_model('usuarios', 'User')
    UserRole = apps.get_model('usuarios', 'UserRole')

    # Permisos extra definidos en la migración anterior
    extra_codes = [
        "monedas.restore",
        "medios_acreditacion.list", "medios_acreditacion.create", "medios_acreditacion.edit", "medios_acreditacion.delete",
        "cotizaciones.list", "cotizaciones.create", "cotizaciones.edit", "cotizaciones.delete",
        "simulador.view",
    ]
    extra_permissions = Permission.objects.filter(code__in=extra_codes)

    # Obtener el rol Admin
    try:
        admin_role = Role.objects.get(name="Admin")
    except Role.DoesNotExist:
        return

    # Asignar los permisos extra al rol Admin
    admin_role.permissions.add(*extra_permissions)
    admin_role.save()

    # Asegurar que el usuario admin tenga el rol Admin
    user = User.objects.filter(email="admin@gmail.com").first()
    if user:
        UserRole.objects.get_or_create(user=user, role=admin_role)

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0012_add_extra_project_permissions"),
    ]
    operations = [
        migrations.RunPython(assign_extra_permissions_to_admin),
    ]
