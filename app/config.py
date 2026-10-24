import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)

def _get_database_uri():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url or db_url == 'sqlite:///instance/fileguard.db':
        return 'sqlite:///' + os.path.join(INSTANCE_DIR, 'fileguard.db').replace('\\', '/')
    if db_url.startswith('sqlite:///') and not os.path.isabs(db_url[10:]):
        return 'sqlite:///' + os.path.join(BASE_DIR, db_url[10:]).replace('\\', '/')
    return db_url

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database
    SQLALCHEMY_DATABASE_URI = _get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    WTF_CSRF_ENABLED = os.environ.get('WTF_CSRF_ENABLED', 'True') == 'True'

    # Monitoring
    SCAN_INTERVAL_SECONDS = int(os.environ.get('SCAN_INTERVAL_SECONDS', '60'))
    MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', '100'))
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    # Demo Mode
    DEMO_MODE_ENABLED = os.environ.get('DEMO_MODE_ENABLED', 'False') == 'True'

    # Application
    APP_NAME = 'FileGuard FIM'
    APP_VERSION = '1.0.0'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
