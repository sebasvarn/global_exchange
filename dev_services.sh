#!/bin/bash
# Script unificado para gestionar servicios de desarrollo
# Uso: ./dev_services.sh [sipap|django|all|stop|status]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIPAP_DIR="$PROJECT_ROOT/simulador_sipap"
APP_DIR="$PROJECT_ROOT/app"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

start_sipap() {
    echo ""
    log_info "Iniciando Simulador de Pasarela de Pagos (SIPAP)"
    echo "============================================="
    
    cd "$SIPAP_DIR"
    
    # Verificar si Docker está corriendo
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker no está corriendo"
        echo "   Por favor inicia Docker Desktop o el daemon de Docker"
        exit 1
    fi
    
    # Iniciar PostgreSQL con Docker Compose
    log_info "Iniciando PostgreSQL..."
    docker-compose up -d
    
    # Esperar a que PostgreSQL esté listo
    log_info "Esperando a que PostgreSQL esté listo..."
    for i in {1..30}; do
        if docker exec simulador_pagos_db pg_isready -U simulador -d simulador_pagos > /dev/null 2>&1; then
            log_success "PostgreSQL iniciado correctamente en puerto 5433"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "PostgreSQL no pudo iniciarse en 30 segundos"
            docker-compose logs postgres
            exit 1
        fi
        sleep 1
    done
    
    # Inicializar base de datos
    log_info "Inicializando base de datos..."
    ./init_database.sh > /dev/null 2>&1 || log_warning "Base de datos ya existe"
    
    # Verificar/Crear entorno virtual
    if [ ! -d "venv" ]; then
        log_info "Creando entorno virtual..."
        python3 -m venv venv
    fi
    
    # Activar entorno virtual e instalar dependencias
    log_info "Instalando/Actualizando dependencias..."
    source venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    
    # Iniciar FastAPI en background
    log_info "Iniciando FastAPI en puerto 8080..."
    nohup python main.py > sipap.log 2>&1 &
    SIPAP_PID=$!
    echo $SIPAP_PID > sipap.pid
    
    # Esperar a que FastAPI esté listo
    sleep 3
    if ps -p $SIPAP_PID > /dev/null; then
        log_success "SIPAP iniciado correctamente"
        log_success "API:            http://localhost:8080"
        log_success "Documentación:  http://localhost:8080/docs"
        log_success "Health Check:   http://localhost:8080/health"
    else
        log_error "SIPAP no pudo iniciarse. Ver sipap.log para detalles"
        cat sipap.log
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
}

start_django() {
    echo ""
    log_info "Iniciando Django Development Server"
    echo "===================================="
    
    cd "$APP_DIR"
    
    # Verificar si el entorno virtual existe
    if [ ! -d "../.venv" ]; then
        log_warning "Entorno virtual no encontrado. Creando..."
        python3 -m venv ../.venv
        source ../.venv/bin/activate
        pip install -q --upgrade pip
        pip install -q -r ../requirements.txt
    else
        source ../.venv/bin/activate
    fi
    
    # Aplicar migraciones pendientes
    log_info "Verificando migraciones..."
    python manage.py migrate --noinput > /dev/null 2>&1
    
    # Iniciar Django
    log_info "Iniciando servidor Django en puerto 8000..."
    nohup python manage.py runserver 0.0.0.0:8000 > ../django.log 2>&1 &
    DJANGO_PID=$!
    echo $DJANGO_PID > ../django.pid
    
    # Esperar a que Django esté listo
    sleep 3
    if ps -p $DJANGO_PID > /dev/null; then
        log_success "Django iniciado correctamente"
        log_success "Aplicación: http://localhost:8000"
        log_success "Admin:      http://localhost:8000/admin"
    else
        log_error "Django no pudo iniciarse. Ver django.log para detalles"
        cat ../django.log
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
}

