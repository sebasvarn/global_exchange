#!/bin/bash
# Script para detener todos los servicios

echo "🛑 Deteniendo Simulador de Pasarela de Pagos"
echo "============================================="
echo ""

# Detener FastAPI (si está corriendo)
echo "🛑 Deteniendo FastAPI..."
pkill -f "uvicorn main:app" 2>/dev/null || echo "   FastAPI no estaba corriendo"

# Detener PostgreSQL con Docker Compose
echo "🛑 Deteniendo PostgreSQL..."
docker-compose down

echo ""
echo "✅ Todos los servicios detenidos correctamente"
