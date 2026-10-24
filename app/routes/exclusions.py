from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.models.exclusion import Exclusion
from app.extensions import db
from app.services.audit_service import AuditService

bp = Blueprint('exclusions', __name__, url_prefix='/exclusions')
audit_service = AuditService()

@bp.route('/')
@login_required
def index():
    """Exclusions page"""
    exclusions = Exclusion.query.order_by(Exclusion.created_at.desc()).all()
    return render_template('exclusions.html', exclusions=exclusions)

@bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new exclusion pattern"""
    if not current_user.is_administrator():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    pattern = request.form.get('pattern', '').strip()
    pattern_type = request.form.get('pattern_type', 'glob')
    description = request.form.get('description', '').strip()

    if not pattern:
        flash('Please provide a pattern', 'error')
        return redirect(url_for('exclusions.index'))

    # Create exclusion
    exclusion = Exclusion(
        pattern=pattern,
        pattern_type=pattern_type,
        description=description,
        created_by=current_user.username,
        is_enabled=True
    )
    db.session.add(exclusion)
    db.session.commit()

    # Log action
    audit_service.log_action(
        actor=current_user.username,
        action='exclusion_added',
        resource_type='exclusion',
        resource_id=str(exclusion.id),
        outcome='success',
        details=f"Added exclusion: {pattern} ({pattern_type})"
    )

    flash('Exclusion pattern added', 'success')
    return redirect(url_for('exclusions.index'))

@bp.route('/<int:exclusion_id>/toggle', methods=['POST'])
@login_required
def toggle(exclusion_id):
    """Enable/disable an exclusion"""
    if not current_user.is_administrator():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    exclusion = Exclusion.query.get_or_404(exclusion_id)
    exclusion.is_enabled = not exclusion.is_enabled
    db.session.commit()

    # Log action
    audit_service.log_action(
        actor=current_user.username,
        action='exclusion_toggled',
        resource_type='exclusion',
        resource_id=str(exclusion_id),
        outcome='success',
        details=f"Exclusion {'enabled' if exclusion.is_enabled else 'disabled'}: {exclusion.pattern}"
    )

    return jsonify({'success': True, 'is_enabled': exclusion.is_enabled})

@bp.route('/<int:exclusion_id>/delete', methods=['POST'])
@login_required
def delete(exclusion_id):
    """Delete an exclusion"""
    if not current_user.is_administrator():
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    exclusion = Exclusion.query.get_or_404(exclusion_id)
    pattern = exclusion.pattern

    db.session.delete(exclusion)
    db.session.commit()

    # Log action
    audit_service.log_action(
        actor=current_user.username,
        action='exclusion_deleted',
        resource_type='exclusion',
        resource_id=str(exclusion_id),
        outcome='success',
        details=f"Deleted exclusion: {pattern}"
    )

    return jsonify({'success': True})
