from flask import Blueprint, render_template, current_app
from flask_login import login_required

from app.models.monitored_directory import MonitoredDirectory
from app.extensions import db

bp = Blueprint('settings', __name__, url_prefix='/settings')

@bp.route('/')
@login_required
def index():
    """Settings page"""
    config = {
        'app_name': current_app.config['APP_NAME'],
        'app_version': current_app.config['APP_VERSION'],
        'scan_interval': current_app.config['SCAN_INTERVAL_SECONDS'],
        'max_file_size_mb': current_app.config['MAX_FILE_SIZE_MB'],
        'demo_mode': current_app.config['DEMO_MODE_ENABLED'],
    }

    # Database status
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'Connected'
    except:
        db_status = 'Error'

    # Count directories
    monitored_count = MonitoredDirectory.query.filter_by(is_enabled=True).count()

    return render_template(
        'settings.html',
        config=config,
        db_status=db_status,
        monitored_count=monitored_count
    )
