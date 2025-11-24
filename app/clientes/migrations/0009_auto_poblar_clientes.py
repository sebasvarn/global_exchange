from django.db import migrations
from datetime import date, timedelta
def crear_clientes(apps, schema_editor):

    Cliente = apps.get_model('clientes', 'Cliente')
    TasaComision = apps.get_model('clientes', 'TasaComision')
    User = apps.get_model('usuarios', 'User')
    EstadoRegistroEnum = type('EstadoRegistroEnum', (), {"ACTIVO": "activo"})

    # Obtener el usuario admin por defecto
    admin_user = User.objects.filter(email="admin@gmail.com").first()

    clientes_data = [
        {"nombre": "Augusto Bianciotto", "tipo": "MIN"},
        {"nombre": "Ilson Gonzales", "tipo": "CORP"},
        {"nombre": "Maria Gomez", "tipo": "MIN"},
        {"nombre": "Sebastian Vera", "tipo": "VIP"},
        {"nombre": "Tomas Uzain", "tipo": "CORP"},
    ]
    for data in clientes_data:
        cliente = Cliente.objects.create(**data)
        if admin_user:
            cliente.usuarios.add(admin_user)

    # Poblar tasas de comisión
    tasas = [
        {"tipo_cliente": "VIP", "porcentaje": 10, "vigente_desde": date.today(), "vigente_hasta": date.today() + timedelta(days=1), "estado": "activo"},
        {"tipo_cliente": "CORP", "porcentaje": 5, "vigente_desde": date.today(), "vigente_hasta": date.today() + timedelta(days=1), "estado": "activo"},
        {"tipo_cliente": "MIN", "porcentaje": 0, "vigente_desde": date.today(), "vigente_hasta": date.today() + timedelta(days=1), "estado": "activo"},
    ]
    for tasa in tasas:
        TasaComision.objects.create(**tasa)

class Migration(migrations.Migration):
    dependencies = [
        ("clientes", "0008_limiteclientetipo"),
        ("usuarios", "0008_create_default_admin_user"),
    ]

    operations = [
        migrations.RunPython(crear_clientes),
    ]
