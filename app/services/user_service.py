# Lógica para usuarios
import bcrypt
from app.__init__ import db
from app.models.user_model import User  # Actualizado

def authenticate_user(username, password):
    user = User.query.filter_by(username=username).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return user
    return None

def create_user(username, password, is_admin=False):
    if User.query.filter_by(username=username).first():
        return False, "El usuario ya existe"
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(username=username, password=hashed_pw, is_admin=is_admin)
    db.session.add(new_user)
    db.session.commit()
    return True, "Usuario creado"

def delete_user(user_id, current_username):
    user = User.query.get(user_id)
    if not user:
        return False, "Usuario no encontrado"
    if user.username == current_username:
        return False, "No puedes eliminarte a ti mismo"
    db.session.delete(user)
    db.session.commit()
    return True, "Usuario eliminado"