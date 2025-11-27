# Crear un entorno virtual llamado venv
python -m venv venv

# Activar el entorno virtual
& .\venv\Scripts\Activate.ps1

# Verificar si el archivo .env no existe y crearlo copiando del archivo dot_env_sample
if (-Not (Test-Path -Path ".env")) {
    Copy-Item -Path "dot_env_sample" -Destination ".env"
}

# Instalar los requisitos desde requirements.txt
pip install -r requirements.txt

# Ejecutar el programa app.py
python app.py