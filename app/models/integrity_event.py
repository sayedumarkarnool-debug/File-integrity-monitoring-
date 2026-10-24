from datetime import datetime
from app.extensions import db

class IntegrityEvent(db.Model):
    """Model for file integrity events"""
    __tablename__ = 'integrity_events'

    id = db.Column(db.Integer, primary_key=True)
    directory_id = db.Column(db.Integer, db.ForeignKey('monitored_directories.id'), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    event_type = db.Column(db.String(20), nullable=False)  # 'added', 'modified', 'deleted'
    detected_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    previous_hash = db.Column(db.String(64))
    current_hash = db.Column(db.String(64))
    file_size = db.Column(db.BigInteger)
    status = db.Column(db.String(20), default='detected')  # 'detected', 'reviewed', 'accepted'

    # Relationship
    directory = db.relationship('MonitoredDirectory', backref='events')

    def __repr__(self):
        return f'<IntegrityEvent {self.event_type} {self.file_path}>'
