from datetime import datetime
from app.extensions import db

class MonitoredDirectory(db.Model):
    """Model for directories configured for monitoring"""
    __tablename__ = 'monitored_directories'

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(512), nullable=False, unique=True)
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_scan = db.Column(db.DateTime)
    last_scan_status = db.Column(db.String(50))  # 'success', 'failed', 'incomplete'
    last_scan_error = db.Column(db.Text)
    file_count = db.Column(db.Integer, default=0)

    # Relationships
    baseline_entries = db.relationship('BaselineEntry', backref='directory', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<MonitoredDirectory {self.path}>'
