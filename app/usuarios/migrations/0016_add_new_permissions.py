from django.db import migrations

def crear_permisos_generales_por_pantalla(apps, schema_editor):
    Permission = apps.get_model('usuarios', 'Permission')
    permisos = [
        # Permisos para tauser
        ("tauser.view", "Ver listado de TAUsers"),
        ("tauser.add", "Agregar TAUser"),
        ("tauser.edit", "Editar TAUser"),
        ("tauser.delete", "Eliminar TAUser"),
        ("tauser.tramitar", "Tramitar transacciones de TAUser"),
        ("tauser.stock.view", "Ver stock de TAUser"),
        ("tauser.stock.edit", "Asignar/editar stock de TAUser"),

        # Permisos para pagos y comisión por métodos de pago
        ("pagos.comision.view", "Ver comisión por métodos de pago"),
        ("pagos.comision.edit", "Editar comisión por métodos de pago"),

        # Permisos para control_ganancias (reportes)
        ("control_ganancias.dashboard.view", "Ver dashboard de ganancias"),

        # Permisos para límites de cliente
        ("clientes.limites.edit", "Ver y editar límites de cliente"),
    ]
    for code, desc in permisos:
        Permission.objects.get_or_create(code=code, defaults={"description": desc})

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0015_remove_soporte_role"),
    ]
    operations = [
        migrations.RunPython(crear_permisos_generales_por_pantalla),
    ]
