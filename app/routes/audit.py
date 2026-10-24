from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import or_

from app.models.audit_log import AuditLog
from app.extensions import db

bp = Blueprint('audit', __name__, url_prefix='/audit')

@bp.route('/')
@login_required
def index():
    """Audit logs page"""
    # Get filter parameters
    action = request.args.get('action', '')
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Build query
    query = AuditLog.query

    if action:
        query = query.filter_by(action=action)

    if search_query:
        query = query.filter(
            or_(
                AuditLog.actor.like(f'%{search_query}%'),
                AuditLog.details.like(f'%{search_query}%')
            )
        )

    # Order by most recent
    query = query.order_by(AuditLog.timestamp.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items

    return render_template(
        'audit_logs.html',
        logs=logs,
        pagination=pagination,
        action=action,
        search_query=search_query
    )
