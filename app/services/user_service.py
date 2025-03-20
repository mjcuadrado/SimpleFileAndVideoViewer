# Lógica para usuarios
import bcrypt
from app.__init__ import db
from app.models.user_model import User
from flask import current_app

def authenticate_user(username, password):
    try:
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return user
        return None
    except Exception as e:
        current_app.logger.error(f"Error en authenticate_user: {str(e)}", exc_info=True)
        return None

def create_user(username, password, is_admin=False):
    try:
        if User.query.filter_by(username=username).first():
            return False, "El usuario ya existe"
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_user = User(username=username, password=hashed_pw, is_admin=is_admin)
        db.session.add(new_user)
        db.session.commit()
        return True, "Usuario creado"
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error en create_user: {str(e)}", exc_info=True)
        return False, "Error al crear el usuario"

def delete_user(user_id, current_username):
    try:
        user = User.query.get(user_id)
        if not user:
            return False, "Usuario no encontrado"
        if user.username == current_username:
            return False, "No puedes eliminarte a ti mismo"
        db.session.delete(user)
        db.session.commit()
        return True, "Usuario eliminado"
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error en delete_user: {str(e)}", exc_info=True)
        return False, "Error al eliminar el usuario"