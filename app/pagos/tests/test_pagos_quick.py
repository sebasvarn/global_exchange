#!/usr/bin/env python
"""
Script de prueba rápida para verificar el sistema de pagos.

Ejecutar desde el directorio app/:
    python test_pagos_quick.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_exchange.settings.dev')
django.setup()

from decimal import Decimal
from pagos.services import PaymentOrchestrator, PasarelaNoDisponibleError
from transaccion.models import Transaccion
from usuarios.models import User
from clientes.models import Cliente
from monedas.models import Moneda
import json

def print_separator():
    print("\n" + "="*70 + "\n")

def test_simulador_disponible():
    """Verifica que el simulador esté corriendo"""
    print("🔍 Verificando disponibilidad del simulador...")
    
    from pagos.services import PasarelaService
    service = PasarelaService()
    
    try:
        # Intentar hacer health check
        import httpx
        response = httpx.get(f"{service.base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Simulador disponible en {service.base_url}")
            print(f"   Status: {data.get('status')}")
            print(f"   Pagos procesados: {data.get('pagos_procesados', 0)}")
            return True
        else:
            print(f"⚠️  Simulador responde pero con código {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Simulador NO disponible: {e}")
        print(f"   Asegúrate de ejecutar: cd app/pagos/simulador && ./run.sh")
        return False

def test_pago_exitoso():
    """Prueba un pago que debe ser exitoso"""
    print("💳 Probando pago exitoso con tarjeta...")
    
    try:
        # Obtener datos necesarios
        user = User.objects.first()
        if not user:
            print("⚠️  No hay usuarios en la BD. Crea uno primero.")
            return False
        
        cliente = Cliente.objects.filter(usuario=user).first()
        if not cliente:
            print("⚠️  No hay clientes. Creando uno de prueba...")
            cliente = Cliente.objects.create(usuario=user)
        
        pyg = Moneda.objects.filter(codigo='PYG').first()
        if not pyg:
            print("⚠️  Moneda PYG no existe. Créala primero.")
            return False
        
        # Crear transacción de prueba
        txn = Transaccion.objects.create(
            cliente=cliente,
            tipo='COMPRA',
            monto_origen=Decimal('150000'),
            moneda_origen=pyg,
            monto_destino=Decimal('150000'),
            moneda_destino=pyg,
        )
        print(f"   Transacción creada: ID={txn.id}")
        
        # Procesar pago
        orchestrator = PaymentOrchestrator()
        resultado = orchestrator.procesar_pago(
            transaccion=txn,
            monto=Decimal('150000'),
            metodo='tarjeta',
            moneda='PYG',
            datos={'numero_tarjeta': '4111111111111112'}  # 12 no es primo -> éxito
        )
        
        print(f"   Estado: {resultado.get('estado')}")
        print(f"   ID Pago: {resultado.get('id_pago')}")
        
        if resultado.get('estado') == 'exito':
            print("✅ Pago procesado exitosamente")
            return True
        else:
            print(f"⚠️  Pago no exitoso: {resultado.get('motivo_rechazo')}")
            return False
            
    except PasarelaNoDisponibleError as e:
        print(f"❌ Pasarela no disponible: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pago_rechazado():
    """Prueba un pago que debe ser rechazado"""
    print("🚫 Probando pago rechazado con tarjeta (número primo)...")
    
    try:
        user = User.objects.first()
        cliente = Cliente.objects.filter(usuario=user).first()
        pyg = Moneda.objects.filter(codigo='PYG').first()
        
        # Crear transacción de prueba
        txn = Transaccion.objects.create(
            cliente=cliente,
            tipo='COMPRA',
            monto_origen=Decimal('100000'),
            moneda_origen=pyg,
            monto_destino=Decimal('100000'),
            moneda_destino=pyg,
        )
        
        # Procesar pago con número que termina en 13 (primo)
        orchestrator = PaymentOrchestrator()
        resultado = orchestrator.procesar_pago(
            transaccion=txn,
            monto=Decimal('100000'),
            metodo='tarjeta',
            moneda='PYG',
            datos={'numero_tarjeta': '4111111111111113'}  # 13 es primo -> rechazo
        )
        
        print(f"   Estado: {resultado.get('estado')}")
        print(f"   Motivo: {resultado.get('motivo_rechazo')}")
        
        if resultado.get('estado') == 'fallo':
            print("✅ Pago rechazado correctamente")
            return True
        else:
            print(f"⚠️  Se esperaba rechazo pero fue: {resultado.get('estado')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_billetera():
    """Prueba pago con billetera"""
    print("💰 Probando pago con billetera...")
    
    try:
        user = User.objects.first()
        cliente = Cliente.objects.filter(usuario=user).first()
        pyg = Moneda.objects.filter(codigo='PYG').first()
        
        txn = Transaccion.objects.create(
            cliente=cliente,
            tipo='COMPRA',
            monto_origen=Decimal('80000'),
            moneda_origen=pyg,
            monto_destino=Decimal('80000'),
            moneda_destino=pyg,
        )
        
        orchestrator = PaymentOrchestrator()
        resultado = orchestrator.procesar_pago(
            transaccion=txn,
            monto=Decimal('80000'),
            metodo='billetera',
            moneda='PYG',
            datos={'numero_billetera': '0981123450'}  # 50 no es primo
        )
        
        print(f"   Estado: {resultado.get('estado')}")
        
        if resultado.get('estado') == 'exito':
            print("✅ Pago con billetera exitoso")
            return True
        else:
            print(f"⚠️  Pago no exitoso: {resultado.get('motivo_rechazo')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("  🧪 PRUEBAS DEL SISTEMA DE PAGOS")
    print("="*70)
    
    tests = [
        ("Disponibilidad del Simulador", test_simulador_disponible),
        ("Pago Exitoso", test_pago_exitoso),
        ("Pago Rechazado", test_pago_rechazado),
        ("Pago con Billetera", test_billetera),
    ]
    
    results = []
    
    for name, test_func in tests:
        print_separator()
        result = test_func()
        results.append((name, result))
    
    # Resumen
    print_separator()
    print("📊 RESUMEN DE PRUEBAS:")
    print()
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
        if result:
            passed += 1
    
    print()
    print(f"Total: {passed}/{len(results)} pruebas pasadas")
    print("="*70 + "\n")
    
    if passed == len(results):
        print("🎉 ¡Todas las pruebas pasaron! El sistema está funcionando correctamente.")
        return 0
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa los mensajes arriba.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
