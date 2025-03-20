# Rutas de gestión de videos
from flask import render_template, request, redirect, url_for, session
import os
from app.__init__ import db
from app.models.video_model import ConvertedVideo  # Actualizado
from app.services.video_service import conversion_status, video_candidates_cache, cache_status, set_queue_size, conversion_queue

def register_video_routes(app):
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