"""
Simulador de Pasarela de Pagos - FastAPI con PostgreSQL
Servicio interno para simular pagos con tarjeta, billetera y transferencia
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from enum import Enum
from uuid import uuid4
from typing import Optional
from datetime import datetime
from contextlib import contextmanager
import httpx
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = FastAPI(
    title="Simulador Pasarela de Pago",
    description="API para simular una pasarela de pago con métodos múltiples",
    version="1.0.0"
)

# CORS para permitir llamadas desde Django
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================================================

DATABASE_CONFIG = {
    'host': os.getenv("DB_HOST", "localhost"),
    'port': int(os.getenv("DB_PORT", "5433")),
    'database': os.getenv("DB_NAME", "simulador_pagos"),
    'user': os.getenv("DB_USER", "simulador"),
    'password': os.getenv("DB_PASSWORD", "simulador123")
}


@contextmanager
def get_db_connection():
    """Context manager para conexiones a la base de datos"""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Inicializar base de datos y crear tablas si no existen"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Crear tabla si no existe
            create_table_query = """
            CREATE TABLE IF NOT EXISTS pagos (
                id_pago VARCHAR(255) PRIMARY KEY,
                monto DECIMAL(15,2) NOT NULL,
                metodo VARCHAR(50) NOT NULL,
                moneda VARCHAR(10) NOT NULL DEFAULT 'PYG',
                estado VARCHAR(50) NOT NULL,
                webhook_url VARCHAR(500),
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                numero_tarjeta VARCHAR(20),
                numero_billetera VARCHAR(20),
                numero_comprobante VARCHAR(50),
                motivo_rechazo VARCHAR(500)
            );
            """
            cursor.execute(create_table_query)
            
            # Agregar índices si no existen
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_pagos_estado ON pagos(estado);",
                "CREATE INDEX IF NOT EXISTS idx_pagos_fecha ON pagos(fecha DESC);",
                "CREATE INDEX IF NOT EXISTS idx_pagos_metodo ON pagos(metodo);",
            ]
            
            for indice in indices:
                cursor.execute(indice)
            
            cursor.close()
            print("✅ Base de datos inicializada correctamente")
    except Exception as e:
        print(f"⚠️  Error inicializando base de datos: {e}")


# Inicializar la base de datos al arrancar
init_database()

# ============================================================================
# SCHEMAS
# ============================================================================

class MetodoPago(str, Enum):
    tarjeta = "tarjeta"
    tarjeta_credito_local = "tarjeta_credito_local"
    billetera = "billetera"
    transferencia = "transferencia"


class EstadoPago(str, Enum):
    exito = "exito"
    fallo = "fallo"
    pendiente = "pendiente"


class PagoRequest(BaseModel):
    monto: float = Field(..., gt=0, description="Monto del pago")
    metodo: MetodoPago = Field(..., description="Método de pago")
    moneda: str = Field(default="PYG", description="Código de moneda")
    escenario: EstadoPago = Field(default=EstadoPago.exito, description="Escenario de simulación (solo para testing)")
    webhook_url: Optional[str] = Field(None, description="URL para notificaciones")
    
    # Campos específicos por método
    numero_tarjeta: Optional[str] = Field(None, description="Número de tarjeta (para tarjeta/tarjeta_credito_local)")
    numero_billetera: Optional[str] = Field(None, description="Número de billetera o teléfono")
    numero_comprobante: Optional[str] = Field(None, description="Código de comprobante de transferencia")


class PagoResponse(BaseModel):
    id_pago: str
    estado: EstadoPago
    fecha: datetime
    motivo_rechazo: Optional[str] = None


# ============================================================================
# LÓGICA DE VALIDACIÓN
# ============================================================================

def es_primo(n: int) -> bool:
    """Verifica si un número es primo"""
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


def validar_pago(pago: PagoRequest) -> tuple[EstadoPago, Optional[str]]:
    """
    Valida el pago según las reglas de negocio específicas por método.
    
    Reglas de validación por método:
    - tarjeta: Rechaza si últimos 2 dígitos son primos (fondos insuficientes)
    - tarjeta_credito_local: Rechaza si últimos 2 dígitos son primos (límite excedido)
    - billetera: Rechaza si últimos 2 dígitos son primos (cuenta suspendida)
    - transferencia: Rechaza si contiene "000" o tiene < 6 caracteres
    
    Returns:
        (estado, motivo_rechazo)
    """
    
    # Si el escenario ya está definido como fallo, respetarlo (útil para testing)
    if pago.escenario == EstadoPago.fallo:
        return EstadoPago.fallo, "Error simulado por configuración"
    
    # Validación para TARJETA DE DÉBITO
    if pago.metodo == MetodoPago.tarjeta:
        if not pago.numero_tarjeta:
            return EstadoPago.fallo, "Número de tarjeta requerido"
        
        try:
            ultimos_digitos = int(pago.numero_tarjeta[-2:])
            if es_primo(ultimos_digitos):
                return (
                    EstadoPago.fallo,
                    "Transacción declinada: fondos insuficientes en la cuenta asociada"
                )
        except (ValueError, IndexError):
            return EstadoPago.fallo, "Número de tarjeta inválido"
    
    # Validación para TARJETA DE CRÉDITO LOCAL
    elif pago.metodo == MetodoPago.tarjeta_credito_local:
        if not pago.numero_tarjeta:
            return EstadoPago.fallo, "Número de tarjeta requerido"
        
        try:
            ultimos_digitos = int(pago.numero_tarjeta[-2:])
            if es_primo(ultimos_digitos):
                return (
                    EstadoPago.fallo,
                    "Tarjeta bloqueada: límite de crédito excedido, contacte a su banco"
                )
        except (ValueError, IndexError):
            return EstadoPago.fallo, "Número de tarjeta inválido"
    
    # Validación para BILLETERA ELECTRÓNICA
    elif pago.metodo == MetodoPago.billetera:
        if not pago.numero_billetera:
            return EstadoPago.fallo, "Número de billetera requerido"
        
        try:
            ultimos_digitos = int(pago.numero_billetera[-2:])
            if es_primo(ultimos_digitos):
                return (
                    EstadoPago.fallo,
                    "Billetera rechazada: cuenta suspendida temporalmente"
                )
        except (ValueError, IndexError):
            return EstadoPago.fallo, "Número de billetera inválido"
    
    # Validación para TRANSFERENCIA BANCARIA
    elif pago.metodo == MetodoPago.transferencia:
        if not pago.numero_comprobante:
            return EstadoPago.fallo, "Número de comprobante requerido"
        
        # Rechazar si contiene "000" (simulando problema bancario)
        if "000" in pago.numero_comprobante:
            return (
                EstadoPago.fallo,
                "Transferencia rechazada: operación no autorizada por el banco origen"
            )
        
        # Rechazar si es muy corto (< 6 caracteres)
        if len(pago.numero_comprobante) < 6:
            return (
                EstadoPago.fallo,
                "Transferencia rechazada: número de comprobante inválido o incompleto"
            )
    
    # Si pasa todas las validaciones, retornar el escenario solicitado
    return pago.escenario, None


def notificar_webhook(url: str, data: dict):
    """Envía notificación a webhook (en background)"""
    try:
        timeout = int(os.getenv("WEBHOOK_TIMEOUT", "5"))
        httpx.post(url, json=data, timeout=timeout)
    except Exception:
        pass  # Ignorar errores de webhook


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
def home():
    """Endpoint de bienvenida"""
    return {
        "servicio": "Simulador de Pasarela de Pagos",
        "version": "1.0.0",
        "base_datos": "PostgreSQL",
        "metodos_pago": ["tarjeta", "tarjeta_credito_local", "billetera", "transferencia"],
        "endpoints": {
            "crear_pago": "POST /pago",
            "consultar_pago": "GET /pago/{id_pago}",
            "listar_pagos": "GET /admin/pagos",
            "estadisticas": "GET /admin/estadisticas",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }


@app.post("/pago", response_model=PagoResponse, summary="Crear pago", tags=["Pagos"])
def crear_pago(pago: PagoRequest, background_tasks: BackgroundTasks):
    """
    Procesa un nuevo pago según el método seleccionado.
    
    ### Reglas de validación por método:
    
    - **tarjeta (débito)**: Rechaza si últimos 2 dígitos son primos
      - ❌ `4111111111111113` (13 es primo) → "Fondos insuficientes"
      - ✅ `4111111111111112` (12 no es primo) → Éxito
    
    - **tarjeta_credito_local**: Rechaza si últimos 2 dígitos son primos
      - ❌ `5500000000000007` (07 es primo) → "Límite excedido"
      - ✅ `5500000000000004` (04 no es primo) → Éxito
    
    - **billetera**: Rechaza si últimos 2 dígitos son primos
      - ❌ `0981123457` (57 termina en 7, primo) → "Cuenta suspendida"
      - ✅ `0981123450` (50 no es primo) → Éxito
    
    - **transferencia**: Rechaza si contiene "000" o < 6 caracteres
      - ❌ `ABC000XYZ` → "Operación no autorizada"
      - ❌ `12345` → "Comprobante inválido"
      - ✅ `ABC123XYZ` → Éxito
    """
    
    # Validar pago según reglas de negocio
    estado_final, motivo_rechazo = validar_pago(pago)
    
    # Generar ID único
    id_pago = str(uuid4())
    fecha_actual = datetime.utcnow()
    
    # Guardar en base de datos PostgreSQL
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO pagos (
            id_pago, monto, metodo, moneda, estado, webhook_url,
            numero_tarjeta, numero_billetera, numero_comprobante,
            motivo_rechazo, fecha
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            id_pago,
            pago.monto,
            pago.metodo.value,
            pago.moneda,
            estado_final.value,
            pago.webhook_url,
            pago.numero_tarjeta,
            pago.numero_billetera,
            pago.numero_comprobante,
            motivo_rechazo,
            fecha_actual
        ))
        
        cursor.close()
    
    # Preparar respuesta
    response = PagoResponse(
        id_pago=id_pago,
        estado=estado_final,
        fecha=fecha_actual,
        motivo_rechazo=motivo_rechazo
    )
    
    # Notificar webhook si existe
    if pago.webhook_url:
        background_tasks.add_task(
            notificar_webhook,
            pago.webhook_url,
            response.dict()
        )
    
    return response


@app.get("/pago/{id_pago}", response_model=PagoResponse, summary="Consultar pago", tags=["Pagos"])
def consultar_pago(id_pago: str):
    """
    Consulta el estado de un pago por su ID.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        select_query = "SELECT * FROM pagos WHERE id_pago = %s"
        cursor.execute(select_query, (id_pago,))
        pago_data = cursor.fetchone()
        
        cursor.close()
    
    if not pago_data:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    return PagoResponse(
        id_pago=pago_data['id_pago'],
        estado=EstadoPago(pago_data['estado']),
        fecha=pago_data['fecha'],
        motivo_rechazo=pago_data.get('motivo_rechazo')
    )


