import os
import tempfile
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User

@pytest.fixture
def app():
    """Create and configure a test Flask application with a clean temporary SQLite database"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)

    test_app = create_app('default')
    test_app.config['TESTING'] = True
    test_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path.replace(os.sep, "/")}'
    test_app.config['WTF_CSRF_ENABLED'] = False

    with test_app.app_context():
        db.create_all()

        # Create test users if not existing
        if not User.query.filter_by(username='testadmin').first():
            admin = User(username='testadmin', email='admin@test.com', role='administrator')
            admin.set_password('TestPass123!')
            db.session.add(admin)

        if not User.query.filter_by(username='testreadonly').first():
            readonly = User(username='testreadonly', email='readonly@test.com', role='readonly')
            readonly.set_password('ReadOnly123!')
            db.session.add(readonly)

        db.session.commit()

        yield test_app

        db.session.remove()
        db.drop_all()

    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except OSError:
        pass

@pytest.fixture
def client(app):
    """Create test client for HTTP requests"""
    return app.test_client()
