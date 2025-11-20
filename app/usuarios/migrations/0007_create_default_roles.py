from django.db import migrations

def create_default_roles(apps, schema_editor):
    Role = apps.get_model('usuarios', 'Role')
    default_roles = [
        ("Admin", "Administrador del sistema"),
        ("Analista", "Usuario con permisos de análisis"),
        ("Soporte", "Usuario de soporte técnico"),
        ("Usuario Operador", "Usuario operador del sistema"),
    ]
    for name, description in default_roles:
        Role.objects.get_or_create(name=name, defaults={"description": description})

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0006_remove_role_is_deleted_remove_user_is_deleted_and_more"),
    ]

    operations = [
        migrations.RunPython(create_default_roles),
    ]
