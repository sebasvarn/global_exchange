from django.db import migrations

def remove_transferencia_and_update_tarjeta(apps, schema_editor):
    ComisionMetodoPago = apps.get_model('payments', 'ComisionMetodoPago')
    # Eliminar transferencia si existe
    ComisionMetodoPago.objects.filter(tipo_metodo='transferencia').delete()
    # Actualizar valor de tarjeta
    ComisionMetodoPago.objects.filter(tipo_metodo='tarjeta').update(porcentaje_comision=1.5)

class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0017_alter_comisionmetodopago_tipo_metodo'),
    ]

    operations = [
        migrations.RunPython(remove_transferencia_and_update_tarjeta),
    ]