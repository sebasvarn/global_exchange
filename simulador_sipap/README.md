# Simulador SIPAP - Pasarela de Pagos

Simulador interno de pasarela de pagos para Global Exchange. Soporta múltiples métodos de pago con reglas de validación configurables.

## 🚀 Características

- ✅ **Múltiples métodos de pago**: Tarjeta de débito/crédito, billetera electrónica, transferencia bancaria
- ✅ **Base de datos PostgreSQL**: Persistencia de transacciones
- ✅ **API RESTful**: Documentación automática con FastAPI
- ✅ **Reglas de validación**: Simulación realista de aprobación/rechazo

## 📋 Requisitos

- Python 3.10+
- PostgreSQL 13+
- pip (gestor de paquetes)

## 🛠️ Instalación

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar base de datos

Ejecutar el script de inicialización:

```bash
psql -U simulador -d simulador_pagos -f init_db.sql
```

O si ya tienes una base de datos existente con los campos antiguos, ejecutar la migración:

```bash
psql -U simulador -d simulador_pagos -f migrate_remove_fields.sql
```

### 3. Configurar variables de entorno

Crear archivo `.env`:

```env
DB_HOST=localhost
DB_PORT=5433
DB_NAME=simulador_pagos
DB_USER=simulador
DB_PASSWORD=simulador123
```

## ▶️ Ejecución

### Modo desarrollo (con recarga automática)

```bash
python main.py
```

### Modo producción

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

El servicio estará disponible en: `http://localhost:8080`

## 📚 Documentación API

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## 🔍 Métodos de Pago

### 1. Tarjeta de Débito (`tarjeta`)
- **Validación**: Siempre aprueba (simulación simplificada)
- **Uso**: Pagos directos desde cuenta bancaria
- 
### 3. Billetera Electrónica (`billetera`)
- **Validación**: Rechaza si últimos 2 dígitos son números primos
- **Campo requerido**: `numero_billetera` (teléfono o email)
- **Ejemplos**:
  - ✅ `0981123450` → Éxito (50 no es primo)
  - ❌ `0981123457` → Rechazado (57 contiene 7 primo)
  - ✅ `user@domain.com` → Éxito (hash mod 100 no primo)

### 4. Transferencia Bancaria (`transferencia`)
- **Validación**: Rechaza si contiene "000" o tiene menos de 6 caracteres
- **Campo requerido**: `numero_comprobante`
- **Ejemplos**:
  - ✅ `ABC123XYZ` → Éxito
  - ❌ `ABC000XYZ` → Rechazado (contiene "000")
  - ❌ `12345` → Rechazado (< 6 caracteres)


## ADMIN PANEL
http://localhost:8080/admin


## 🔧 Endpoints Principales

### Crear Pago
```http
POST /pago
Content-Type: application/json

{
  "monto": 100000,
  "metodo": "billetera",
  "moneda": "PYG",
  "numero_billetera": "0981123450"
}
```

### Consultar Pago
```http
GET /pago/{id_pago}
```

### Listar Pagos (Admin)
```http
GET /admin/pagos?limite=50&estado=exito&metodo=billetera
```

### Estadísticas (Admin)
```http
GET /admin/estadisticas
```

### Health Check
```http
GET /health
```