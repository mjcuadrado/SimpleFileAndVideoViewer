# Rutas de autenticación
from flask import render_template, request, redirect, url_for, session
from app.services.user_service import authenticate_user

def register_auth_routes(app):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        try:
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                app.logger.debug(f"Intento de login para usuario: {username}")
                user = authenticate_user(username, password)
                if user:
                    session['logged_in'] = True
                    session['username'] = user.username
                    session['is_admin'] = user.is_admin
                    app.logger.info(f"Usuario {username} autenticado con éxito")
                    return redirect(url_for('index'))
                app.logger.warning(f"Credenciales incorrectas para usuario: {username}")
                return render_template('login.html', error="Credenciales incorrectas")
            return render_template('login.html', error=None)
        except Exception as e:
            app.logger.error(f"Error en login: {str(e)}", exc_info=True)
            return "Error interno del servidor", 500

    @app.route('/logout')
    def logout():
        try:
            app.logger.info(f"Usuario {session.get('username')} ha cerrado sesión")
            session.pop('logged_in', None)
            session.pop('username', None)
            session.pop('is_admin', None)
            return redirect(url_for('login'))
        except Exception as e:
            app.logger.error(f"Error en logout: {str(e)}", exc_info=True)
            return "Error interno del servidor", 500