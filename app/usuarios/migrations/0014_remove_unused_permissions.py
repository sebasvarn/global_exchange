from django.db import migrations

def remove_unused_permissions(apps, schema_editor):
    Permission = apps.get_model('usuarios', 'Permission')
    codes = [
        "exchange.view_rates",
        "comisiones.restore",
        "monedas.tasa_cambio",
        ""
    ]
    Permission.objects.filter(code__in=codes).delete()

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0013_admin_role_extra_permissions"),
    ]
    operations = [
        migrations.RunPython(remove_unused_permissions),
    ]
