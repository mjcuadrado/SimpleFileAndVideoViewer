# Lógica para videos
import os
import subprocess
import threading
import hashlib
import re
import time
import json
from queue import Queue
from app.__init__ import db
from app.config import Config  # Importar Config
from app.models.video_model import ConvertedVideo
from flask import current_app

# Colas y estado global
conversion_queue = Queue(maxsize=Config.MAX_QUEUE_SIZE)
conversion_status = {}
video_candidates_cache = []
cache_status = "scanning"

def get_file_hash(file_path):
    try:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        current_app.logger.error(f"Error en get_file_hash: {str(e)}", exc_info=True)
        return None

def get_video_info(file_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-i', file_path, '-show_streams', '-show_format', '-print_format', 'json'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            info = json.loads(result.stdout)
            video_stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
            return {
                'file_path': file_path,
                'size_mb': round(os.path.getsize(file_path) / (1024 * 1024), 2),
                'format': info['format']['format_name'],
                'video_codec': video_stream['codec_name'] if video_stream else 'N/A',
                'duration': float(info['format'].get('duration', 0))
            }
        current_app.logger.error(f"ffprobe falló: {result.stderr}")
        return {'error': f"ffprobe falló: {result.stderr}"}
    except Exception as e:
        current_app.logger.error(f"Error en get_video_info: {str(e)}", exc_info=True)
        return {'error': str(e)}

def scan_videos(app):
    global video_candidates_cache, cache_status
    while True:
        with app.app_context():
            cache_status = "scanning"
            app.logger.info("Iniciando escaneo recursivo de videos...")
            videos = []
            try:
                processed_videos = {cv.converted_path: cv for cv in ConvertedVideo.query.all()}
                for root, dirs, files in os.walk(Config.CURSOS_DIR):
                    if '_archive' in root or '_temp' in root:
                        continue
                    rel_path = os.path.relpath(root, Config.CURSOS_DIR)
                    if rel_path == '.':
                        continue
                    path_parts = rel_path.split(os.sep)
                    curso = path_parts[0]
                    seccion = '/'.join(path_parts[1:]) or ''
                    for filename in files:
                        if filename.endswith('.mp4'):
                            file_path = os.path.join(root, filename)
                            file_hash = get_file_hash(file_path)
                            if not file_hash:
                                continue
                            status = conversion_status.get(file_path, {'status': 'none', 'message': ''})
                            video_info = get_video_info(file_path)
                            if 'error' in video_info:
                                app.logger.warning(f"Error en ffprobe para {file_path}: {video_info['error']}")
                                continue
                            video_data = {
                                'curso': curso,
                                'seccion': seccion,
                                'filename': filename,
                                'codec': video_info.get('video_codec', 'N/A'),
                                'size_mb': video_info.get('size_mb', 0),
                                'needs_conversion': video_info.get('video_codec') not in ['h264', 'h265'],
                                'status': status['status'],
                                'message': status['message'],
                                'file_path': file_path,
                                'duration': video_info.get('duration', 0),
                                'processed': file_path in processed_videos
                            }
                            videos.append(video_data)
                            if video_data['needs_conversion'] and video_data['status'] not in ['queued', 'processing', 'completed'] and not video_data['processed']:
                                if not conversion_queue.full():
                                    conversion_queue.put(file_path)
                                    conversion_status[file_path] = {'status': 'queued', 'message': 'En cola', 'progress': 0, 'eta': 'Esperando...'}
            except Exception as e:
                app.logger.error(f"Error durante el escaneo de videos: {str(e)}", exc_info=True)
            video_candidates_cache = videos
            cache_status = "ready"
            app.logger.info(f"Caché de videos actualizada: {len(videos)} videos encontrados")
        time.sleep(300)

def convert_video(file_path):
    filename = os.path.basename(file_path)
    temp_output_path = os.path.join(Config.TEMP_DIR, f"{hashlib.md5(filename.encode()).hexdigest()}_h264_temp.mp4")
    archive_path = os.path.join(Config.ARCHIVE_DIR, filename)
    original_hash = get_file_hash(file_path)
    if not original_hash:
        conversion_status[file_path] = {'status': 'failed', 'message': 'No se pudo calcular el hash del archivo', 'progress': 0, 'eta': 'N/A'}
        return
    video_info = get_video_info(file_path)
    duration = video_info.get('duration', 0) if 'duration' in video_info else 0
    conversion_status[file_path] = {'status': 'processing', 'message': 'Iniciando conversión', 'progress': 0, 'eta': 'Calculando...'}

    try:
        process = subprocess.Popen(
            ['ffmpeg', '-i', file_path, '-c:v', 'libx264', '-preset', 'fast', '-c:a', 'copy', '-progress', 'pipe:1', temp_output_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
        )
        for line in process.stdout:
            if 'time=' in line:
                match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                if match:
                    hours, minutes, seconds = map(float, match.groups())
                    elapsed = hours * 3600 + minutes * 60 + seconds
                    if duration > 0:
                        progress = min(100, int((elapsed / duration) * 100))
                        eta = (duration - elapsed) if progress < 100 else 0
                        conversion_status[file_path] = {
                            'status': 'processing',
                            'message': f'Convirtiendo ({progress}%)',
                            'progress': progress,
                            'eta': f"{int(eta // 60)}m {int(eta % 60)}s" if eta > 0 else "Finalizando..."
                        }
        process.wait()
        if process.returncode == 0:
            os.rename(file_path, archive_path)
            os.rename(temp_output_path, file_path)
            with db.session:
                converted = ConvertedVideo(original_hash=original_hash, original_path=archive_path, converted_path=file_path)
                db.session.add(converted)
                db.session.commit()
            conversion_status[file_path] = {'status': 'completed', 'message': f'Convertido y archivado: {file_path}', 'progress': 100, 'eta': '0s'}
        else:
            conversion_status[file_path] = {'status': 'failed', 'message': 'FFmpeg falló', 'progress': 0, 'eta': 'N/A'}
            if os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    except Exception as e:
        conversion_status[file_path] = {'status': 'failed', 'message': str(e), 'progress': 0, 'eta': 'N/A'}
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
        current_app.logger.error(f"Error en convert_video: {str(e)}", exc_info=True)

def conversion_worker():
    while True:
        try:
            file_path = conversion_queue.get()
            convert_video(file_path)
            conversion_queue.task_done()
        except Exception as e:
            current_app.logger.error(f"Error en conversion_worker: {str(e)}", exc_info=True)
            conversion_queue.task_done()

def set_queue_size(new_size):
    try:
        global conversion_queue
        new_queue = Queue(maxsize=new_size)
        while not conversion_queue.empty() and not new_queue.full():
            new_queue.put(conversion_queue.get())
        conversion_queue = new_queue
    except Exception as e:
        current_app.logger.error(f"Error en set_queue_size: {str(e)}", exc_info=True)