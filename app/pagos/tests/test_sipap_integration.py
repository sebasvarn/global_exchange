#!/usr/bin/env python
"""
Script de prueba rápida para verificar integración SIPAP.
Ejecutar con: python manage.py shell < test_sipap_integration.py
"""

print("=" * 70)
print("🧪 PRUEBA DE INTEGRACIÓN SIPAP")
print("=" * 70)

# Imports
from clientes.models import Cliente
from monedas.models import Moneda
from payments.models import PaymentMethod
from transaccion.models import Transaccion
from transaccion.services import calcular_transaccion, crear_transaccion, confirmar_transaccion
from commons.enums import PaymentTypeEnum, TipoTransaccionEnum, EstadoTransaccionEnum
from decimal import Decimal

print("\n📋 Paso 1: Verificar métodos agregados a PaymentMethod...")

# Verificar que los métodos existen
metodos_esperados = ['puede_usar_sipap', 'get_metodo_sipap', 'get_datos_sipap']
for metodo in metodos_esperados:
    if hasattr(PaymentMethod, metodo):
        print(f"  ✅ {metodo}() existe")
    else:
        print(f"  ❌ {metodo}() NO existe")
        exit(1)

print("\n📋 Paso 2: Obtener/crear cliente y moneda de prueba...")

# Obtener primer cliente o crear uno
try:
    cliente = Cliente.objects.first()
    if not cliente:
        print("  ⚠️  No hay clientes. Crear uno en el admin primero.")
        exit(1)
    print(f"  ✅ Cliente: {cliente}")
except Exception as e:
    print(f"  ❌ Error al obtener cliente: {e}")
    exit(1)

# Obtener moneda USD
try:
    moneda = Moneda.objects.get(codigo='USD')
    print(f"  ✅ Moneda: {moneda}")
except Moneda.DoesNotExist:
    print("  ⚠️  Moneda USD no existe. Crear en el admin primero.")
    exit(1)

print("\n📋 Paso 3: Crear métodos de pago de prueba...")

# Limpiar métodos de prueba anteriores
PaymentMethod.objects.filter(
    cliente=cliente,
    tarjeta_nombre__in=["TEST SIPAP APRUEBA", "TEST SIPAP RECHAZA"]
).delete()

# Tarjeta que APRUEBA (últimos 2 dígitos: 00 = no primo)
tarjeta_ok = PaymentMethod.objects.create(
    cliente=cliente,
    payment_type=PaymentTypeEnum.TARJETA.value,
    tarjeta_nombre="TEST SIPAP APRUEBA",
    tarjeta_numero="4532123456780000",  # 00 no es primo → APRUEBA
    tarjeta_vencimiento="12/25",
    tarjeta_cvv="123",
    tarjeta_marca="VISA"
)
print(f"  ✅ Tarjeta APRUEBA creada: {tarjeta_ok}")
print(f"     - puede_usar_sipap(): {tarjeta_ok.puede_usar_sipap()}")
print(f"     - get_metodo_sipap(): {tarjeta_ok.get_metodo_sipap()}")
print(f"     - get_datos_sipap(): {tarjeta_ok.get_datos_sipap()}")

# Tarjeta que RECHAZA (últimos 2 dígitos: 13 = primo)
tarjeta_fail = PaymentMethod.objects.create(
    cliente=cliente,
    payment_type=PaymentTypeEnum.TARJETA.value,
    tarjeta_nombre="TEST SIPAP RECHAZA",
    tarjeta_numero="4532123456780013",  # 13 es primo → RECHAZA
    tarjeta_vencimiento="12/25",
    tarjeta_cvv="456",
    tarjeta_marca="MASTERCARD"
)
print(f"  ✅ Tarjeta RECHAZA creada: {tarjeta_fail}")

print("\n📋 Paso 4: Verificar que SIPAP esté corriendo...")

import requests
try:
    response = requests.get("http://localhost:8001/health", timeout=2)
    if response.status_code == 200:
        print(f"  ✅ SIPAP está corriendo: {response.json()}")
    else:
        print(f"  ⚠️  SIPAP responde pero con status {response.status_code}")
        print(f"     Ejecutar: cd simulador_sipap && make start")
