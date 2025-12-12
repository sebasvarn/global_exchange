#!/bin/bash
# Script para inicializar la base de datos de SIPAP

echo "📋 Inicializando base de datos SIPAP..."

# Esperar a que PostgreSQL esté listo
echo "⏳ Esperando a que PostgreSQL esté listo..."
until docker exec simulador_pagos_db pg_isready -U simulador -d simulador_pagos > /dev/null 2>&1; do
    sleep 1
done

echo "✅ PostgreSQL está listo"

# Verificar si la tabla ya existe
TABLE_EXISTS=$(docker exec simulador_pagos_db psql -U simulador -d simulador_pagos -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pagos');")

if [ "$TABLE_EXISTS" = "t" ]; then
    echo "✅ La tabla 'pagos' ya existe. No es necesario inicializar."
else
    echo "📦 Creando tabla 'pagos' y estructura inicial..."
    
    # Ejecutar el script SQL
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    docker exec -i simulador_pagos_db psql -U simulador -d simulador_pagos < "$SCRIPT_DIR/init_db.sql"
    
    if [ $? -eq 0 ]; then
        echo "✅ Base de datos inicializada correctamente"
    else
        echo "❌ Error al inicializar la base de datos"
        exit 1
    fi
fi

echo "🎉 Base de datos lista para usar"
