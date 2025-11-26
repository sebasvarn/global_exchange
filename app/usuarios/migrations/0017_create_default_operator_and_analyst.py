from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_default_operator_and_analyst(apps, schema_editor):
    Cliente = apps.get_model('clientes', 'Cliente')
    User = apps.get_model('usuarios', 'User')
    Role = apps.get_model('usuarios', 'Role')
    UserRole = apps.get_model('usuarios', 'UserRole')

    users_roles = [
        ("usuario@gmail.com", "usuario_operador", "Usuario Operador"),
        ("analistao@gmail.com", "analista_cambiario", "Analista"),
    ]
    for idx, (email, nombre, rol_nombre) in enumerate(users_roles):
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                "password": make_password("12345678"),
                "estado": "activo",
                "first_name": nombre.replace('_', ' ').title(),
            }
        )
        try:
            rol = Role.objects.get(name=rol_nombre)
            UserRole.objects.get_or_create(user=user, role=rol)
            # Asignar permisos al rol Usuario Operador
            Permission = apps.get_model('usuarios', 'Permission')
            if rol_nombre == "Usuario Operador":
                permisos_operador = [
                    "clientes.seleccionar",
                    "payments.create_method",
                    "payments.delete_method",
                    "payments.list_methods",
                    "payments.edit_method",
                    "transacciones.list",
                    "transacciones.confirmar",
                    "transacciones.create",
                    "transacciones.cancelar",
                    "medios_acreditacion.list",
                    "medios_acreditacion.edit",
                    "medios_acreditacion.create",
                    "medios_acreditacion.delete",
                    "tauser.tramitar",
                    "simulador.view",
                ]
                permisos_objs = Permission.objects.filter(code__in=permisos_operador)
                rol.permissions.add(*permisos_objs)
                rol.save()
                # Asignar dos clientes por defecto
                clientes_default = Cliente.objects.all()[:2]
                for cliente in clientes_default:
                    cliente.usuarios.add(user)
            # Asignar permisos al rol Analista
            if rol_nombre == "Analista":
                permisos_analista = [
                    "clientes.seleccionar",
                    "descuentos.list",
                    "descuentos.edit",
                    "descuentos.create",
                    "descuentos.delete",
                    "monedas.list",
                    "monedas.create",
                    "monedas.edit",
                    "monedas.delete",
                    "payments.list_methods",
                    "payments.create_method",
                    "payments.edit_method",
                    "payments.delete_method",
                    "transacciones.list",
                    "transacciones.create",
                    "transacciones.confirmar",
                    "transacciones.cancelar",
                    "monedas.restore",
                    "medios_acreditacion.list",
                    "medios_acreditacion.create",
                    "medios_acreditacion.edit",
                    "medios_acreditacion.delete",
                    "cotizaciones.list",
                    "cotizaciones.create",
                    "cotizaciones.edit",
                    "cotizaciones.delete",
                    "simulador.view",
                    "tauser.tramitar",
                    "pagos.comision.view",
                    "pagos.comision.edit",
                    "clientes.limites.edit",
                    "control_ganancias.dashboard.view",
                ]
                permisos_objs = Permission.objects.filter(code__in=permisos_analista)
                rol.permissions.add(*permisos_objs)
                rol.save()
        except Role.DoesNotExist:
            pass

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0016_add_new_permissions"),
    ]

    operations = [
        migrations.RunPython(create_default_operator_and_analyst),
    ]