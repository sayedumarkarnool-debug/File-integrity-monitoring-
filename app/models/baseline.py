from datetime import datetime
from app.extensions import db

class BaselineEntry(db.Model):
    """Model for baseline file entries"""
    __tablename__ = 'baseline_entries'

    id = db.Column(db.Integer, primary_key=True)
    directory_id = db.Column(db.Integer, db.ForeignKey('monitored_directories.id'), nullable=False)
    relative_path = db.Column(db.String(512), nullable=False)
    sha256_hash = db.Column(db.String(64), nullable=False)
    file_size = db.Column(db.BigInteger)
    modification_time = db.Column(db.DateTime)
    baseline_version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Composite index for fast lookups
    __table_args__ = (
        db.Index('idx_directory_path', 'directory_id', 'relative_path'),
    )

    def __repr__(self):
        return f'<BaselineEntry {self.relative_path}>'
