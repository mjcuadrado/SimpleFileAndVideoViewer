from flask import Flask, render_template, send_from_directory, request, redirect, url_for, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
import os
import bcrypt
import subprocess
import threading
from queue import Queue
import hashlib
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from sqlalchemy.exc import OperationalError
import logging
import time
import re
from dotenv import load_dotenv
import whisper
import torch  # Añadimos torch para verificar si CUDA está disponible

# Cargar variables de entorno desde .env
load_dotenv()

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecreto')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://user:password@db:5432/oposicionesdb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Inicializa Flask-Migrate

CURSOS_DIR = "/cursos"
ARCHIVE_DIR = os.path.join(CURSOS_DIR, "_archive")
TEMP_DIR = os.path.join(CURSOS_DIR, "_temp")
os.makedirs(ARCHIVE_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

conversion_queue = Queue(maxsize=int(os.getenv('MAX_QUEUE_SIZE', 5)))
conversion_status = {}
video_candidates_cache = []
cache_status = "scanning"

# Verificar si CUDA está disponible
if torch.cuda.is_available():
    app.logger.info("CUDA está disponible. openai-whisper usará GPU.")
    device = "cuda"
else:
    app.logger.info("CUDA no está disponible. openai-whisper usará CPU.")
    device = "cpu"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

class ConvertedVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_hash = db.Column(db.String(64), unique=True, nullable=False)
    original_path = db.Column(db.String(255), nullable=False)
    converted_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='completed')
    has_subtitles = db.Column(db.Boolean, default=False)

class VideoProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    curso = db.Column(db.String(255), nullable=False)
    seccion = db.Column(db.String(255), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    progress = db.Column(db.Float, default=0.0)
    completed = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'curso', 'seccion', 'filename', name='unique_user_video'),)

@retry(stop=stop_after_attempt(20), wait=wait_fixed(5), retry=retry_if_exception_type(OperationalError))
def init_db():
    with app.app_context():
        migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
        try:
            if os.path.exists(migrations_dir):
                upgrade(directory=migrations_dir)
                app.logger.info("Migraciones aplicadas correctamente.")
            else:
                app.logger.warning("Directorio de migraciones no encontrado, creando base de datos desde cero.")
                db.create_all()
        except Exception as e:
            app.logger.error(f"Error al aplicar migraciones o crear la base de datos: {e}")
            app.logger.warning("Usando creación de base de datos como fallback.")
            db.create_all()

        # Configuración inicial de usuario admin
        admin_password = os.getenv('ADMIN_PASSWORD', 'default_password')
        hashed_pw = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            admin_user.password = hashed_pw
            db.session.commit()
        else:
            admin = User(username='admin', password=hashed_pw, is_admin=True)
            db.session.add(admin)
            db.session.commit()

try:
    init_db()
except Exception as e:
    app.logger.error(f"Error grave al inicializar la base de datos, intentando continuar: {e}")
    # Intentar crear la base de datos como último recurso
    with app.app_context():
        db.create_all()

