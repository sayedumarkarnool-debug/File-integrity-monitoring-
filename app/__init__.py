import os
from flask import Flask
from app.config import config
from app.extensions import init_extensions, db

def create_app(config_name='default'):
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Initialize extensions
    init_extensions(app)

    # Create instance folder
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)

    # Register blueprints
    from app.routes import auth, dashboard, integrity, directories, baselines, audit, exclusions, reports, settings

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(integrity.bp)
    app.register_blueprint(directories.bp)
    app.register_blueprint(baselines.bp)
    app.register_blueprint(audit.bp)
    app.register_blueprint(exclusions.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(settings.bp)

    # Create database tables
    with app.app_context():
        db.create_all()
        # Initialize default admin user if none exists (skip in test mode)
        if not app.config.get('TESTING', False):
            from app.models.user import User
            try:
                if not User.query.filter_by(username='admin').first():
                    admin = User(
                        username='admin',
                        email='admin@fileguard.local',
                        role='administrator'
                    )
                    admin.set_password('admin123')  # Default password - must be changed
                    db.session.add(admin)
                    db.session.commit()
            except Exception:
                db.session.rollback()

    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'app': app.config['APP_NAME'], 'version': app.config['APP_VERSION']}, 200

    return app
