from django.db import migrations

def crear_permisos(apps, schema_editor):
    Permission = apps.get_model('usuarios', 'Permission')
    permisos = [
        # clientes
        ("clientes.list", "Ver lista de clientes"),
        ("clientes.create", "Crear cliente"),
        ("clientes.edit", "Editar cliente"),
        ("clientes.delete", "Eliminar cliente"),
        ("clientes.restore", "Restaurar cliente"),
        ("clientes.seleccionar", "Seleccionar cliente activo"),
        ("clientes.asignar_usuarios", "Asignar usuarios a cliente"),
        ("comisiones.list", "Ver lista de tasas de comisión"),
        ("comisiones.create", "Crear tasa de comisión"),
        ("comisiones.edit", "Editar tasa de comisión"),
        ("comisiones.delete", "Eliminar tasa de comisión"),
        # monedas
        ("monedas.list", "Ver lista de monedas"),
        ("monedas.create", "Crear moneda"),
        ("monedas.edit", "Editar moneda"),
        ("monedas.delete", "Eliminar moneda"),
        # payments
        ("payments.list_methods", "Ver métodos de pago"),
        ("payments.create_method", "Crear método de pago"),
        ("payments.edit_method", "Editar método de pago"),
        ("payments.delete_method", "Eliminar método de pago"),
        # usuarios
        ("usuarios.restore", "Restaurar usuario"),
        ("usuarios.create", "Crear usuario"),
        ("usuarios.list", "Ver lista de usuarios"),
        ("usuarios.edit", "Editar usuario"),
        ("usuarios.delete", "Eliminar usuario"),
        ("roles.list", "Ver lista de roles"),
        ("roles.edit", "Editar rol"),
        ("roles.delete", "Eliminar rol"),
        ("roles.restore", "Restaurar rol"),
        ("roles.assign_to_user", "Asignar rol a usuario"),
        ("usuarios.asignar_clientes", "Asignar clientes a usuario"),
        # transferencias
        ("transacciones.list", "Listar transferencias"),
        ("transacciones.create", "Crear transferencia"),
        ("transacciones.confirmar", "Confirmar transferencia"),
        ("transacciones.cancelar", "Cancelar transferencia"),
    ]
    for code, desc in permisos:
        Permission.objects.get_or_create(code=code, defaults={"description": desc})

def eliminar_permisos(apps, schema_editor):
    Permission = apps.get_model('usuarios', 'Permission')
    codes = [
    "clientes.list", "clientes.create", "clientes.edit", "clientes.delete", "clientes.restore", "clientes.seleccionar", "clientes.asignar_usuarios",
        "comisiones.list", "comisiones.create", "comisiones.edit", "comisiones.delete", "comisiones.restore",
        "monedas.list", "monedas.create", "monedas.edit", "monedas.delete", "monedas.tasa_cambio",
        "exchange.view_rates",
        "payments.list_methods", "payments.create_method", "payments.edit_method", "payments.delete_method",
        "usuarios.restore", "usuarios.create", "usuarios.list", "usuarios.edit", "usuarios.delete",
        "roles.list", "roles.edit", "roles.delete", "roles.restore", "roles.assign_to_user", "usuarios.asignar_clientes",
        "transacciones.list", "transacciones.create", "transacciones.confirmar","transacciones.cancelar",
    ]
    Permission.objects.filter(code__in=codes).delete()

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0009_permission_role_permissions"),
    ]
    operations = [
        migrations.RunPython(crear_permisos, eliminar_permisos),
    ]
