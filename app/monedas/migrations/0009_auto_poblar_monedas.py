from django.db import migrations
from datetime import datetime, timedelta
from django.utils import timezone

def crear_monedas(apps, schema_editor):

    TasaCambio = apps.get_model('monedas', 'TasaCambio')

    Moneda = apps.get_model('monedas', 'Moneda')
    PrecioBaseComision = apps.get_model('monedas', 'PrecioBaseComision')
    monedas = [
        {"codigo": "PYG", "nombre": "Guaraní Paraguayo", "simbolo": "₲", "decimales": 0, "es_base": True, "activa": True},
        {"codigo": "ARS", "nombre": "Peso Argentino", "simbolo": "$", "decimales": 2, "es_base": False, "activa": True},
        {"codigo": "USD", "nombre": "Dólar Estadounidense", "simbolo": "$", "decimales": 2, "es_base": False, "activa": True},
        {"codigo": "EUR", "nombre": "Euro", "simbolo": "€", "decimales": 2, "es_base": False, "activa": True},
        {"codigo": "BRL", "nombre": "Real Brasileño", "simbolo": "R$", "decimales": 2, "es_base": False, "activa": True},
    ]
    precios = {
        "ARS": {"precio_base": 8, "comision_compra": 1.5, "comision_venta": 3.5},    
        "USD": {"precio_base": 7300, "comision_compra": 50, "comision_venta": 200},
        "EUR": {"precio_base": 7900, "comision_compra": 80, "comision_venta": 170}, 
        "BRL": {"precio_base": 1500, "comision_compra": 20, "comision_venta": 200}, 
    }
    for moneda in monedas:
        obj, _ = Moneda.objects.update_or_create(codigo=moneda["codigo"], defaults=moneda)
        if obj and obj.codigo != "PYG":
            p = precios[obj.codigo]
            PrecioBaseComision.objects.update_or_create(
                moneda=obj,
                defaults={
                    "precio_base": p["precio_base"],
                    "comision_compra": p["comision_compra"],
                    "comision_venta": p["comision_venta"]
                }
            )

            # Poblar 10 cotizaciones históricas, la última es la activa y coincide con precio base y comisiones
            base = p["precio_base"]
            com_compra = p["comision_compra"]
            com_venta = p["comision_venta"]
            hoy = datetime.now()
            fechas = [
                timezone.make_aware(hoy.replace(year=hoy.year-3, month=5, day=15)),
                timezone.make_aware(hoy.replace(year=hoy.year-2, month=8, day=10)),
                timezone.make_aware(hoy.replace(year=hoy.year-2, month=12, day=20)),
                timezone.make_aware(hoy.replace(year=hoy.year-1, month=1, day=5)),
                timezone.make_aware(hoy.replace(year=hoy.year-1, month=4, day=25)),
                timezone.make_aware(hoy.replace(year=hoy.year-1, month=9, day=13)),
                timezone.make_aware(hoy.replace(year=hoy.year, month=2, day=7)),
                timezone.make_aware(hoy.replace(year=hoy.year, month=5, day=19)),
                timezone.make_aware(hoy.replace(year=hoy.year, month=8, day=2)),
            ]
            for i in range(9):
                variacion = (i-5)*0.01 * base
                compra = round((base + variacion) - com_compra, 2)
                venta = round((base + variacion) + com_venta, 2)
                tc = TasaCambio.objects.create(
                    moneda=obj,
                    compra=compra,
                    venta=venta,
                    activa=False,
                    es_automatica=True,
                    fuente="BCP",
                    base_codigo="PYG",
                    ts_fuente=fechas[i]
                )
                tc.fecha_creacion = fechas[i]
                tc.save(update_fields=["fecha_creacion"])
            # Última cotización: la activa, igual a precio base y comisiones, fecha actual
            compra = round(base - com_compra, 2)
            venta = round(base + com_venta, 2)
            tc = TasaCambio.objects.create(
                moneda=obj,
                compra=compra,
                venta=venta,
                activa=True,
                es_automatica=True,
                fuente="BCP",
                base_codigo="PYG",
                ts_fuente=timezone.make_aware(hoy)
            )
            tc.fecha_creacion = timezone.make_aware(hoy)
            tc.save(update_fields=["fecha_creacion"])

class Migration(migrations.Migration):
    dependencies = [
        ("monedas", "0008_alter_tasacambio_variacion"),
    ]

    operations = [
        migrations.RunPython(crear_monedas),
    ]
