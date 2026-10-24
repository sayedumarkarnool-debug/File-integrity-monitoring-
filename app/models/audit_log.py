from datetime import datetime
from app.extensions import db

class AuditLog(db.Model):
    """Model for audit logs"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    actor = db.Column(db.String(64))  # Username or 'system'
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))  # 'baseline', 'directory', 'user', 'exclusion', etc.
    resource_id = db.Column(db.String(256))
    file_path = db.Column(db.String(512))
    event_type = db.Column(db.String(20))
    previous_hash = db.Column(db.String(64))
    current_hash = db.Column(db.String(64))
    outcome = db.Column(db.String(20))  # 'success', 'failed'
    error_details = db.Column(db.Text)
    details = db.Column(db.Text)

    def __repr__(self):
        return f'<AuditLog {self.action} by {self.actor}>'
