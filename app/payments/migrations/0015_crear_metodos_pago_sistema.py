from django.db import migrations


def crear_metodos_pago_sistema(apps, schema_editor):
    """
    Crea métodos de pago "sistema" para efectivo y tarjeta que no requieren
    datos específicos del cliente pero necesitan un registro para mantener
    consistencia en el modelo.
    """
    PaymentMethod = apps.get_model('payments', 'PaymentMethod')
    Cliente = apps.get_model('clientes', 'Cliente')
    
    # Obtener un cliente "sistema" o crear uno si no existe
    try:
        cliente_sistema, created = Cliente.objects.get_or_create(
            nombre='Sistema',
            defaults={
                'tipo': 'CORP',
                'estado': 'activo',
            }
        )
        
        # Crear método de pago para EFECTIVO (universal)
        PaymentMethod.objects.get_or_create(
            payment_type='efectivo',
            cliente=cliente_sistema,
            defaults={
                'titular_cuenta': 'Sistema - Efectivo',
                'banco': 'Caja',
                'numero_cuenta': 'EFECTIVO',
            }
        )
        
        # Crear método de pago para TARJETA (universal - procesado por Stripe)
        PaymentMethod.objects.get_or_create(
            payment_type='tarjeta',
            cliente=cliente_sistema,
            defaults={
                'titular_cuenta': 'Sistema - Tarjeta',
                'banco': 'Stripe',
                'numero_cuenta': 'STRIPE',
            }
        )
        
        print("✅ Métodos de pago sistema creados correctamente")
        
    except Exception as e:
        print(f"⚠️ No se pudieron crear métodos sistema: {e}")
        print("Se crearán bajo demanda cuando se registre una transacción")


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0014_alter_comisionmetodopago_tipo_metodo'),
        ('clientes', '0009_auto_poblar_clientes'),
    ]

    operations = [
        migrations.RunPython(
            crear_metodos_pago_sistema,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
