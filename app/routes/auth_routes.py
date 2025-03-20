# Rutas de autenticación
from flask import render_template, request, redirect, url_for, session
from app.services.user_service import authenticate_user  # Actualizado

def register_auth_routes(app):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = authenticate_user(username, password)
            if user:
                session['logged_in'] = True
                session['username'] = user.username
                session['is_admin'] = user.is_admin
                return redirect(url_for('index'))
            return render_template('login.html', error="Credenciales incorrectas")
        return render_template('login.html', error=None)

    @app.route('/logout')
    def logout():
        session.pop('logged_in', None)
        session.pop('username', None)
        session.pop('is_admin', None)
        return redirect(url_for('login'))