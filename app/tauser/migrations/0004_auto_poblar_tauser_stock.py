from django.db import migrations
import os
import json

def poblar_tauser_stock(apps, schema_editor):
    Tauser = apps.get_model('tauser', 'Tauser')
    Denominacion = apps.get_model('tauser', 'Denominacion')
    TauserStock = apps.get_model('tauser', 'TauserStock')
    Moneda = apps.get_model('monedas', 'Moneda')

    # Leer denominaciones desde el JSON y crearlas si no existen
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, 'denominaciones.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            denominaciones_json = json.load(f)
        for d in denominaciones_json:
            moneda = Moneda.objects.filter(codigo=d['currency']).first()
            if moneda:
                Denominacion.objects.get_or_create(
                    moneda=moneda,
                    value=d['value'],
                    type=d['type']
                )

    tausers = Tauser.objects.all()
    denominaciones = Denominacion.objects.all()
    # Asignar 100 unidades de cada denominación a cada tauser
    for tauser in tausers:
        for denominacion in denominaciones:
            stock, created = TauserStock.objects.get_or_create(
                tauser=tauser,
                denominacion=denominacion,
                defaults={"quantity": 1000}
            )
            if not created:
                stock.quantity = 1000
                stock.save()

class Migration(migrations.Migration):
    dependencies = [
        ("tauser", "0003_auto_poblar_tausers"),
    ]

    operations = [
        migrations.RunPython(poblar_tauser_stock),
    ]