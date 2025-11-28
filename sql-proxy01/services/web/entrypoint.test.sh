#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Inicializar base de datos
python manage.py create_db

# Inicializar configuración ESI
python init_esi.py

exec "$@"