stop_all() {
    echo ""
    log_info "Deteniendo todos los servicios"
    echo "==============================="
    
    # Detener Django
    if [ -f "$PROJECT_ROOT/django.pid" ]; then
        DJANGO_PID=$(cat "$PROJECT_ROOT/django.pid")
        if ps -p $DJANGO_PID > /dev/null 2>&1; then
            log_info "Deteniendo Django (PID: $DJANGO_PID)..."
            kill $DJANGO_PID 2>/dev/null || true
            log_success "Django detenido"
        fi
        rm -f "$PROJECT_ROOT/django.pid"
    else
        # Fallback: buscar por nombre de proceso
        pkill -f "manage.py runserver" 2>/dev/null && log_success "Django detenido" || true
    fi
    
    # Detener SIPAP FastAPI
    cd "$SIPAP_DIR"
    if [ -f "sipap.pid" ]; then
        SIPAP_PID=$(cat sipap.pid)
        if ps -p $SIPAP_PID > /dev/null 2>&1; then
            log_info "Deteniendo SIPAP FastAPI (PID: $SIPAP_PID)..."
            kill $SIPAP_PID 2>/dev/null || true
            log_success "SIPAP FastAPI detenido"
        fi
        rm -f sipap.pid
    else
        # Fallback: buscar por nombre de proceso
        pkill -f "python.*main.py" 2>/dev/null && log_success "SIPAP FastAPI detenido" || true
    fi
    
    # Detener PostgreSQL de SIPAP
    log_info "Deteniendo PostgreSQL de SIPAP..."
    docker-compose down > /dev/null 2>&1
    log_success "PostgreSQL detenido"
    
    cd "$PROJECT_ROOT"
    
    # Limpiar archivos de log antiguos (opcional)
    # Comentar las siguientes líneas si quieres mantener los logs entre reinicios
    # rm -f "$PROJECT_ROOT/django.log"
    # rm -f "$SIPAP_DIR/sipap.log"
    
    echo ""
    log_success "Todos los servicios detenidos correctamente"
}

show_status() {
    echo ""
    log_info "Estado de los servicios"
    echo "======================="
    echo ""
    
    # Django
    if pgrep -f "manage.py runserver" > /dev/null; then
        log_success "Django:     ✓ Corriendo (http://localhost:8000)"
    else
        log_warning "Django:     ✗ Detenido"
    fi
    
    # SIPAP FastAPI
    if pgrep -f "python.*main.py" > /dev/null; then
        log_success "SIPAP API:  ✓ Corriendo (http://localhost:8080)"
    else
        log_warning "SIPAP API:  ✗ Detenido"
    fi
    
    # PostgreSQL SIPAP
    cd "$SIPAP_DIR"
    if docker-compose ps 2>/dev/null | grep -q "Up"; then
        log_success "PostgreSQL: ✓ Corriendo (localhost:5433)"
    else
        log_warning "PostgreSQL: ✗ Detenido"
    fi
    cd "$PROJECT_ROOT"
    
    echo ""
}

show_menu() {
    echo ""
    echo "🌐 URLs disponibles:"
    echo "   Django:"
    echo "     - Aplicación: http://localhost:8000"
    echo "     - Admin:      http://localhost:8000/admin"
    echo ""
    echo "   SIPAP:"
    echo "     - API:        http://localhost:8080"
    echo "     - Docs:       http://localhost:8080/docs"
    echo "     - Health:     http://localhost:8080/health"
    echo "     - PostgreSQL: localhost:5433"
    echo ""
    echo "📋 Comandos útiles:"
    echo "   - Ver logs Django: tail -f $PROJECT_ROOT/django.log"
    echo "   - Ver logs SIPAP:  tail -f $SIPAP_DIR/sipap.log"
    echo "   - Ver logs DB:     cd simulador_sipap && docker-compose logs -f postgres"
    echo "   - Acceder a DB:    docker exec -it simulador_pagos_db psql -U simulador -d simulador_pagos"
    echo "   - Detener todo:    ./dev_services.sh stop"
    echo "   - Ver estado:      ./dev_services.sh status"
    echo ""
}

# Trap para limpieza en caso de interrupción
cleanup() {
    echo ""
    log_warning "Interrupción detectada. Deteniendo servicios..."
    stop_all
    exit 0
}

trap cleanup INT TERM

# Main
case "${1:-all}" in
    sipap)
        start_sipap
        show_menu
        log_info "Presiona Ctrl+C para detener los servicios"
        # Mantener el script corriendo
        tail -f "$SIPAP_DIR/sipap.log"
        ;;
    django)
        start_django
        show_menu
        log_info "Presiona Ctrl+C para detener los servicios"
        # Mantener el script corriendo
        tail -f "$PROJECT_ROOT/django.log"
        ;;
    all)
        start_sipap
        sleep 2
        start_django
        show_menu
        log_info "Presiona Ctrl+C para detener todos los servicios"
        # Mantener el script corriendo mostrando ambos logs
        tail -f "$PROJECT_ROOT/django.log" -f "$SIPAP_DIR/sipap.log"
        ;;
    stop)
        stop_all
        ;;
    status)
        show_status
        ;;
    *)
        echo "Uso: $0 [sipap|django|all|stop|status]"
        echo ""
        echo "Comandos:"
        echo "  sipap   - Iniciar solo SIPAP (FastAPI + PostgreSQL)"
        echo "  django  - Iniciar solo Django"
        echo "  all     - Iniciar todos los servicios (por defecto)"
        echo "  stop    - Detener todos los servicios"
        echo "  status  - Mostrar estado de los servicios"
        exit 1
        ;;
esac