except requests.exceptions.RequestException as e:
    print(f"  ❌ SIPAP NO está corriendo: {e}")
    print(f"     Ejecutar: cd simulador_sipap && make start")
    exit(1)

print("\n📋 Paso 5: Crear transacción de prueba (SIN confirmar)...")

# Calcular transacción
try:
    calculo = calcular_transaccion(
        cliente=cliente,
        tipo=TipoTransaccionEnum.COMPRA,
        moneda=moneda,
        monto_operado=Decimal("100.00")
    )
    print(f"  ✅ Cálculo exitoso:")
    print(f"     - Tasa: {calculo['tasa_aplicada']}")
    print(f"     - Comisión: {calculo['comision']}")
    print(f"     - Monto PYG: {calculo['monto_pyg']}")
except Exception as e:
    print(f"  ❌ Error en cálculo: {e}")
    exit(1)

# Crear transacción con tarjeta que APRUEBA
try:
    transaccion = crear_transaccion(
        cliente=cliente,
        tipo=TipoTransaccionEnum.COMPRA,
        moneda=moneda,
        monto_operado=Decimal("100.00"),
        tasa_aplicada=calculo['tasa_aplicada'],
        comision=calculo['comision'],
        monto_pyg=calculo['monto_pyg'],
        medio_pago=tarjeta_ok
    )
    print(f"  ✅ Transacción creada: #{transaccion.id} (UUID: {transaccion.uuid})")
    print(f"     - Estado: {transaccion.estado}")
    print(f"     - Medio: {transaccion.medio_pago}")
except Exception as e:
    print(f"  ❌ Error al crear transacción: {e}")
    exit(1)

print("\n📋 Paso 6: Confirmar transacción (debe pasar por SIPAP)...")

try:
    transaccion_confirmada = confirmar_transaccion(transaccion)
    print(f"  ✅ Transacción confirmada exitosamente!")
    print(f"     - Estado final: {transaccion_confirmada.estado}")
    print(f"     - Debe ser: {EstadoTransaccionEnum.PAGADA}")
    
    if transaccion_confirmada.estado == EstadoTransaccionEnum.PAGADA:
        print(f"  🎉 ¡PRUEBA EXITOSA!")
    else:
        print(f"  ⚠️  Estado inesperado")
        
except Exception as e:
    print(f"  ❌ Error al confirmar: {e}")
    print(f"  Nota: Si el error es de SIPAP, verificar:")
    print(f"     1. Que SIPAP esté corriendo (make health)")
    print(f"     2. Logs de SIPAP (make logs)")
    print(f"     3. Que la validación sea correcta (últimos 2 dígitos)")

print("\n📋 Paso 7: Intentar confirmar transacción que debe FALLAR...")

# Crear otra transacción con tarjeta que RECHAZA
try:
    transaccion_fail = crear_transaccion(
        cliente=cliente,
        tipo=TipoTransaccionEnum.COMPRA,
        moneda=moneda,
        monto_operado=Decimal("100.00"),
        tasa_aplicada=calculo['tasa_aplicada'],
        comision=calculo['comision'],
        monto_pyg=calculo['monto_pyg'],
        medio_pago=tarjeta_fail
    )
    print(f"  ✅ Transacción FAIL creada: #{transaccion_fail.id}")
    
    # Intentar confirmar (debe fallar)
    try:
        confirmar_transaccion(transaccion_fail)
        print(f"  ⚠️  ATENCIÓN: La transacción NO debería haber sido confirmada!")
    except Exception as e:
        print(f"  ✅ Rechazo esperado: {str(e)[:100]}...")
        print(f"  🎉 ¡VALIDACIÓN DE RECHAZO FUNCIONA!")
        
except Exception as e:
    print(f"  ❌ Error inesperado: {e}")

print("\n" + "=" * 70)
print("✅ PRUEBAS COMPLETADAS")
print("=" * 70)
print("\n📊 Para ver estadísticas de SIPAP:")
print("   cd simulador_sipap && make stats")
print("\n📋 Para ver pagos registrados:")
print("   cd simulador_sipap && make logs-pagos")
print("=" * 70)
