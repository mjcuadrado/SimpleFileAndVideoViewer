# Configuraciones de la app
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'supersecreto')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://user:password@db:5432/oposicionesdb')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CURSOS_DIR = "/cursos"
    ARCHIVE_DIR = os.path.join(CURSOS_DIR, "_archive")
    TEMP_DIR = os.path.join(CURSOS_DIR, "_temp")
    MAX_QUEUE_SIZE = int(os.getenv('MAX_QUEUE_SIZE', 5))