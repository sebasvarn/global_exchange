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

## 📖 Opciones del Menú

### 1️⃣ Iniciar Django (Puerto 8000)
Inicia solo el servidor Django. Útil cuando:
- Solo necesitas el backend principal
- Ya tienes SIPAP corriendo
- Estás trabajando en features que no usan la pasarela

**Servicios iniciados:**
- ✅ Django en `http://localhost:8000`

### 2️⃣ Iniciar SIPAP (Puerto 8080)
Inicia el simulador de pasarela de pagos con su base de datos. Útil cuando:
- Necesitas probar procesamiento de pagos
- Estás desarrollando features de transacciones
- Quieres ver estadísticas de pagos simulados

**Servicios iniciados:**
- ✅ PostgreSQL (Docker) en puerto 5433
- ✅ SIPAP FastAPI en `http://localhost:8080`
- ✅ Docs interactivas en `http://localhost:8080/docs`

### 3️⃣ Iniciar AMBOS servicios
Inicia Django + SIPAP en paralelo. Útil cuando:
- Necesitas el stack completo
- Vas a crear y confirmar transacciones
- Estás haciendo pruebas end-to-end

**Servicios iniciados:**
- ✅ PostgreSQL (Docker)
- ✅ SIPAP en background
- ✅ Django en foreground

**Nota:** SIPAP corre en background, Django en foreground. Al presionar Ctrl+C detienes Django pero SIPAP sigue corriendo.

### 4️⃣ Ver estado de servicios
Muestra el estado actual de todos los servicios:
- Si están corriendo o detenidos
- En qué puerto están
- El PID del proceso

### 5️⃣ Ver estadísticas de SIPAP
Muestra las estadísticas de pagos procesados:
- Total de pagos
- Exitosos vs Fallidos
- Tasa de éxito
- Distribución por método de pago

### 6️⃣ Detener todos los servicios
Detiene gracefully todos los servicios en orden:
1. Django
2. SIPAP
3. PostgreSQL (Docker)

### 0️⃣ Salir
Sale del script sin detener servicios.

## 🎨 Características

### ✨ Interfaz Visual
- Colores para fácil lectura
- Iconos para identificar servicios
- Estado claro de cada operación

### 🔒 Validaciones
- Verifica si Docker está corriendo
- Detecta puertos ocupados
- Previene múltiples instancias
- Manejo de errores graceful

### 🧹 Auto-setup
- Crea entornos virtuales si no existen
- Instala dependencias automáticamente
- Ejecuta migraciones de Django
- Inicializa base de datos de SIPAP

### 🔄 Reinicio Automático
- SIPAP usa `--reload` para hot-reload
- Django detecta cambios automáticamente

## 📝 Ejemplos de Uso

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

### Ver estadísticas sin detener servicios
```bash
./dev_services.sh
# Seleccionar: 5 (Ver estadísticas)
# Ver datos, presionar Enter
# Volver al menú
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
# o
open -a Docker  # macOS
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

### Entornos Virtuales

- **Django:** `.venv` en `/app/`
- **SIPAP:** `venv` en `/simulador_sipap/`

## 🎯 Casos de Uso por Rol

### Desarrollador Backend
```bash
./dev_services.sh → Opción 3 (AMBOS)
# Trabaja en Django, prueba con SIPAP integrado
```

### Desarrollador Frontend
```bash
./dev_services.sh → Opción 1 (Django)
# Solo necesitas el backend, no pagos
```

### QA / Tester
```bash
./dev_services.sh → Opción 3 (AMBOS)
# Luego opción 5 para ver estadísticas después de pruebas
```

### DevOps / Infra
```bash
./dev_services.sh → Opción 4 (Ver estado)
# Verificar qué está corriendo
./dev_services.sh → Opción 6 (Detener todo)
# Limpiar antes de deploy
```

## 🚦 Checklist de Inicio

Antes de usar el script por primera vez:

- [ ] Docker instalado y corriendo
- [ ] Python 3.8+ instalado
- [ ] Git clone del repositorio
- [ ] Permisos de ejecución: `chmod +x dev_services.sh`

## 💡 Tips

1. **Usa tmux/screen** para mantener servicios en background persistentes
2. **Alias útil:** Agrega a `.bashrc` o `.zshrc`:
   ```bash
   alias devstart='cd ~/is2/global_exchange && ./dev_services.sh'
   ```
3. **VS Code Terminal:** Corre el script en la terminal integrada de VS Code
4. **Logs en tiempo real:** Usa `tail -f /tmp/sipap.log` en otra terminal

## 📚 Referencias

- [Integración SIPAP](./INTEGRACION_SIPAP_COMPLETADA.md)
- [Documentación SIPAP](./simulador_sipap/README.md)
- [Makefile SIPAP](./simulador_sipap/Makefile)

## 🆘 Soporte

Si encuentras problemas:

1. Revisa los logs: `docker-compose logs` o `/tmp/sipap.log`
2. Verifica el estado: Opción 4 del menú
3. Detén todo y reinicia: Opción 6, luego vuelve a iniciar
4. Revisa los puertos: `lsof -i :8000,8080,5433`

---

**¡Happy coding! 🚀**
