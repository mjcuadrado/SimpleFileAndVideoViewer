# Lógica para manejo de archivos
import os
from flask import send_from_directory, current_app, abort
from app.config import Config  # Importar Config

def scan_cursos():
    try:
        cursos = {}
        total_secciones = 0
        total_archivos = 0

        current_app.logger.debug(f"Escaneando directorio: {Config.CURSOS_DIR}")
        if not os.path.exists(Config.CURSOS_DIR):
            current_app.logger.error(f"El directorio {Config.CURSOS_DIR} no existe")
            return {}
        if not os.access(Config.CURSOS_DIR, os.R_OK):
            current_app.logger.error(f"No hay permisos de lectura para {Config.CURSOS_DIR}")
            return {}

        for root, dirs, files in os.walk(Config.CURSOS_DIR):
            if '_archive' in root or '_temp' in root:
                continue
            rel_path = os.path.relpath(root, Config.CURSOS_DIR)
            if rel_path == '.':
                continue
            path_parts = rel_path.split(os.sep)
            curso = path_parts[0]
            seccion = '/'.join(path_parts[1:]) or ''
            if curso not in cursos:
                cursos[curso] = {}
            if seccion not in cursos[curso]:
                cursos[curso][seccion] = {'videos': [], 'pdfs': []}
                total_secciones += 1  # Contar la sección
            videos = [f for f in files if f.endswith('.mp4') and os.path.isfile(os.path.join(root, f))]
            pdfs = [f for f in files if f.endswith('.pdf') and os.path.isfile(os.path.join(root, f))]
            cursos[curso][seccion] = {'videos': videos, 'pdfs': pdfs}
            total_archivos += len(videos) + len(pdfs)  # Sumar los archivos encontrados

        # Registrar el resumen
        current_app.logger.info(
            f"Cursos encontrados: {len(cursos)}\n"
            f"Secciones: {total_secciones}\n"
            f"Archivos totales: {total_archivos}\n"
            f"Ruta: {Config.CURSOS_DIR}"
        )
        return cursos
    except Exception as e:
        current_app.logger.error(f"Error en scan_cursos: {str(e)}", exc_info=True)
        return {}

def scan_cursos_filtered(search_query):
    try:
        cursos = {}
        total_secciones = 0
        total_archivos = 0
        search_query = search_query.lower()

        current_app.logger.debug(f"Filtrando cursos con búsqueda: {search_query}")
        if not os.path.exists(Config.CURSOS_DIR):
            current_app.logger.error(f"El directorio {Config.CURSOS_DIR} no existe")
            return {}
        if not os.access(Config.CURSOS_DIR, os.R_OK):
            current_app.logger.error(f"No hay permisos de lectura para {Config.CURSOS_DIR}")
            return {}

        for root, dirs, files in os.walk(Config.CURSOS_DIR):
            if '_archive' in root or '_temp' in root:
                continue
            rel_path = os.path.relpath(root, Config.CURSOS_DIR)
            if rel_path == '.':
                continue
            path_parts = rel_path.split(os.sep)
            curso = path_parts[0]
            seccion = '/'.join(path_parts[1:]) or ''
            if curso not in cursos:
                cursos[curso] = {}
            if seccion not in cursos[curso]:
                cursos[curso][seccion] = {'videos': [], 'pdfs': []}
            videos = [f for f in files if f.endswith('.mp4') and os.path.isfile(os.path.join(root, f))]
            pdfs = [f for f in files if f.endswith('.pdf') and os.path.isfile(os.path.join(root, f))]
            if (search_query in curso.lower() or 
                search_query in seccion.lower() or 
                any(search_query in v.lower() for v in videos) or 
                any(search_query in p.lower() for p in pdfs)):
                cursos[curso][seccion] = {'videos': videos, 'pdfs': pdfs}
                total_secciones += 1  # Contar la sección filtrada
                total_archivos += len(videos) + len(pdfs)  # Sumar los archivos filtrados

        # Registrar el resumen
        current_app.logger.info(
            f"Cursos encontrados (filtrados): {len(cursos)}\n"
            f"Secciones: {total_secciones}\n"
            f"Archivos totales: {total_archivos}\n"
            f"Ruta: {Config.CURSOS_DIR}"
        )
        return cursos
    except Exception as e:
        current_app.logger.error(f"Error en scan_cursos_filtered: {str(e)}", exc_info=True)
        return {}

def serve_file(file_path, filename):
    try:
        if os.path.isfile(file_path):
            if filename.endswith('.mp4'):
                mimetype = 'video/mp4'
            elif filename.endswith('.pdf'):
                mimetype = 'application/pdf'
            else:
                mimetype = 'application/octet-stream'
            return send_from_directory(os.path.dirname(file_path), filename, mimetype=mimetype)
        current_app.logger.warning(f"Archivo no encontrado para servir: {file_path}")
        abort(404)
    except Exception as e:
        current_app.logger.error(f"Error en serve_file: {str(e)}", exc_info=True)
        abort(500)