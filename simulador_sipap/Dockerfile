# simulador_sipap/Dockerfile
FROM python:3.11-slim

LABEL maintainer="Global Exchange Team"
LABEL description="Simulador de Pasarela de Pagos con FastAPI y PostgreSQL"
LABEL version="1.0.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copiar código fuente ---
COPY . .

# Crear carpeta static si no existe
RUN mkdir -p /app/static

# Marcar entrypoint como ejecutable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

HEALTHCHECK --interval=20s --timeout=10s --start-period=25s --retries=5 \
    CMD curl -fsS http://localhost:8080/health || exit 1

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
