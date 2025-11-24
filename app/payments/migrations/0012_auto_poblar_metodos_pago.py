from django.db import migrations

def poblar_metodos_pago(apps, schema_editor):
    Cliente = apps.get_model('clientes', 'Cliente')
    PaymentMethod = apps.get_model('payments', 'PaymentMethod')
    clientes = Cliente.objects.all().order_by('id')[:5]
    metodos = [
        [
            {
                'payment_type': 'cuenta_bancaria',
                'titular_cuenta': 'Titular 1',
                'tipo_cuenta': 'Caja de ahorro',
                'banco': 'Banco Nacional',
                'numero_cuenta': '1234567890',
            },
            {
                'payment_type': 'billetera',
                'proveedor_billetera': 'PayPal',
                'billetera_email_telefono': 'cliente1@email.com',
                'billetera_titular': 'Titular 1',
            },
        ],
        [
            {
                'payment_type': 'cuenta_bancaria',
                'titular_cuenta': 'Titular 2',
                'tipo_cuenta': 'Corriente',
                'banco': 'Banco Regional',
                'numero_cuenta': '2222222222',
            },
            {
                'payment_type': 'billetera',
                'proveedor_billetera': 'MercadoPago',
                'billetera_email_telefono': 'cliente2@email.com',
                'billetera_titular': 'Titular 2',
            },
        ],
        [
            {
                'payment_type': 'billetera',
                'proveedor_billetera': 'MercadoPago',
                'billetera_email_telefono': 'cliente3@email.com',
                'billetera_titular': 'Titular 3',
            },
            {
                'payment_type': 'cuenta_bancaria',
                'titular_cuenta': 'Titular 3',
                'tipo_cuenta': 'Caja de ahorro',
                'banco': 'Banco Continental',
                'numero_cuenta': '3333333333',
            },
        ],
        [
            {
                'payment_type': 'cuenta_bancaria',
                'titular_cuenta': 'Titular 4',
                'tipo_cuenta': 'Caja de ahorro',
                'banco': 'Banco Continental',
                'numero_cuenta': '4444444444',
            },
            {
                'payment_type': 'billetera',
                'proveedor_billetera': 'Wise',
                'billetera_email_telefono': 'cliente4@email.com',
                'billetera_titular': 'Titular 4',
            },
        ],
        [
            {
                'payment_type': 'cuenta_bancaria',
                'titular_cuenta': 'Titular 5',
                'tipo_cuenta': 'Corriente',
                'banco': 'Banco Nación',
                'numero_cuenta': '5555555555',
            },
            {
                'payment_type': 'billetera',
                'proveedor_billetera': 'PayPal',
                'billetera_email_telefono': 'cliente5@email.com',
                'billetera_titular': 'Titular 5',
            },
        ],
    ]
    for cliente, metodos_cliente in zip(clientes, metodos):
        for metodo in metodos_cliente:
            PaymentMethod.objects.create(cliente=cliente, **metodo)

class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0011_remove_paymentmethod_cheque_banco_and_more"),
    ]

    operations = [
        migrations.RunPython(poblar_metodos_pago),
    ]
