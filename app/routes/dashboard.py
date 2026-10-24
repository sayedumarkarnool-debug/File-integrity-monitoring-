from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.services.report_service import ReportService

bp = Blueprint('dashboard', __name__, url_prefix='/')

@bp.route('/')
@bp.route('/dashboard')
@bp.route('/dashboard/')
@login_required
def index():
    """Dashboard overview page"""
    report_service = ReportService()
    stats = report_service.get_dashboard_stats()

    return render_template('dashboard.html', stats=stats)
