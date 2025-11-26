from django.db import migrations

def add_cuenta_bancaria(apps, schema_editor):
    ComisionMetodoPago = apps.get_model('payments', 'ComisionMetodoPago')
    ComisionMetodoPago.objects.get_or_create(
        tipo_metodo='cuenta_bancaria',
        defaults={'porcentaje_comision': 2.00}
    )

class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0019_alter_comisionmetodopago_tipo_metodo'),
    ]
    operations = [
        migrations.RunPython(add_cuenta_bancaria),
    ]
