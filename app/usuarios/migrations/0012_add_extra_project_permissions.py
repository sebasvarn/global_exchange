from django.db import migrations

def crear_permisos_extra(apps, schema_editor):
    Permission = apps.get_model('usuarios', 'Permission')
    permisos = [
        # monedas extra
        ("monedas.restore", "Restaurar moneda"),
        # Medios de acreditación
        ("medios_acreditacion.list", "Ver lista de medios de acreditación"),
        ("medios_acreditacion.create", "Crear medio de acreditación"),
        ("medios_acreditacion.edit", "Editar medio de acreditación"),
        ("medios_acreditacion.delete", "Eliminar medio de acreditación"),
        # Cotizaciones
        ("cotizaciones.list", "Ver lista de cotizaciones"),
        ("cotizaciones.create", "Crear cotización"),
        ("cotizaciones.edit", "Editar cotización"),
        ("cotizaciones.delete", "Eliminar cotización"),
        # simulador
        ("simulador.view", "Ver simulador de transferencias"),
    ]
    for code, desc in permisos:
        Permission.objects.get_or_create(code=code, defaults={"description": desc})

def eliminar_permisos_extra(apps, schema_editor):
    Permission = apps.get_model('usuarios', 'Permission')
    codes = [
        "medios_acreditacion.list", "medios_acreditacion.create", "medios_acreditacion.edit", "medios_acreditacion.delete",
        "cotizaciones.list", "cotizaciones.create", "cotizaciones.edit", "cotizaciones.delete",
        "transferencias.list", "transferencias.create",
        "simulador.view", "monedas.restore",
    ]
    Permission.objects.filter(code__in=codes).delete()

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0011_admin_role_all_permissions"),
    ]
    operations = [
        migrations.RunPython(crear_permisos_extra, eliminar_permisos_extra),
    ]
