#!/bin/bash

# Crear un entorno virtual llamado venv
python3 -m venv venv

# Activar el entorno virtual
source venv/bin/activate

# Si no existe el archivo .env, crearlo copiando del archivo dot_env_sample
if [ ! -f .env ]; then
    cp dot_env_sample .env
fi

# Instalar los requisitos desde requirements.txt
pip install -r requirements.txt

# Ejecutar el programa app.py
python app.py