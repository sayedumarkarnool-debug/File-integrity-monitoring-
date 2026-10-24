from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime

from app.extensions import db, login_manager
from app.models.user import User
from app.services.audit_service import AuditService

bp = Blueprint('auth', __name__, url_prefix='/auth')
audit_service = AuditService()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()

            # Log successful login
            audit_service.log_action(
                actor=username,
                action='user_login',
                resource_type='user',
                outcome='success'
            )

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid username or password', 'error')

            # Log failed login
            audit_service.log_action(
                actor=username or 'unknown',
                action='user_login_failed',
                resource_type='user',
                outcome='failed'
            )

    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    username = current_user.username

    # Log logout
    audit_service.log_action(
        actor=username,
        action='user_logout',
        resource_type='user',
        outcome='success'
    )

    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))