@app.get("/admin/pagos", summary="Listar pagos", tags=["Admin"])
def listar_pagos(
    limite: int = 50,
    estado: Optional[str] = None,
    metodo: Optional[str] = None
):
    """
    Lista todos los pagos procesados con filtros opcionales.
    
    Parámetros:
    - limite: Número máximo de pagos a retornar (default: 50)
    - estado: Filtrar por estado (exito, fallo, pendiente)
    - metodo: Filtrar por método (tarjeta, billetera, etc.)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM pagos WHERE 1=1"
        params = []
        
        if estado:
            query += " AND estado = %s"
            params.append(estado)
        
        if metodo:
            query += " AND metodo = %s"
            params.append(metodo)
        
        query += " ORDER BY fecha DESC LIMIT %s"
        params.append(limite)
        
        cursor.execute(query, params)
        pagos = cursor.fetchall()
        
        # Contar total
        cursor.execute("SELECT COUNT(*) as total FROM pagos")
        total = cursor.fetchone()['total']
        
        cursor.close()
    
    return {
        "total": total,
        "mostrando": len(pagos),
        "pagos": pagos
    }


@app.delete("/admin/pagos", summary="Limpiar base de datos", tags=["Admin"])
def limpiar_pagos():
    """
    Limpia todos los pagos de la base de datos (útil para testing).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pagos")
        deleted_count = cursor.rowcount
        cursor.close()
    
    return {
        "mensaje": "Base de datos limpiada",
        "pagos_eliminados": deleted_count
    }


@app.get("/admin/estadisticas", summary="Estadísticas de pagos", tags=["Admin"])
def estadisticas():
    """
    Retorna estadísticas generales de los pagos procesados.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Total por estado
        cursor.execute("""
            SELECT estado, COUNT(*) as cantidad, SUM(monto) as monto_total
            FROM pagos
            GROUP BY estado
        """)
        por_estado = cursor.fetchall()
        
        # Total por método
        cursor.execute("""
            SELECT metodo, COUNT(*) as cantidad, SUM(monto) as monto_total
            FROM pagos
            GROUP BY metodo
        """)
        por_metodo = cursor.fetchall()
        
        # Total general
        cursor.execute("""
            SELECT 
                COUNT(*) as total_pagos,
                SUM(monto) as monto_total,
                AVG(monto) as monto_promedio
            FROM pagos
        """)
        totales = cursor.fetchone()
        
        cursor.close()
    
    return {
        "totales": totales,
        "por_estado": por_estado,
        "por_metodo": por_metodo
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health", summary="Health Check", tags=["Health"])
def health_check():
    """Verifica que el servicio y la base de datos están funcionando"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pagos")
            total_pagos = cursor.fetchone()[0]
            cursor.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "pagos_procesados": total_pagos,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
