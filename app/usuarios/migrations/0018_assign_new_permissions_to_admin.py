from django.db import migrations

def assign_new_permissions_to_admin(apps, schema_editor):
    Role = apps.get_model('usuarios', 'Role')
    Permission = apps.get_model('usuarios', 'Permission')
    User = apps.get_model('usuarios', 'User')
    UserRole = apps.get_model('usuarios', 'UserRole')

    # Obtener el rol Admin
    try:
        admin_role = Role.objects.get(name="Admin")
    except Role.DoesNotExist:
        return

    # Permisos agregados en 0016
    new_permission_codes = [
        "tauser.view",
        "tauser.add",
        "tauser.edit",
        "tauser.delete",
        "tauser.tramitar",
        "tauser.stock.view",
        "tauser.stock.edit",
        "pagos.view",
        "pagos.add",
        "pagos.comision.view",
        "pagos.comision.edit",
        "control_ganancias.dashboard.view",
        "control_ganancias.report.view",
        "clientes.limites.edit",
    ]
    new_permissions = Permission.objects.filter(code__in=new_permission_codes)
    admin_role.permissions.add(*new_permissions)
    admin_role.save()

    # Asegurar que el usuario admin tenga el rol Admin
    user = User.objects.filter(email="admin@gmail.com").first()
    if user:
        UserRole.objects.get_or_create(user=user, role=admin_role)

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0017_create_default_operator_and_analyst"),
    ]

    operations = [
        migrations.RunPython(assign_new_permissions_to_admin),
    ]
