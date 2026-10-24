from datetime import datetime
from app.extensions import db

class Exclusion(db.Model):
    """Model for file/directory exclusions"""
    __tablename__ = 'exclusions'

    id = db.Column(db.Integer, primary_key=True)
    pattern = db.Column(db.String(256), nullable=False)
    pattern_type = db.Column(db.String(20), nullable=False)  # 'file', 'directory', 'glob'
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.String(64))
    description = db.Column(db.String(256))

    def __repr__(self):
        return f'<Exclusion {self.pattern_type}: {self.pattern}>'
