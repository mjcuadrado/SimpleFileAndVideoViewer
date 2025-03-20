# Modelo para videos convertidos
from app.__init__ import db

class ConvertedVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_hash = db.Column(db.String(64), nullable=False)
    original_path = db.Column(db.String(255), nullable=False)
    converted_path = db.Column(db.String(255), nullable=False)