# Archivo principal: inicializa la app
import logging
import os
import threading
import sys
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from sqlalchemy.exc import OperationalError

# Añadir el directorio /app al sys.path para que las importaciones funcionen
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
print(f"sys.path: {sys.path}")  # Agregar para depuración

# Importaciones absolutas
from app.__init__ import create_app, db
from app.models.user_model import User  # Actualizado
from app.services.user_service import create_user
from app.services.video_service import scan_videos, conversion_worker

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Verificar dependencias
try:
    import flask
    import flask_sqlalchemy
    import bcrypt
    import tenacity
    import dotenv
    logger.info("Todas las dependencias están instaladas correctamente")
except ImportError as e:
    logger.error(f"Error al importar dependencias: {e}")
    raise

# Crear la app
try:
    logger.info("Creando la aplicación Flask...")
    app = create_app()
    logger.info("Aplicación Flask creada con éxito")
except Exception as e:
    logger.error(f"Error al crear la app: {e}")
    raise

# Inicializar la base de datos
@retry(stop=stop_after_attempt(20), wait=wait_fixed(5), retry=retry_if_exception_type(OperationalError))
def init_db():
    with app.app_context():
        logger.info("Creando todas las tablas en la base de datos...")
        db.create_all()
        admin_password = os.getenv('ADMIN_PASSWORD', 'default_password')
        logger.info("Creando o actualizando el usuario admin...")
        success, message = create_user('admin', admin_password, is_admin=True)
        if not success and "ya existe" not in message:
            raise Exception(f"Error al crear el usuario admin: {message}")
        logger.info("Base de datos inicializada con éxito")

try:
    init_db()
except Exception as e:
    logger.error(f"Error al inicializar la base de datos: {e}")
    raise

# Iniciar hilos de conversión y escaneo
logger.info("Iniciando hilo de conversión de videos...")
threading.Thread(target=conversion_worker, daemon=True).start()
logger.info("Iniciando hilo de escaneo de caché de videos...")
threading.Thread(target=scan_videos, args=(app,), daemon=True).start()

if __name__ == '__main__':
    logger.info("Iniciando la aplicación en 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)