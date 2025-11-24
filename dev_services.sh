#!/bin/bash
# Script para levantar servicios: Django y/o SIPAP
# Uso: ./dev_services.sh [sipap|django|all|stop]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIPAP_DIR="$PROJECT_ROOT/simulador_sipap"
APP_DIR="$PROJECT_ROOT/app"

start_sipap() {
    echo "🚀 Iniciando SIPAP..."
    cd "$SIPAP_DIR"
    
    docker-compose up -d
    sleep 2
    ./init_database.sh
    
    nohup ./venv/bin/python main.py > sipap.log 2>&1 &
    echo "✅ SIPAP: http://localhost:8080"
    cd "$PROJECT_ROOT"
}

start_django() {
    echo "🚀 Iniciando Django..."
    cd "$APP_DIR"
    python manage.py runserver 0.0.0.0:8000 &
    echo "✅ Django: http://localhost:8000"
    cd "$PROJECT_ROOT"
}

stop_all() {
    echo "🛑 Deteniendo servicios..."
    pkill -f "python.*main.py" 2>/dev/null || true
    pkill -f "manage.py runserver" 2>/dev/null || true
    cd "$SIPAP_DIR"
    docker-compose down
    cd "$PROJECT_ROOT"
    echo "✅ Servicios detenidos"
}

show_menu() {
    echo ""
    echo "� Servicios:"
    echo "  SIPAP:  http://localhost:8080"
    echo "  Django: http://localhost:8000"
    echo ""
}

case "${1:-all}" in
    sipap)
        start_sipap
        show_menu
        ;;
    django)
        start_django
        show_menu
        wait
        ;;
    all)
        start_sipap
        sleep 2
        start_django
        show_menu
        wait
        ;;
    stop)
        stop_all
        ;;
    *)
        echo "Uso: $0 [sipap|django|all|stop]"
        exit 1
        ;;
esac