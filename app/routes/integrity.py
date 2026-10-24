from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from datetime import datetime, timedelta

from app.models.integrity_event import IntegrityEvent
from app.extensions import db

bp = Blueprint('integrity', __name__, url_prefix='/integrity')

@bp.route('/')
@login_required
def index():
    """File integrity events page"""
    # Get filter parameters
    event_type = request.args.get('event_type', '')
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 25

    # Build query
    query = IntegrityEvent.query

    if event_type:
        query = query.filter_by(event_type=event_type)

    if search_query:
        query = query.filter(IntegrityEvent.file_path.like(f'%{search_query}%'))

    # Order by most recent
    query = query.order_by(IntegrityEvent.detected_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    events = pagination.items

    return render_template(
        'file_integrity.html',
        events=events,
        pagination=pagination,
        event_type=event_type,
        search_query=search_query
    )

@bp.route('/event/<int:event_id>')
@login_required
def event_detail(event_id):
    """Event detail view"""
    event = IntegrityEvent.query.get_or_404(event_id)
    return jsonify({
        'id': event.id,
        'file_path': event.file_path,
        'event_type': event.event_type,
        'detected_at': event.detected_at.isoformat(),
        'previous_hash': event.previous_hash,
        'current_hash': event.current_hash,
        'file_size': event.file_size,
        'status': event.status,
        'directory': event.directory.path if event.directory else None
    })
