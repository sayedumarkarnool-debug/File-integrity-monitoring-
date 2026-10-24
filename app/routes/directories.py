from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import os

from app.models.monitored_directory import MonitoredDirectory
from app.extensions import db
from app.services.baseline_service import BaselineService
from app.services.detection_engine import DetectionEngine
from app.services.audit_service import AuditService

bp = Blueprint('directories', __name__, url_prefix='/directories')

baseline_service = BaselineService()
detection_engine = DetectionEngine()
audit_service = AuditService()

@bp.route('/')
@login_required
def index():
    """Monitored directories page"""
    directories = MonitoredDirectory.query.order_by(MonitoredDirectory.created_at.desc()).all()
    return render_template('directories.html', directories=directories)

@bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new monitored directory"""
    if not current_user.is_administrator():
        flash('Only administrators can add monitored directories', 'error')
        return redirect(url_for('directories.index'))

    path = request.form.get('path', '').strip()

    if not path:
        flash('Please provide a directory path', 'error')
        return redirect(url_for('directories.index'))

    # Validate path
    path = os.path.abspath(path)

    if not os.path.exists(path):
        flash('Directory does not exist', 'error')
        return redirect(url_for('directories.index'))

    if not os.path.isdir(path):
        flash('Path is not a directory', 'error')
        return redirect(url_for('directories.index'))

    # Check if already monitored
    existing = MonitoredDirectory.query.filter_by(path=path).first()
    if existing:
        flash('Directory is already being monitored', 'warning')
        return redirect(url_for('directories.index'))

    # Add directory
    directory = MonitoredDirectory(path=path, is_enabled=True)
    db.session.add(directory)
    db.session.commit()

    # Log action
    audit_service.log_action(
        actor=current_user.username,
        action='directory_added',
        resource_type='directory',
        resource_id=str(directory.id),
        outcome='success',
        details=f"Added directory: {path}"
    )

    flash(f'Directory added: {path}', 'success')
    return redirect(url_for('directories.index'))

@bp.route('/<int:directory_id>/toggle', methods=['POST'])
@login_required
def toggle(directory_id):
    """Enable/disable monitoring for a directory"""
    if not current_user.is_administrator():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    directory = MonitoredDirectory.query.get_or_404(directory_id)
    directory.is_enabled = not directory.is_enabled
    db.session.commit()

    # Log action
    audit_service.log_action(
        actor=current_user.username,
        action='directory_toggled',
        resource_type='directory',
        resource_id=str(directory_id),
        outcome='success',
        details=f"Directory {'enabled' if directory.is_enabled else 'disabled'}: {directory.path}"
    )

    return jsonify({
        'success': True,
        'is_enabled': directory.is_enabled
    })

@bp.route('/<int:directory_id>/scan', methods=['POST'])
@login_required
def scan(directory_id):
    """Run a manual scan on a directory"""
    directory = MonitoredDirectory.query.get_or_404(directory_id)

    if not directory.is_enabled:
        return jsonify({'success': False, 'message': 'Directory monitoring is disabled'}), 400

    # Check if baseline exists
    baseline_info = baseline_service.get_baseline_info(directory_id)

    if not baseline_info or not baseline_info['exists']:
        return jsonify({
            'success': False,
            'message': 'No baseline exists. Create a baseline first.'
        }), 400

    # Run scan and detection
    result = detection_engine.scan_and_detect(directory_id, current_user.username)

    return jsonify({
        'success': result['scan_complete'],
        'added': len(result['added']),
        'modified': len(result['modified']),
        'deleted': len(result['deleted']),
        'unchanged': result['unchanged'],
        'events_recorded': result.get('events_recorded', 0),
        'errors': result['errors']
    })
