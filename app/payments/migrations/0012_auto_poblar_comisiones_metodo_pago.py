from django.db import migrations

def poblar_comisiones_metodo_pago(apps, schema_editor):
    ComisionMetodoPago = apps.get_model('payments', 'ComisionMetodoPago')
    comisiones = [
        {"tipo_metodo": "tarjeta", "porcentaje_comision": 4.5},
        {"tipo_metodo": "transferencia", "porcentaje_comision": 1.0},
        {"tipo_metodo": "billetera", "porcentaje_comision": 2.5},
    ]
    for com in comisiones:
        ComisionMetodoPago.objects.update_or_create(tipo_metodo=com["tipo_metodo"], defaults={"porcentaje_comision": com["porcentaje_comision"]})

class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0011_auto_poblar_metodos_pago"),
    ]

    operations = [
        migrations.RunPython(poblar_comisiones_metodo_pago),
    ]