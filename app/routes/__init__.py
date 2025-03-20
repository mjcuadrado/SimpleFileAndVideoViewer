# Punto de entrada para registrar todas las rutas
from .auth_routes import register_auth_routes
from .content_routes import register_content_routes
from .user_routes import register_user_routes
from .video_routes import register_video_routes
from .api_routes import register_api_routes

def init_routes(app):
    register_auth_routes(app)
    register_content_routes(app)
    register_user_routes(app)
    register_video_routes(app)
    register_api_routes(app)