def get_file_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_video_info(file_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-i', file_path, '-show_streams', '-show_format', '-print_format', 'json'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
            video_stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
            return {
                'file_path': file_path,
                'size_mb': round(os.path.getsize(file_path) / (1024 * 1024), 2),
                'format': info['format']['format_name'],
                'video_codec': video_stream['codec_name'] if video_stream else 'N/A',
                'duration': float(info['format'].get('duration', 0))
            }
        return {'error': f"ffprobe falló: {result.stderr}"}
    except Exception as e:
        return {'error': str(e)}

def generate_subtitles(file_path):
    filename = os.path.basename(file_path)
    vtt_file = os.path.join(os.path.dirname(file_path), f"{os.path.splitext(filename)[0]}.vtt")
    if not os.path.exists(vtt_file):
        app.logger.info(f"Generando subtítulos para {file_path}")
        try:
            model = whisper.load_model("base", device=device)  # Especificamos el dispositivo (CPU o GPU)
            result = model.transcribe(file_path)
            with open(vtt_file, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                for segment in result['segments']:
                    start = segment['start']
                    end = segment['end']
                    text = segment['text'].strip().replace('\n', ' ')
                    f.write(f"{int(start // 3600):02d}:{int((start % 3600) // 60):02d}:{int(start % 60):02d}.000 --> "
                            f"{int(end // 3600):02d}:{int((end % 3600) // 60):02d}:{int(end % 60):02d}.000\n")
                    f.write(f"{text}\n\n")
            with app.app_context():
                converted = ConvertedVideo.query.filter_by(converted_path=file_path).first()
                if converted:
                    converted.has_subtitles = True
                    db.session.commit()
            app.logger.info(f"Subtítulos generados y guardados en {vtt_file}")
        except Exception as e:
            app.logger.error(f"Error al generar subtítulos para {file_path}: {str(e)}")
    else:
        app.logger.info(f"Subtítulos ya existen para {file_path}")

def scan_videos():
    global video_candidates_cache, cache_status
    while True:
        with app.app_context():
            cache_status = "scanning"
            app.logger.info("Iniciando escaneo recursivo de videos...")
            videos = []
            processed_videos = {cv.converted_path: cv for cv in ConvertedVideo.query.all()}
            try:
                for root, dirs, files in os.walk(CURSOS_DIR):
                    if '_archive' in root or '_temp' in root:
                        continue
                    rel_path = os.path.relpath(root, CURSOS_DIR)
                    if rel_path == '.':
                        continue
                    path_parts = rel_path.split(os.sep)
                    curso = path_parts[0]
                    seccion = '/'.join(path_parts[1:]) or ''
                    for filename in files:
                        if filename.endswith('.mp4'):
                            file_path = os.path.join(root, filename)
                            file_hash = get_file_hash(file_path)
                            status = conversion_status.get(file_path, {'status': 'none', 'message': ''})
                            video_info = get_video_info(file_path)
                            if 'error' in video_info:
                                app.logger.warning(f"Error en ffprobe para {file_path}: {video_info['error']}")
                                continue
                            has_subtitles = os.path.exists(os.path.join(root, f"{os.path.splitext(filename)[0]}.vtt"))
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
                                'processed': file_path in processed_videos,
                                'has_subtitles': has_subtitles
                            }
                            videos.append(video_data)
                            if video_data['needs_conversion'] and video_data['status'] not in ['queued', 'processing', 'completed'] and not video_data['processed']:
                                if not conversion_queue.full():
                                    conversion_queue.put(file_path)
                                    conversion_status[file_path] = {'status': 'queued', 'message': 'En cola', 'progress': 0, 'eta': 'Esperando...'}
                            if not has_subtitles and file_path in processed_videos:
                                generate_subtitles(file_path)
            except Exception as e:
                app.logger.error(f"Error durante el escaneo de videos: {str(e)}")
            video_candidates_cache = videos
            cache_status = "ready"
            app.logger.info(f"Caché de videos actualizada: {len(videos)} videos encontrados")
        time.sleep(300)

def convert_video(file_path):
    filename = os.path.basename(file_path)
    temp_output_path = os.path.join(TEMP_DIR, f"{hashlib.md5(filename.encode()).hexdigest()}_h264_temp.mp4")
    archive_path = os.path.join(ARCHIVE_DIR, filename)
    original_hash = get_file_hash(file_path)
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
            generate_subtitles(file_path)
            with app.app_context():
                converted = ConvertedVideo(original_hash=original_hash, original_path=archive_path, converted_path=file_path, has_subtitles=True)
                db.session.add(converted)
                db.session.commit()
            conversion_status[file_path] = {'status': 'completed', 'message': f'Convertido y subtítulos generados: {file_path}', 'progress': 100, 'eta': '0s'}
        else:
            conversion_status[file_path] = {'status': 'failed', 'message': 'FFmpeg falló', 'progress': 0, 'eta': 'N/A'}
            if os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    except Exception as e:
        conversion_status[file_path] = {'status': 'failed', 'message': str(e), 'progress': 0, 'eta': 'N/A'}
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)

def conversion_worker():
    while True:
        file_path = conversion_queue.get()
        convert_video(file_path)
        conversion_queue.task_done()

app.logger.info("Iniciando hilo de conversión de videos...")
threading.Thread(target=conversion_worker, daemon=True).start()
app.logger.info("Iniciando hilo de escaneo de caché de videos...")
threading.Thread(target=scan_videos, daemon=True).start()

def set_queue_size(new_size):
    global conversion_queue
    new_queue = Queue(maxsize=new_size)
    while not conversion_queue.empty() and not new_queue.full():
        new_queue.put(conversion_queue.get())
    conversion_queue = new_queue

@app.context_processor
def inject_globals():
    cursos = {}
    for root, dirs, files in os.walk(CURSOS_DIR):
        if '_archive' in root or '_temp' in root:
            continue
        rel_path = os.path.relpath(root, CURSOS_DIR)
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
    return {
        'cursos': cursos,
        'is_admin': session.get('is_admin', False),
        'search_query': request.form.get('search', '')
    }

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.checkpw(password, user.password.encode('utf-8')):
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

