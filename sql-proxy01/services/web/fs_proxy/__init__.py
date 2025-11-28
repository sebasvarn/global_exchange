from flask import Flask
from fs_proxy.db import db
from logging.config import dictConfig
import logging

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '%(asctime)s fs_proxy %(levelname)-8s %(filename)s(%(lineno)d) %(funcName)s(): %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'DEBUG',
        'handlers': ['wsgi']
    },
    'disable_existing_loggers': False
})

# Create a Flask application instance
app = Flask(__name__)
app.config.from_object("fs_proxy.config.Config")

# Inicializar base de datos
db.init_app(app)
logging.debug("Iniciamos app flask")

# Configurar CORS
try:
    from flask_cors import CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:8000", 
                "http://127.0.0.1:8000", 
                "http://globalexchange:8000",
                "http://localhost:3000",
                "http://127.0.0.1:3000"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"]
        }
    })
    logging.debug("CORS configurado exitosamente")
except ImportError:
    logging.warning("Flask-CORS no instalado. Ejecuta: pip install flask-cors")

# One time setup - crear tablas si no existen
with app.app_context():
    try:
        db.create_all()
        db.session.commit()
        logging.debug("Base de datos inicializada")
    except Exception as e:
        logging.error(f"Error al inicializar base de datos: {e}")

# Importar y registrar todas las vistas y APIs
from fs_proxy.views import *
from fs_proxy.api import api_bp  # Importar el blueprint de API

# Registrar el blueprint de API
app.register_blueprint(api_bp)
logging.debug("Blueprint de API registrado")

logging.debug("Aplicación Flask completamente inicializada")