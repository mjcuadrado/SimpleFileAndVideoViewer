# Rutas de contenido
from flask import render_template, request, redirect, url_for, session, jsonify
import os
from app.services.file_service import scan_cursos, scan_cursos_filtered, serve_file  # Actualizado
from app.services.video_service import get_video_info  # Actualizado
from app.config import Config

def register_content_routes(app):
    @app.context_processor
    def inject_globals():
        try:
            cursos = scan_cursos()
            return {
                'cursos': cursos,
                'is_admin': session.get('is_admin', False),
                'search_query': request.form.get('search', '')
            }
        except Exception as e:
            app.logger.error(f"Error en inject_globals: {str(e)}")
            return {'cursos': {}, 'is_admin': False, 'search_query': ''}

    @app.route('/', methods=['GET', 'POST'])
    def index():
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        search_query = request.form.get('search', '').lower()
        selected_curso = request.args.get('curso')

        if search_query and request.method == 'POST':
            cursos = scan_cursos_filtered(search_query)
        else:
            cursos = scan_cursos()

        if not selected_curso and cursos:
            selected_curso = list(cursos.keys())[0]

        return render_template('index.html', cursos=cursos, search_query=search_query, 
                            selected_curso=selected_curso)

    @app.route('/inspect/<curso>/<path:seccion>/<filename>', methods=['GET'])
    def inspect_video(curso, seccion, filename):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        file_path = os.path.join(Config.CURSOS_DIR, curso, seccion, filename)
        app.logger.debug(f"Intentando inspeccionar: {file_path}")
        if os.path.isfile(file_path):
            video_info = get_video_info(file_path)
            return jsonify(video_info)
        app.logger.error(f"Archivo no encontrado para inspección: {file_path}")
        return jsonify({'error': 'Archivo no encontrado'}), 404

    @app.route('/cursos/<curso>/<filename>', methods=['GET'])
    def serve_file_no_section(curso, filename):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        file_path = os.path.join(Config.CURSOS_DIR, curso, filename)
        app.logger.debug(f"Intentando servir archivo sin sección: {file_path}")
        return serve_file(file_path, filename)

    @app.route('/cursos/<curso>/<path:seccion>/<filename>', methods=['GET'])
    def serve_file_with_section(curso, seccion, filename):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        file_path = os.path.join(Config.CURSOS_DIR, curso, seccion, filename)
        app.logger.debug(f"Intentando servir archivo con sección: {file_path}")
        return serve_file(file_path, filename)