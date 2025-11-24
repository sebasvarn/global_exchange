from django.db import migrations

def poblar_medios_acreditacion(apps, schema_editor):
    Cliente = apps.get_model('clientes', 'Cliente')
    MedioAcreditacion = apps.get_model('medios_acreditacion', 'MedioAcreditacion')
    clientes = Cliente.objects.all().order_by('id')[:5]
    medios = [
        [
            {
                'tipo_medio': 'cuenta_bancaria',
                'titular_cuenta': 'Titular 1',
                'tipo_cuenta': 'Caja de ahorro',
                'banco': 'Banco Nacional',
                'numero_cuenta': '1234567890',
            },
            {
                'tipo_medio': 'billetera',
                'proveedor_billetera': 'PayPal',
                'billetera_email_telefono': 'cliente1@email.com',
                'billetera_titular': 'Titular 1',
            },
        ],
        [
            {
                'tipo_medio': 'cuenta_bancaria',
                'titular_cuenta': 'Titular 2',
                'tipo_cuenta': 'Corriente',
                'banco': 'Banco Regional',
                'numero_cuenta': '2222222222',
            },
            {
                'tipo_medio': 'billetera',
                'proveedor_billetera': 'MercadoPago',
                'billetera_email_telefono': 'cliente2@email.com',
                'billetera_titular': 'Titular 2',
            },
        ],
        [
            {
                'tipo_medio': 'cuenta_bancaria',
                'titular_cuenta': 'Titular 3',
                'tipo_cuenta': 'Caja de ahorro',
                'banco': 'Banco Continental',
                'numero_cuenta': '3333333333',
            },
            {
                'tipo_medio': 'billetera',
                'proveedor_billetera': 'Wise',
                'billetera_email_telefono': 'cliente3@email.com',
                'billetera_titular': 'Titular 3',
            },
        ],
        [
            {
                'tipo_medio': 'cuenta_bancaria',
                'titular_cuenta': 'Titular 4',
                'tipo_cuenta': 'Corriente',
                'banco': 'Banco Familiar',
                'numero_cuenta': '4444444444',
            },
            {
                'tipo_medio': 'billetera',
                'proveedor_billetera': 'PayPal',
                'billetera_email_telefono': 'cliente4@email.com',
                'billetera_titular': 'Titular 4',
            },
        ],
        [
            {
                'tipo_medio': 'cuenta_bancaria',
                'titular_cuenta': 'Titular 5',
                'tipo_cuenta': 'Caja de ahorro',
                'banco': 'Banco Regional',
                'numero_cuenta': '5555555555',
            },
            {
                'tipo_medio': 'billetera',
                'proveedor_billetera': 'MercadoPago',
                'billetera_email_telefono': 'cliente5@email.com',
                'billetera_titular': 'Titular 5',
            },
        ],
    ]
    for cliente, medios_cliente in zip(clientes, medios):
        for medio in medios_cliente:
            MedioAcreditacion.objects.create(cliente=cliente, **medio)

class Migration(migrations.Migration):
    dependencies = [
        ("medios_acreditacion", "0003_remove_medioacreditacion_monto"),
        ("clientes", "0009_auto_poblar_clientes"),
    ]

    operations = [
        migrations.RunPython(poblar_medios_acreditacion),
    ]
