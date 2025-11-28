:: filepath: /Users/ggonzalez/dev/git/sql-proxy/client/setup_and_run.bat
@echo off

:: Crear un entorno virtual llamado venv
python -m venv venv

:: Activar el entorno virtual
call venv\Scripts\activate.bat

:: Verificar si el archivo .env existe, si no, copiar desde dot_env_sample
if not exist .env (
    copy dot_env_sample .env
)

:: Instalar los requisitos desde requirements.txt
pip install -r requirements.txt

:: Ejecutar el programa app.py
python app.py

:: Desactivar el entorno virtual
deactivate