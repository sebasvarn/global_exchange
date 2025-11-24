#!/bin/bash
# Script para iniciar PostgreSQL + Simulador FastAPI

set -e

echo "🚀 Iniciando Simulador de Pasarela de Pagos"
echo "==========================================="
echo ""

# Verificar si Docker está corriendo
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker no está corriendo"
    echo "   Por favor inicia Docker Desktop o el daemon de Docker"
    exit 1
fi

# Iniciar PostgreSQL con Docker Compose
echo "📦 Iniciando PostgreSQL..."
docker-compose up -d

# Esperar a que PostgreSQL esté listo
echo "⏳ Esperando a que PostgreSQL esté listo..."
for i in {1..30}; do
    if docker exec simulador_pagos_db pg_isready -U simulador -d simulador_pagos > /dev/null 2>&1; then
        echo "✅ PostgreSQL iniciado correctamente en puerto 5433"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Error: PostgreSQL no pudo iniciarse en 30 segundos"
        docker-compose logs postgres
        exit 1
    fi
    sleep 1
done

# Inicializar base de datos
echo "📦 Inicializando base de datos..."
./init_database.sh

# Verificar/Crear entorno virtual
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "📦 Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "📦 Instalando/Actualizando dependencias..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "✅ Todos los servicios iniciados correctamente"
echo ""
echo "🌐 URLs disponibles:"
echo "   - API:            http://localhost:8080"
echo "   - Documentación:  http://localhost:8080/docs"
echo "   - Health Check:   http://localhost:8080/health"
echo "   - PostgreSQL:     localhost:5433"
echo ""
echo "🔧 Comandos útiles:"
echo "   - Ver logs DB:    docker-compose logs -f postgres"
echo "   - Detener todo:   ./stop_all.sh"
echo "   - Acceder a DB:   docker exec -it simulador_pagos_db psql -U simulador -d simulador_pagos"
echo ""
echo "🚀 Iniciando FastAPI en puerto 8080..."
echo ""

# Iniciar FastAPI
python main.py

# Si se interrumpe (Ctrl+C), mostrar mensaje
trap "echo ''; echo '👋 Deteniendo servicios...'; docker-compose down; echo '✅ Servicios detenidos'" EXIT
