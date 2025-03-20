# Lógica para manejo de archivos
import os
from flask import send_from_directory
from app.config import Config

def scan_cursos():
    cursos = {}
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
        cursos[curso][seccion] = {'videos': videos, 'pdfs': pdfs}
    return cursos

def scan_cursos_filtered(search_query):
    cursos = {}
    search_query = search_query.lower()
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
    return cursos

def serve_file(file_path, filename):
    if os.path.isfile(file_path):
        if filename.endswith('.mp4'):
            mimetype = 'video/mp4'
        elif filename.endswith('.pdf'):
            mimetype = 'application/pdf'
        else:
            mimetype = 'application/octet-stream'
        return send_from_directory(os.path.dirname(file_path), filename, mimetype=mimetype)
    return "Archivo no encontrado", 404