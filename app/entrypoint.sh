#!/bin/sh
# app/entrypoint.sh

set -e

echo "=== Iniciando entrypoint de Django ==="

# Esperar a que PostgreSQL esté listo
echo "Esperando a PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "PostgreSQL está disponible"

# Ejecutar migraciones
echo "Ejecutando migraciones..."
python manage.py migrate --noinput

# Insertar configuración de facturación desde variables de entorno
echo "Insertando configuración de facturación..."
python manage.py shell << EOF
import os
from facturacion.models import ConfiguracionFacturacion
from django.utils.timezone import now

if not ConfiguracionFacturacion.objects.exists():
    ConfiguracionFacturacion.objects.create(
        id=1,
        ruc_emisor=os.getenv('FACTURACION_RUC_EMISOR', '2595733'),
        dv_emisor=os.getenv('FACTURACION_DV_EMISOR', '3'),
        nombre_emisor=os.getenv('FACTURACION_NOMBRE_EMISOR', 'GLOBAL EXCHANGE'),
        direccion_emisor=os.getenv('FACTURACION_DIRECCION_EMISOR', 'YVAPOVO C/ TOBATI'),
        numero_casa=os.getenv('FACTURACION_NUMERO_CASA', '1543'),
        departamento_emisor='1',
        descripcion_departamento='CAPITAL',
        ciudad_emisor='1',
        descripcion_ciudad='ASUNCION (DISTRITO)',
        telefono_emisor=os.getenv('FACTURACION_TELEFONO_EMISOR', '(0961)988439'),
        email_emisor=os.getenv('FACTURACION_EMAIL_EMISOR', 'ggonzar@gmail.com'),
        numero_timbrado=os.getenv('FACTURACION_NUMERO_TIMBRADO', '02595733'),
        fecha_inicio_timbrado=os.getenv('FACTURACION_FECHA_INICIO_TIMBRADO', '2025-03-27'),
        sql_proxy_url=os.getenv('SQL_PROXY_BASE_URL', 'http://sql-proxy-web:5000'),
        activo=True
    )
    print("✅ Configuración de facturación insertada desde variables de entorno")
else:
    print("✅ Configuración de facturación ya existe")
EOF

# Colectar archivos estáticos
echo "Colectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

echo "=== Entrypoint completado ==="

# Ejecutar el comando principal
exec "$@"