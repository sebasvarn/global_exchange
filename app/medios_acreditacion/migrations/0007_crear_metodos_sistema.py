from django.db import migrations


def crear_metodos_sistema(apps, schema_editor):
    """
    Crea medios de acreditación "sistema" para efectivo y tarjeta.
    """
    MedioAcreditacion = apps.get_model('medios_acreditacion', 'MedioAcreditacion')
    Cliente = apps.get_model('clientes', 'Cliente')
    
    try:
        # Obtener o crear cliente sistema
        cliente_sistema, created = Cliente.objects.get_or_create(
            nombre='Sistema',
            defaults={
                'tipo': 'CORP',
                'estado': 'activo',
            }
        )
        
        # Crear medio de acreditación para EFECTIVO
        MedioAcreditacion.objects.get_or_create(
            tipo_medio='efectivo',
            cliente=cliente_sistema,
            defaults={
                'titular_cuenta': 'Sistema - Efectivo',
                'banco': 'Caja',
                'numero_cuenta': 'EFECTIVO',
            }
        )
        
        # Crear medio de acreditación para TARJETA
        MedioAcreditacion.objects.get_or_create(
            tipo_medio='tarjeta',
            cliente=cliente_sistema,
            defaults={
                'titular_cuenta': 'Sistema - Tarjeta',
                'banco': 'Stripe',
                'numero_cuenta': 'STRIPE',
            }
        )
        
        print("✅ Medios de acreditación sistema creados correctamente")
        
    except Exception as e:
        print(f"⚠️ No se pudieron crear medios sistema: {e}")
        print("Se crearán bajo demanda cuando se registre una transacción")


class Migration(migrations.Migration):

    dependencies = [
        ('medios_acreditacion', '0006_alter_medioacreditacion_tipo_medio'),
        ('clientes', '0009_auto_poblar_clientes'),
    ]

    operations = [
        migrations.RunPython(
            crear_metodos_sistema,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
