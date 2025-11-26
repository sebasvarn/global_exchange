from django.db import migrations

def remove_soporte_role(apps, schema_editor):
    Role = apps.get_model('usuarios', 'Role')
    UserRole = apps.get_model('usuarios', 'UserRole')
    soporte_roles = Role.objects.filter(name="Soporte")
    # Eliminar relaciones de usuarios con el rol Soporte
    UserRole.objects.filter(role__in=soporte_roles).delete()
    # Eliminar el rol Soporte
    soporte_roles.delete()

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0014_remove_unused_permissions"),
    ]
    operations = [
        migrations.RunPython(remove_soporte_role),
    ]
