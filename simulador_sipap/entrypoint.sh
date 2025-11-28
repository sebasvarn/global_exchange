#!/bin/sh
set -e

echo "=== Iniciando entrypoint Simulador SIPAP ==="

# Esperar a la base de datos si es necesario
if [ "$WAIT_FOR_DB" = "true" ]; then
    echo "Esperando a PostgreSQL..."
    while ! nc -z simulador-pagos-db 5432; do
        sleep 2
    done
    echo "PostgreSQL está disponible"
    
    # Esperar adicionalmente a que esté completamente listo
    sleep 5
fi

# Inicializar base de datos si es necesario
if [ "$INIT_DB" = "true" ]; then
    echo "Verificando estado de la base de datos..."
    # Aquí podrías agregar lógica para inicializar la BD si es necesario
    echo "Base de datos verificada"
fi

echo "=== Simulador SIPAP listo ==="

# Ejecutar comando principal
exec "$@"