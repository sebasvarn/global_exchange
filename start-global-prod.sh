#!/usr/bin/env bash
set -e

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"
LOGFILE="$PROJECT_ROOT/deploy.log"
DATE=$(date "+%Y-%m-%d %H:%M:%S")

echo "====================================================" | tee -a "$LOGFILE"
echo "[ $DATE ] 🚀 Iniciando despliegue automático (PROD)" | tee -a "$LOGFILE"
echo "====================================================" | tee -a "$LOGFILE"

# ============================================================================
# VALIDACIONES
# ============================================================================

function check_file() {
    if [ ! -f "$1" ]; then
        echo "❌ ERROR: No se encontró: $1" | tee -a "$LOGFILE"
        exit 1
    else
        echo "✔ Archivo encontrado: $1" | tee -a "$LOGFILE"
    fi
}

echo "📌 Verificando archivos necesarios..." | tee -a "$LOGFILE"

check_file "$COMPOSE_FILE"
check_file "$PROJECT_ROOT/app/Dockerfile.prod"
check_file "$PROJECT_ROOT/app/.env.prod"
check_file "$PROJECT_ROOT/sql-proxy01/.env.prod"
check_file "$PROJECT_ROOT/sql-proxy01/.env.test.db"
check_file "$PROJECT_ROOT/sql-proxy01/.env-sched.test"

echo "✔ Validaciones completadas" | tee -a "$LOGFILE"

# ============================================================================
# OPCIÓN DEBUG
# ============================================================================
DEBUG=false
if [[ "$1" == "--debug" ]]; then
    DEBUG=true
    echo "🔍 DEBUG ACTIVADO" | tee -a "$LOGFILE"
fi

# ============================================================================
# BAJAR SERVICIOS
# ============================================================================
echo "🛑 Deteniendo servicios anteriores..." | tee -a "$LOGFILE"
docker compose -f "$COMPOSE_FILE" down --remove-orphans || true

# ============================================================================
# BUILD + DEPLOY
# ============================================================================
echo "⚙️ Construyendo imágenes..." | tee -a "$LOGFILE"

docker compose -f "$COMPOSE_FILE" build --no-cache

echo "🚀 Levantando servicios..." | tee -a "$LOGFILE"

docker compose -f "$COMPOSE_FILE" up -d

# ============================================================================
# HEALTHCHECK GLOBAL
# ============================================================================

echo "🩺 Verificando estado de los servicios..." | tee -a "$LOGFILE"

SERVICES=(
    "global_exchange_db"
    "global_exchange_django"
    "sql_proxy_db"
    "sql_proxy_web"
    "sql_proxy_scheduler"
    "simulador_pagos_db"
    "simulador_pagos_api"
)

for svc in "${SERVICES[@]}"; do
    echo "⏳ Esperando que $svc esté healthy..." | tee -a "$LOGFILE"
    for i in {1..30}; do
        STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$svc" 2>/dev/null || echo "starting")

        if [ "$STATUS" == "healthy" ]; then
            echo "✔ $svc está healthy" | tee -a "$LOGFILE"
            break
        fi

        if [ "$STATUS" == "unhealthy" ]; then
            echo "❌ $svc está UNHEALTHY" | tee -a "$LOGFILE"
            exit 1
        fi

        sleep 3
    done

done

echo "🏥 Todos los servicios están listos" | tee -a "$LOGFILE"

# ============================================================================
# LOGS (solo si debug=true)
# ============================================================================
if [ "$DEBUG" = true ]; then
    echo "📜 Mostrando logs (modo debug)..." | tee -a "$LOGFILE"
    docker compose -f "$COMPOSE_FILE" logs -f
fi

# ============================================================================
# FIN
# ============================================================================
echo "====================================================" | tee -a "$LOGFILE"
echo "🎉 DEPLOYMENT COMPLETADO CON ÉXITO (PROD)" | tee -a "$LOGFILE"
echo "===================================================="
