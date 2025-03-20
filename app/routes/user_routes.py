# Rutas de gestión de usuarios
from flask import render_template, request, redirect, url_for, session
from app.models.user_model import User
from app.services.user_service import create_user, delete_user

def register_user_routes(app):
    @app.route('/admin/users', methods=['GET', 'POST'])
    def manage_users():
        try:
            app.logger.info("Accediendo a la ruta /admin/users")
            if not session.get('logged_in') or not session.get('is_admin'):
                app.logger.warning("Usuario no autenticado o no es admin, redirigiendo a index")
                return redirect(url_for('index'))

            if request.method == 'POST':
                app.logger.info("Procesando solicitud POST en /admin/users")
                action = request.form.get('action')
                if action == 'add':
                    app.logger.debug("Acción: agregar usuario")
                    username = request.form.get('username')
                    password = request.form.get('password')
                    if not username or not password:
                        app.logger.error("Usuario o contraseña no proporcionados")
                        return render_template('users.html', users=User.query.all(), error="Usuario y contraseña son obligatorios")
                    is_admin = 'is_admin' in request.form
                    success, message = create_user(username, password, is_admin)
                    if not success:
                        app.logger.error(f"Error al crear usuario: {message}")
                        return render_template('users.html', users=User.query.all(), error=message)
                    app.logger.info(f"Usuario {username} creado con éxito")
                elif action == 'delete':
                    app.logger.debug("Acción: eliminar usuario")
                    user_id = request.form.get('user_id')
                    if not user_id:
                        app.logger.error("ID de usuario no proporcionado")
                        return render_template('users.html', users=User.query.all(), error="ID de usuario no proporcionado")
                    success, message = delete_user(user_id, session.get('username'))
                    if not success:
                        app.logger.error(f"Error al eliminar usuario: {message}")
                        return render_template('users.html', users=User.query.all(), error=message)
                    app.logger.info(f"Usuario con ID {user_id} eliminado con éxito")

            app.logger.debug("Obteniendo lista de usuarios")
            users = User.query.all()
            app.logger.info("Renderizando plantilla users.html")
            return render_template('users.html', users=users, error=None)

        except Exception as e:
            app.logger.error(f"Error en manage_users: {str(e)}", exc_info=True)
            return "Error interno del servidor", 500