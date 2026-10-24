from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.models.monitored_directory import MonitoredDirectory
from app.services.baseline_service import BaselineService
from app.services.audit_service import AuditService

bp = Blueprint('baselines', __name__, url_prefix='/baselines')

baseline_service = BaselineService()
audit_service = AuditService()

@bp.route('/')
@login_required
def index():
    """Baseline management page"""
    directories = MonitoredDirectory.query.all()

    # Get baseline info for each directory
    baseline_infos = {}
    for directory in directories:
        baseline_infos[directory.id] = baseline_service.get_baseline_info(directory.id)

    return render_template('baselines.html', directories=directories, baseline_infos=baseline_infos)

@bp.route('/<int:directory_id>/create', methods=['POST'])
@login_required
def create(directory_id):
    """Create a new baseline"""
    if not current_user.is_administrator():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    directory = MonitoredDirectory.query.get_or_404(directory_id)

    # Check if baseline already exists
    baseline_info = baseline_service.get_baseline_info(directory_id)

    if baseline_info and baseline_info['exists']:
        return jsonify({
            'success': False,
            'message': 'Baseline already exists. Use replace instead.',
            'requires_confirmation': True
        }), 400

    # Create baseline
    result = baseline_service.create_baseline(directory_id, current_user.username)

    return jsonify(result)

@bp.route('/<int:directory_id>/replace', methods=['POST'])
@login_required
def replace(directory_id):
    """Replace existing baseline"""
    if not current_user.is_administrator():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    reason = request.json.get('reason', 'Manual replacement') if request.is_json else 'Manual replacement'
    confirmed = request.json.get('confirmed', False) if request.is_json else False

    if not confirmed:
        return jsonify({
            'success': False,
            'message': 'Baseline replacement requires explicit confirmation',
            'requires_confirmation': True
        }), 400

    # Replace baseline
    result = baseline_service.replace_baseline(directory_id, current_user.username, reason)

    return jsonify(result)