@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    cursos = {}
    search_query = request.form.get('search', '').lower()
    selected_curso = request.args.get('curso')

    for root, dirs, files in os.walk(CURSOS_DIR):
        if '_archive' in root or '_temp' in root:
            continue
        rel_path = os.path.relpath(root, CURSOS_DIR)
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
        if search_query and request.method == 'POST':
            if (search_query in curso.lower() or 
                search_query in seccion.lower() or 
                any(search_query in v.lower() for v in videos) or 
                any(search_query in p.lower() for p in pdfs)):
                cursos[curso][seccion] = {'videos': videos, 'pdfs': pdfs}
        else:
            cursos[curso][seccion] = {'videos': videos, 'pdfs': pdfs}

    if not selected_curso and not cursos:
        selected_curso = None
    elif not selected_curso and cursos:
        selected_curso = list(cursos.keys())[0]

    return render_template('index.html', cursos=cursos, search_query=search_query, 
                           selected_curso=selected_curso, video_candidates=video_candidates_cache)

@app.route('/inspect/<curso>/<path:seccion>/<filename>', methods=['GET'])
def inspect_video(curso, seccion, filename):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    file_path = os.path.join(CURSOS_DIR, curso, seccion, filename)
    app.logger.debug(f"Intentando inspeccionar: {file_path}")
    if os.path.isfile(file_path):
        video_info = get_video_info(file_path)
        return jsonify(video_info)
    app.logger.error(f"Archivo no encontrado para inspección: {file_path}")
    return jsonify({'error': 'Archivo no encontrado'}), 404

