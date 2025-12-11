from django.db import migrations
from django.utils import timezone
import random
from datetime import timedelta, datetime, timedelta

def populate_transacciones(apps, schema_editor):
    Transaccion = apps.get_model('transaccion', 'Transaccion')
    Cliente = apps.get_model('clientes', 'Cliente')
    Moneda = apps.get_model('monedas', 'Moneda')
    PaymentMethod = apps.get_model('payments', 'PaymentMethod')
    MedioAcreditacion = apps.get_model('medios_acreditacion', 'MedioAcreditacion')
    Tauser = apps.get_model('tauser', 'Tauser')

    # Obtener instancias necesarias

    clientes = list(Cliente.objects.all())
    monedas = list(Moneda.objects.all())
    medios_pago = list(PaymentMethod.objects.all())
    medios_cobro = list(MedioAcreditacion.objects.all())
    tausers = list(Tauser.objects.all())

    # Datos fijos del usuario
    transacciones = [
        {"tipo": "compra", "monto_operado": 100.00, "monto_pyg": 750000.00, "tasa_aplicada": 7500.0000, "comision": 200.00, "estado": "pendiente", "cliente_id": 1, "moneda_id": 3, "medio_pago_id": 11, "medio_cobro_id": None, "uuid": "0c8a52be-6956-45b4-8451-6dd030786ee5", "codigo_verificacion": "V3JTN6", "fecha": "2024-11-02 16:28:18.074000+00:00", "fecha_expiracion": "2025-12-05 16:17:38.605619+00:00", "tauser_id": 1, "ganancia": None},
        {"tipo": "compra", "monto_operado": 150.00, "monto_pyg": 257050.00, "tasa_aplicada": 1680.0000, "comision": 200.00, "estado": "pagada", "cliente_id": 4, "moneda_id": 5, "medio_pago_id": 7, "medio_cobro_id": None, "uuid": "ef85fdbd-72e0-4f1b-b40e-d884388e19e0", "codigo_verificacion": "8LHB6K", "fecha": "2025-05-08 16:28:18.071000+00:00", "fecha_expiracion": "2025-12-06 16:19:57.288007+00:00", "tauser_id": 3, "ganancia": 30000.00},
        {"tipo": "venta", "monto_operado": 200.00, "monto_pyg": 296000.00, "tasa_aplicada": 1480.0000, "comision": 20.00, "estado": "completada", "cliente_id": 3, "moneda_id": 5, "medio_pago_id": None, "medio_cobro_id": 5, "uuid": "44705de4-c52a-4053-a89e-4cab2003acb8", "codigo_verificacion": "G9OCYD", "fecha": "2024-12-09 16:28:18.066000+00:00", "fecha_expiracion": "2025-12-07 16:20:18.189683+00:00", "tauser_id": 3, "ganancia": 4000.00},
        {"tipo": "venta", "monto_operado": 123.00, "monto_pyg": 961850.00, "tasa_aplicada": 7820.0000, "comision": 80.00, "estado": "pendiente", "cliente_id": 3, "moneda_id": 4, "medio_pago_id": None, "medio_cobro_id": 11, "uuid": "4bbedf47-72d2-4afa-846a-998e20b0144f", "codigo_verificacion": "V79EWD", "fecha": "2025-12-08 16:28:18.073000+00:00", "fecha_expiracion": "2025-12-08 16:21:14.429432+00:00", "tauser_id": 4, "ganancia": None},
        {"tipo": "compra", "monto_operado": 120.00, "monto_pyg": 207650.00, "tasa_aplicada": 1680.0000, "comision": 200.00, "estado": "cancelada", "cliente_id": 4, "moneda_id": 5, "medio_pago_id": 8, "medio_cobro_id": None, "uuid": "ae87dc4f-765e-47a8-a672-d83d03a47b54", "codigo_verificacion": "35390W", "fecha": "2023-06-12 16:28:18.062000+00:00", "fecha_expiracion": "2025-12-09 16:21:32.968882+00:00", "tauser_id": 2, "ganancia": None},
        {"tipo": "compra", "monto_operado": 1200.00, "monto_pyg": 14000.00, "tasa_aplicada": 11.5000, "comision": 3.50, "estado": "pagada", "cliente_id": 3, "moneda_id": 2, "medio_pago_id": 12, "medio_cobro_id": None, "uuid": "e3723648-e070-486b-af28-b0d6aef7c4fb", "codigo_verificacion": "GOCBIL", "fecha": "2025-05-08 16:28:18.070000+00:00", "fecha_expiracion": "2025-12-10 16:21:54.358646+00:00", "tauser_id": 5, "ganancia": 4200.00},
        {"tipo": "venta", "monto_operado": 2000.00, "monto_pyg": 13150.00, "tasa_aplicada": 6.5750, "comision": 1.50, "estado": "completada", "cliente_id": 5, "moneda_id": 2, "medio_pago_id": None, "medio_cobro_id": 10, "uuid": "48465df6-ea66-4345-ad04-4606c6f6211a", "codigo_verificacion": "QWTC1F", "fecha": "2025-12-08 16:28:18.065000+00:00", "fecha_expiracion": "2025-12-11 16:23:11.401843+00:00", "tauser_id": 4, "ganancia": 3000.00},
        {"tipo": "venta", "monto_operado": 80.00, "monto_pyg": 118500.00, "tasa_aplicada": 1481.0000, "comision": 20.00, "estado": "cancelada", "cliente_id": 2, "moneda_id": 5, "medio_pago_id": None, "medio_cobro_id": 3, "uuid": "abd6c8ad-b626-4f3a-aa32-a6a241ca2dbd", "codigo_verificacion": "DB04C9", "fecha": "2023-06-12 16:28:18.069000+00:00", "fecha_expiracion": "2025-12-12 16:24:00.602793+00:00", "tauser_id": 4, "ganancia": None},
        {"tipo": "compra", "monto_operado": 100.00, "monto_pyg": 831200.00, "tasa_aplicada": 8070.0000, "comision": 170.00, "estado": "anulada", "cliente_id": 1, "moneda_id": 4, "medio_pago_id": 2, "medio_cobro_id": None, "uuid": "489801c9-6442-4506-9b31-ebd840d6e2cb", "codigo_verificacion": "LGZ1QM", "fecha": "2024-11-01 16:28:18.067000+00:00", "fecha_expiracion": "2025-12-13 16:24:39.564203+00:00", "tauser_id": 2, "ganancia": None},
        {"tipo": "venta", "monto_operado": 100.00, "monto_pyg": 650.00, "tasa_aplicada": 6.5750, "comision": 1.50, "estado": "anulada", "cliente_id": 5, "moneda_id": 2, "medio_pago_id": None, "medio_cobro_id": 9, "uuid": "0c041e06-a524-435c-8abe-47af9648108b", "codigo_verificacion": "9B18FS", "fecha": "2024-12-05 16:28:18.063000+00:00", "fecha_expiracion": "2025-12-14 16:24:27.861476+00:00", "tauser_id": 1, "ganancia": None},
    ]

    from django.utils.dateparse import parse_datetime
    from django.db import connection
    for t in transacciones:
        fecha = parse_datetime(t["fecha"])
        trans = Transaccion.objects.create(
            tipo=t["tipo"],
            monto_operado=t["monto_operado"],
            monto_pyg=t["monto_pyg"],
            tasa_aplicada=t["tasa_aplicada"],
            comision=t["comision"],
            estado=t["estado"],
            cliente_id=t["cliente_id"],
            moneda_id=t["moneda_id"],
            medio_pago_id=t["medio_pago_id"],
            medio_cobro_id=t["medio_cobro_id"],
            uuid=t["uuid"],
            codigo_verificacion=t["codigo_verificacion"],
            fecha_expiracion=t["fecha_expiracion"],
            fecha_pago=None,
            tauser_id=t["tauser_id"],
            ganancia=t["ganancia"],
        )
        # Actualizar la fecha directamente en la base de datos
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE transaccion_transaccion SET fecha = %s WHERE id = %s",
                [fecha, trans.id]
            )

class Migration(migrations.Migration):
    dependencies = [
        ('transaccion', '0010_transaccion_ganancia'),
    ]
    operations = [
        migrations.RunPython(populate_transacciones),
    ]
