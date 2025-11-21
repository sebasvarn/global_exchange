from django.db import migrations

def poblar_tausers(apps, schema_editor):
    Tauser = apps.get_model('tauser', 'Tauser')
    ubicaciones = [
        "Sucursal Centro",
        "Sucursal Shopping",
        "Sucursal Aeropuerto",
        "Sucursal Villa Morra",
        "Sucursal San Lorenzo",
    ]
    for idx, ubicacion in enumerate(ubicaciones, start=1):
        nombre = f"Tauser {idx}"
        Tauser.objects.create(nombre=nombre, ubicacion=ubicacion, estado="activo")

class Migration(migrations.Migration):
    dependencies = [
        ("tauser", "0002_denominacion_tauserstock"),
    ]

    operations = [
        migrations.RunPython(poblar_tausers),
    ]
