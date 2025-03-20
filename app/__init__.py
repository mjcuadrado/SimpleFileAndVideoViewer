# Marca app/ como paquete
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import logging
from logging.handlers import RotatingFileHandler
import os

# Inicializar db fuera de la función para evitar ciclos
db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    
    # Cargar configuraciones
    from app.config import Config
    app.config.from_object(Config)
    
    # Configurar logging
    log_dir = '/app/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configurar el manejador de archivo con rotación
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=1024 * 1024 * 10,  # 10 MB por archivo
        backupCount=5  # Mantener hasta 5 archivos de respaldo
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Configurar el manejador de consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    
    # Configurar el logger de la app
    app.logger.handlers.clear()
    app.logger.setLevel(logging.DEBUG)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    
    # Inicializar la base de datos
    db.init_app(app)
    
    # Registrar rutas
    from app.routes import init_routes
    init_routes(app)
    
    # Manejador global de excepciones
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"Excepción no manejada: {str(e)}", exc_info=True)
        if app.debug:
            raise e
        return "Error interno del servidor. Por favor, contacta al administrador.", 500
    
    # Manejador para errores 404
    @app.errorhandler(404)
    def page_not_found(e):
        app.logger.warning(f"Página no encontrada: {request.url}")
        return render_template('404.html'), 404
    
    return app