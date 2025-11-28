from flask_cors import CORS

def init_cors(app):
    """
    Configura CORS para permitir peticiones desde Global Exchange
    """
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