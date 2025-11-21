# App: Pagos

Aplicación Django para procesar pagos a través del simulador de pasarela de pagos.

## 🎯 Propósito

Esta app **NO** gestiona los métodos de pago del cliente (eso lo hace `payments`).  
Esta app **SÍ** procesa pagos reales enviándolos al simulador de pasarela externa.

## 📦 Componentes

### Modelos
- **`PagoPasarela`**: Registra cada pago procesado con su estado y respuesta

### Servicios
- **`PasarelaService`**: Cliente HTTP para comunicarse con el simulador
- **`PaymentOrchestrator`**: Orquestador que coordina procesadores y pasarela

### Procesadores
- **`TarjetaProcessor`**: Valida y prepara pagos con tarjeta
- **`BilleteraProcessor`**: Valida y prepara pagos con billetera
- **`TransferenciaProcessor`**: Valida y prepara pagos con transferencia

## 🚀 Uso Básico

```python
from pagos.services import PaymentOrchestrator
from decimal import Decimal

# Crear orquestador
orchestrator = PaymentOrchestrator()

# Procesar pago
resultado = orchestrator.procesar_pago(
    transaccion=transaccion,
    monto=Decimal('150000'),
    metodo='tarjeta',
    moneda='PYG',
    datos={
        'numero_tarjeta': '4111111111111111'
    }
)

if resultado['success']:
    pago = resultado['pago']
    if pago.es_exitoso():
        print("✅ Pago exitoso!")
else:
    print(f"❌ Error: {resultado['error']}")
```

## 📋 Integración con Transacciones

```python
# En tu vista de procesamiento
from pagos.services import PaymentOrchestrator, PasarelaNoDisponibleError
from transaccion.models import Transaccion, EstadoTransaccion

def procesar_pago_transaccion(request, transaccion_id):
    transaccion = get_object_or_404(Transaccion, id=transaccion_id)
    
    orchestrator = PaymentOrchestrator()
    
    try:
        resultado = orchestrator.procesar_pago(
            transaccion=transaccion,
            monto=transaccion.monto_origen,
            metodo=request.POST.get('metodo'),
            moneda=transaccion.moneda_origen.codigo,
            datos={
                'numero_tarjeta': request.POST.get('numero_tarjeta')
            }
        )
        
        if resultado['success'] and resultado['pago'].es_exitoso():
            # Actualizar transacción
            transaccion.estado = EstadoTransaccion.objects.get(codigo='PAGADA')
            transaccion.save()
            
            messages.success(request, "¡Pago exitoso!")
        else:
            messages.error(request, "Pago rechazado")
            
    except PasarelaNoDisponibleError:
        messages.error(request, "Pasarela no disponible")
    
    return redirect('resumen_transaccion', transaccion_id=transaccion.id)
```

## ⚙️ Configuración

En `settings.py`:

```python
# Configuración de pasarela de pagos
PASARELA_BASE_URL = env('PASARELA_BASE_URL', default='http://localhost:3001')
PASARELA_TIMEOUT = 30  # segundos
PASARELA_WEBHOOK_URL = 'http://localhost:8000/pagos/webhook/'

INSTALLED_APPS = [
    # ...
    'pagos',  # ← Agregar la app
]
```

## 🗄️ Migraciones

```bash
# Crear migraciones
python manage.py makemigrations pagos

# Aplicar migraciones
python manage.py migrate pagos
```

## 🧪 Testing

```python
from django.test import TestCase
from pagos.services import PaymentOrchestrator
from pagos.models import PagoPasarela
from decimal import Decimal

class PagosTest(TestCase):
    def test_procesar_pago(self):
        orchestrator = PaymentOrchestrator()
        
        resultado = orchestrator.procesar_pago(
            transaccion=self.transaccion,
            monto=Decimal('100000'),
            metodo='tarjeta',
            moneda='PYG',
            datos={'numero_tarjeta': '4111111111111111'}
        )
        
        self.assertTrue(resultado['success'])
```

## 📝 Métodos Disponibles

| Método | Código | Datos Requeridos |
|--------|--------|------------------|
| Tarjeta Débito | `tarjeta` | `numero_tarjeta` |
| Tarjeta Crédito Local | `tarjeta_credito_local` | `numero_tarjeta` |
| Billetera | `billetera` | `numero_billetera` o `telefono` |
| Transferencia | `transferencia` | `numero_comprobante` |

## 🔗 Endpoints

- **Webhook**: `POST /pagos/webhook/` - Recibe notificaciones de la pasarela
- **Consultar**: `GET /pagos/consultar/<id_pago>/` - Consulta estado de un pago

## 📊 Flujo Completo

```
Vista Django
    ↓
PaymentOrchestrator
    ↓
Procesador (validar datos)
    ↓
PasarelaService (HTTP POST)
    ↓
Simulador Externo (puerto 3001)
    ↓
Respuesta con estado
    ↓
Crear PagoPasarela
    ↓
Actualizar Transacción
```

## 🆘 Troubleshooting

### Error: "Pasarela no disponible"
✅ Verifica que el simulador esté corriendo en `http://localhost:3001`

### Error: "Import httpx could not be resolved"
✅ Instala: `pip install httpx`

### Pago queda en "pendiente"
✅ Normal para transferencias. Espera el webhook o consulta manualmente.

## 🎁 Diferencia con `payments`

| App | Propósito |
|-----|-----------|
| **`payments`** | Gestiona métodos de pago del cliente (PaymentMethod, CuentaCliente) |
| **`pagos`** | Procesa pagos reales a través de pasarela externa |

---

**Siguiente paso**: Integra esta app en tus vistas de transacciones usando `PaymentOrchestrator`.
