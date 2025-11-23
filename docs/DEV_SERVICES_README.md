# 🚀 Script de Gestión de Servicios de Desarrollo

## 📋 ¿Qué hace este script?

`dev_services.sh` es un script interactivo que te permite gestionar fácilmente los servicios de desarrollo de **Global Exchange**:

- **Django** (Backend principal) - Puerto 8000
- **SIPAP** (Simulador de pasarela de pagos) - Puerto 8080
- **PostgreSQL** (Base de datos de SIPAP) - Puerto 5433

## 🎯 Uso Rápido

```bash
# Ejecutar el menú interactivo
./dev_services.sh
```

### Desarrollo Normal (Full Stack)
```bash
./dev_services.sh
# Seleccionar: 3 (Iniciar AMBOS)
# Trabajar normalmente
# Ctrl+C cuando termines (Django se detiene, SIPAP sigue)
```

### Solo Backend
```bash
./dev_services.sh
# Seleccionar: 1 (Iniciar Django)
# Trabajar en features que no usan pagos
# Ctrl+C cuando termines
```

### Solo Pagos/SIPAP
```bash
./dev_services.sh
# Seleccionar: 2 (Iniciar SIPAP)
# Probar endpoints de SIPAP directamente
# Ctrl+C cuando termines
```

### Detener todo al final del día
```bash
./dev_services.sh
# Seleccionar: 6 (Detener todos)
# Sale automáticamente después
```

## 🐛 Troubleshooting

### Puerto ocupado
Si ves "ya está corriendo en puerto X":
- Usa opción 4 para ver el estado
- Usa opción 6 para detener todo
- O manualmente: `lsof -ti:8000 | xargs kill` (para puerto 8000)

### Docker no está corriendo
```
❌ Docker no está corriendo
```
**Solución:** Inicia Docker Desktop o el daemon:
```bash
sudo systemctl start docker
```

### PostgreSQL no inicia
Si el healthcheck falla después de 30 segundos:
```bash
cd simulador_sipap
docker-compose logs postgres
```

### SIPAP no inicia después de instalar dependencias
Verifica que `psycopg2-binary` esté instalado:
```bash
cd simulador_sipap
./venv/bin/pip list | grep psycopg2
```

## 📂 Estructura de Logs

- **SIPAP logs:** `/tmp/sipap.log` (cuando corre en background)
- **Django logs:** stdout (terminal actual)
- **PostgreSQL logs:** `docker-compose logs postgres`

## 🔧 Configuración

### Cambiar Puertos

**Django (por defecto 8000):**
Editar en `dev_services.sh` línea ~90:
```bash
python manage.py runserver 0.0.0.0:8000
```

**SIPAP (por defecto 8080):**
Ya configurado en `simulador_sipap/main.py` línea 521:
```python
port=8080
```

## 🚦 Checklist de Inicio

Antes de usar el script por primera vez:

- [ ] Docker instalado y corriendo
- [ ] Python 3.8+ instalado
- [ ] Git clone del repositorio
- [ ] Permisos de ejecución: `chmod +x dev_services.sh`
