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
                'payment_type': 'tarjeta',
                'tarjeta_nombre': 'Titular 2',
                'tarjeta_numero': '4111111111112222',
                'tarjeta_vencimiento': '11/29',
                'tarjeta_cvv': '234',
                'tarjeta_marca': 'Mastercard',
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
                'payment_type': 'tarjeta',
                'tarjeta_nombre': 'Titular 3',
                'tarjeta_numero': '4111111111113333',
                'tarjeta_vencimiento': '10/28',
                'tarjeta_cvv': '345',
                'tarjeta_marca': 'Visa',
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
                'payment_type': 'tarjeta',
                'tarjeta_nombre': 'Titular 5',
                'tarjeta_numero': '4111111111115555',
                'tarjeta_vencimiento': '09/27',
                'tarjeta_cvv': '456',
                'tarjeta_marca': 'Visa',
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
        ("payments", "0010_descuentometodopago"),
        ("clientes", "0009_auto_poblar_clientes"),
    ]

    operations = [
        migrations.RunPython(poblar_metodos_pago),
    ]
