# Marca app/ como paquete
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Inicializar db fuera de la función para evitar ciclos
db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    # Cargar configuraciones
    from app.config import Config
    app.config.from_object(Config)
    
    # Inicializar la base de datos
    db.init_app(app)
    
    # Registrar rutas
    from app.routes import init_routes
    init_routes(app)
    
    return app