@app.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    if not session.get('logged_in') or not session.get('is_admin'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            username = request.form.get('username')
            password = request.form.get('password')
            if not username or not password:
                return render_template('users.html', users=User.query.all(), error="Usuario y contraseña son obligatorios")
            password = password.encode('utf-8')
            is_admin = 'is_admin' in request.form
            if User.query.filter_by(username=username).first():
                return render_template('users.html', users=User.query.all(), error="El usuario ya existe")
            hashed_pw = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
            new_user = User(username=username, password=hashed_pw, is_admin=is_admin)
            db.session.add(new_user)
            db.session.commit()
        elif action == 'delete':
            user_id = request.form.get('user_id')
            if not user_id:
                return render_template('users.html', users=User.query.all(), error="ID de usuario no proporcionado")
            user = User.query.get(user_id)
            if not user:
                return render_template('users.html', users=User.query.all(), error="Usuario no encontrado")
            if user.username == session.get('username'):
                return render_template('users.html', users=User.query.all(), error="No puedes eliminarte a ti mismo")
            db.session.delete(user)
            db.session.commit()
    users = User.query.all()
    return render_template('users.html', users=users, error=None)

@app.route('/admin/video-manager', methods=['GET', 'POST'])
def manage_videos():
    if not session.get('logged_in') or not session.get('is_admin'):
        return redirect(url_for('index'))
    archived_videos = ConvertedVideo.query.all()
    videos = video_candidates_cache
    converting_videos = [
        {'file_path': path, **status} 
        for path, status in conversion_status.items() 
        if status['status'] in ['queued', 'processing']
    ]
    error = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'convert':
            file_paths = request.form.getlist('file_paths')
            for file_path in file_paths:
                if conversion_queue.full():
                    error = "Cola llena, espera a que se procesen algunos videos."
                    break
                if file_path not in conversion_status or conversion_status[file_path]['status'] == 'failed':
                    conversion_queue.put(file_path)
                    conversion_status[file_path] = {'status': 'queued', 'message': 'En cola', 'progress': 0, 'eta': 'Esperando...'}
            return redirect(url_for('manage_videos'))
        elif action == 'set_queue_size':
            new_size = int(request.form.get('queue_size', 5))
            set_queue_size(new_size)
        elif action == 'delete_archived':
            archived_id = request.form.get('archived_id')
            archived = ConvertedVideo.query.get(archived_id)
            if archived and os.path.isfile(archived.original_path):
                os.remove(archived.original_path)
                db.session.delete(archived)
                db.session.commit()
    return render_template('video_manager.html', videos=videos, archived_videos=archived_videos, 
                           queue_size=conversion_queue.qsize(), max_queue_size=conversion_queue.maxsize, 
                           error=error, cache_status=cache_status, converting_videos=converting_videos)

@app.route('/cursos/<curso>/<filename>', methods=['GET'])
def serve_file_no_section(curso, filename):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    file_path = os.path.join(CURSOS_DIR, curso, filename)
    app.logger.debug(f"Intentando servir archivo sin sección: {file_path}")
    if os.path.isfile(file_path):
        if filename.endswith('.mp4'):
            mimetype = 'video/mp4'
        elif filename.endswith('.pdf'):
            mimetype = 'application/pdf'
        elif filename.endswith(('.vtt', '.srt')):
            mimetype = 'text/vtt' if filename.endswith('.vtt') else 'application/x-subrip'
        else:
            mimetype = 'application/octet-stream'
        return send_from_directory(os.path.dirname(file_path), filename, mimetype=mimetype)
    app.logger.error(f"Archivo no encontrado para reproducción: {file_path}")
    return "Archivo no encontrado", 404

@app.route('/cursos/<curso>/<path:seccion>/<filename>', methods=['GET'])
def serve_file_with_section(curso, seccion, filename):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    file_path = os.path.join(CURSOS_DIR, curso, seccion, filename)
    app.logger.debug(f"Intentando servir archivo con sección: {file_path}")
    if os.path.isfile(file_path):
        if filename.endswith('.mp4'):
            mimetype = 'video/mp4'
        elif filename.endswith('.pdf'):
            mimetype = 'application/pdf'
        elif filename.endswith(('.vtt', '.srt')):
            mimetype = 'text/vtt' if filename.endswith('.vtt') else 'application/x-subrip'
        else:
            mimetype = 'application/octet-stream'
        return send_from_directory(os.path.dirname(file_path), filename, mimetype=mimetype)
    app.logger.error(f"Archivo no encontrado para reproducción: {file_path}")
    return "Archivo no encontrado", 404

@app.route('/video_progress', methods=['POST', 'GET'])
def video_progress():
    if not session.get('logged_in'):
        return jsonify({'error': 'No autenticado'}), 401
    user = User.query.filter_by(username=session['username']).first()
    if request.method == 'POST':
        data = request.get_json()
        curso = data.get('curso')
        seccion = data.get('seccion', None)
        filename = data.get('filename')
        progress = data.get('progress', 0.0)
        completed = data.get('completed', False)
        
        progress_entry = VideoProgress.query.filter_by(user_id=user.id, curso=curso, seccion=seccion, filename=filename).first()
        if progress_entry:
            progress_entry.progress = progress
            progress_entry.completed = completed
        else:
            progress_entry = VideoProgress(user_id=user.id, curso=curso, seccion=seccion, filename=filename, progress=progress, completed=completed)
            db.session.add(progress_entry)
        db.session.commit()
        return jsonify({'message': 'Progreso guardado'}), 200
    
    if request.method == 'GET':
        curso = request.args.get('curso')
        seccion = request.args.get('seccion', None)
        filename = request.args.get('filename')
        progress_entry = VideoProgress.query.filter_by(user_id=user.id, curso=curso, seccion=seccion, filename=filename).first()
        if progress_entry:
            return jsonify({'progress': progress_entry.progress, 'completed': progress_entry.completed})
        return jsonify({'progress': 0.0, 'completed': False}), 200

@app.route('/transcribe/<curso>/<path:seccion>/<filename>', methods=['GET'])
@app.route('/transcribe/<curso>/<filename>', methods=['GET'])
def transcribe_video(curso, seccion=None, filename=None):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    file_path = os.path.join(CURSOS_DIR, curso, seccion, filename) if seccion else os.path.join(CURSOS_DIR, curso, filename)
    if not os.path.isfile(file_path) or not filename.endswith('.mp4'):
        return "Video no encontrado", 404
    
    try:
        model = whisper.load_model("base", device=device)  # Especificamos el dispositivo (CPU o GPU)
        result = model.transcribe(file_path)
        transcript_path = os.path.join(TEMP_DIR, f"{filename.replace('.mp4', '')}_transcript.txt")
        with open(transcript_path, 'w') as f:
            f.write(result['text'])
        return send_file(transcript_path, as_attachment=True, download_name=f"{filename.replace('.mp4', '')}_transcript.txt")
    except Exception as e:
        app.logger.error(f"Error al transcribir video {file_path}: {str(e)}")
        return "Error al transcribir el video", 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    referrer = request.referrer if request.referrer else "No referrer provided"
    app.logger.info(f"Solicitud recibida en /api/stats desde: {referrer}")
    return jsonify({"error": "Endpoint no implementado aún"}), 200

@app.route('/api/version', methods=['GET'])
def api_version():
    referrer = request.referrer if request.referrer else "No referrer provided"
    app.logger.info(f"Solicitud recibida en /api/version desde: {referrer}")
    return jsonify({"error": "Endpoint no implementado aún"}), 200

if __name__ == '__main__':
    with app.app_context():
        for root, dirs, files in os.walk(CURSOS_DIR):
            if '_archive' in root or '_temp' in root:
                continue
            for filename in files:
                if filename.endswith('.mp4'):
                    file_path = os.path.join(root, filename)
                    converted = ConvertedVideo.query.filter_by(converted_path=file_path).first()
                    if converted and not converted.has_subtitles:
                        try:
                            generate_subtitles(file_path)
                        except Exception as e:
                            app.logger.error(f"Error al procesar subtítulos para {file_path}: {str(e)}")
    app.run(host='0.0.0.0', port=5000, debug=True)