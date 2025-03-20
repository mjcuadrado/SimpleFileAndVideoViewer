# Rutas de contenido
from flask import render_template, request, redirect, url_for, session, jsonify
import os
from app.services.file_service import scan_cursos, scan_cursos_filtered, serve_file
from app.services.video_service import get_video_info
from app.config import Config  # Importar Config

def register_content_routes(app):
    @app.context_processor
    def inject_globals():
        try:
            cursos = scan_cursos()
            # Contar cursos, secciones y archivos para el log
            total_cursos = len(cursos)
            total_secciones = sum(len(secciones) for secciones in cursos.values())
            total_archivos = sum(
                len(contenido['videos']) + len(contenido['pdfs'])
                for curso in cursos.values()
                for contenido in curso.values()
            )
            app.logger.info(
                f"Cursos inyectados en globals:\n"
                f"Cursos encontrados: {total_cursos}\n"
                f"Secciones: {total_secciones}\n"
                f"Archivos totales: {total_archivos}\n"
                f"Ruta: {Config.CURSOS_DIR}"
            )
            return {
                'cursos': cursos,
                'is_admin': session.get('is_admin', False),
                'search_query': request.form.get('search', '')
            }
        except Exception as e:
            app.logger.error(f"Error en inject_globals: {str(e)}", exc_info=True)
            return {'cursos': {}, 'is_admin': False, 'search_query': ''}

    @app.route('/', methods=['GET', 'POST'])
    def index():
        try:
            if not session.get('logged_in'):
                app.logger.debug("Usuario no autenticado, redirigiendo a login")
                return redirect(url_for('login'))
            
            search_query = request.form.get('search', '').lower()
            selected_curso = request.args.get('curso')

            if search_query and request.method == 'POST':
                app.logger.debug(f"Filtrando cursos con búsqueda: {search_query}")
                cursos = scan_cursos_filtered(search_query)
            else:
                cursos = scan_cursos()

            app.logger.debug(f"Cursos cargados en index: {cursos}")
            if not selected_curso and cursos:
                selected_curso = list(cursos.keys())[0]
                app.logger.debug(f"Curso seleccionado automáticamente: {selected_curso}")

            return render_template('index.html', cursos=cursos, search_query=search_query, 
                                selected_curso=selected_curso)
        except Exception as e:
            app.logger.error(f"Error en index: {str(e)}", exc_info=True)
            return "Error interno del servidor", 500

    @app.route('/inspect/<curso>/<path:seccion>/<filename>', methods=['GET'])
    def inspect_video(curso, seccion, filename):
        try:
            if not session.get('logged_in'):
                app.logger.debug("Usuario no autenticado, redirigiendo a login")
                return redirect(url_for('login'))
            file_path = os.path.join(Config.CURSOS_DIR, curso, seccion, filename)
            app.logger.debug(f"Intentando inspeccionar: {file_path}")
            if os.path.isfile(file_path):
                video_info = get_video_info(file_path)
                return jsonify(video_info)
            app.logger.error(f"Archivo no encontrado para inspección: {file_path}")
            return jsonify({'error': 'Archivo no encontrado'}), 404
        except Exception as e:
            app.logger.error(f"Error en inspect_video: {str(e)}", exc_info=True)
            return jsonify({'error': 'Error interno del servidor'}), 500

    @app.route('/cursos/<curso>/<filename>', methods=['GET'])
    def serve_file_no_section(curso, filename):
        try:
            if not session.get('logged_in'):
                app.logger.debug("Usuario no autenticado, redirigiendo a login")
                return redirect(url_for('login'))
            file_path = os.path.join(Config.CURSOS_DIR, curso, filename)
            app.logger.debug(f"Intentando servir archivo sin sección: {file_path}")
            return serve_file(file_path, filename)
        except Exception as e:
            app.logger.error(f"Error en serve_file_no_section: {str(e)}", exc_info=True)
            return "Error interno del servidor", 500

    @app.route('/cursos/<curso>/<path:seccion>/<filename>', methods=['GET'])
    def serve_file_with_section(curso, seccion, filename):
        try:
            if not session.get('logged_in'):
                app.logger.debug("Usuario no autenticado, redirigiendo a login")
                return redirect(url_for('login'))
            file_path = os.path.join(Config.CURSOS_DIR, curso, seccion, filename)
            app.logger.debug(f"Intentando servir archivo con sección: {file_path}")
            return serve_file(file_path, filename)
        except Exception as e:
            app.logger.error(f"Error en serve_file_with_section: {str(e)}", exc_info=True)
            return "Error interno del servidor", 500