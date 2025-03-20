# Rutas para visualización de logs
from flask import render_template, request, redirect, url_for, session
import os

def register_log_routes(app):
    @app.route('/admin/logs', methods=['GET'])
    def view_logs():
        try:
            if not session.get('logged_in') or not session.get('is_admin'):
                app.logger.warning("Usuario no autenticado o no es admin, redirigiendo a index")
                return redirect(url_for('index'))

            # Obtener el nivel de filtro desde los parámetros de la URL
            level_filter = request.args.get('level', '').upper()

            # Leer el archivo de logs
            log_file_path = '/app/logs/app.log'
            logs = []
            if os.path.exists(log_file_path):
                with open(log_file_path, 'r') as f:
                    for line in f:
                        try:
                            # Parsear cada línea del log
                            # Formato: "2025-03-20 21:30:00,123 - flask - WARNING - Mensaje"
                            parts = line.strip().split(' - ', 3)
                            if len(parts) == 4:
                                timestamp, name, level, message = parts
                                # Filtrar por nivel si se especificó
                                if level_filter and level != level_filter:
                                    continue
                                logs.append({
                                    'timestamp': timestamp,
                                    'name': name,
                                    'level': level,
                                    'message': message
                                })
                        except Exception as e:
                            app.logger.warning(f"Error al parsear línea de log: {line} - {str(e)}")
                            continue

            # Ordenar los logs por fecha descendente (más recientes primero)
            logs.sort(key=lambda x: x['timestamp'], reverse=True)

            app.logger.info("Renderizando la página de visualización de logs")
            return render_template('logs.html', logs=logs, level=level_filter)

        except Exception as e:
            app.logger.error(f"Error en view_logs: {str(e)}", exc_info=True)
            return "Error interno del servidor", 500