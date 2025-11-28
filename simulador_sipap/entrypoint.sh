#!/bin/sh
set -e

echo "=== Iniciando entrypoint Simulador SIPAP ==="

# Esperar a PostgreSQL
if [ "$WAIT_FOR_DB" = "true" ]; then
    echo "⏳ Esperando a PostgreSQL ($DB_HOST:$DB_PORT)..."
    until nc -z "$DB_HOST" "$DB_PORT"; do
        sleep 2
    done
    echo "✔ PostgreSQL está disponible"
fi

# Inicializar BD automáticamente usando init_db.sql
if [ "$INIT_DB" = "true" ]; then
    echo "📦 Inicializando base de datos SIPAP..."

    # Ejecutar script SQL dentro del contenedor de Postgres
    psql "postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME" \
        -f "/app/init_db.sql" || true

    echo "✔ Base de datos inicializada"
fi

# Crear carpeta static si no existe
mkdir -p /app/static

echo "=== Simulador SIPAP listo ==="
exec "$@"
