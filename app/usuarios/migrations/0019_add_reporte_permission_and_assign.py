from django.db import migrations

def add_reporte_permission_and_assign(apps, schema_editor):
    Permission = apps.get_model('usuarios', 'Permission')
    User = apps.get_model('usuarios', 'User')
    Role = apps.get_model('usuarios', 'Role')
    UserRole = apps.get_model('usuarios', 'UserRole')

    # Crear permiso custom para reporte de control de ganancias
    perm_code = 'reporte_transacciones.view'
    perm_desc = 'Puede ver reporte de transacciones'
    perm, _ = Permission.objects.get_or_create(code=perm_code, defaults={'description': perm_desc})

    # Asignar a usuarios específicos
    emails = ['admin@gmail.com', 'analistao@gmail.com']
    for email in emails:
        user = User.objects.filter(email=email).first()
        if user:
            # Buscar roles activos del usuario
            user_roles = UserRole.objects.filter(user=user)
            for ur in user_roles:
                ur.role.permissions.add(perm)
                ur.role.save()


def remove_reporte_permission(apps, schema_editor):
    Permission = apps.get_model('usuarios', 'Permission')
    per_code = 'reporte_transacciones.view'
    Permission.objects.filter(code=perm_code).delete()

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0018_assign_new_permissions_to_admin"),
    ]
    operations = [
        migrations.RunPython(add_reporte_permission_and_assign, remove_reporte_permission),
    ]
