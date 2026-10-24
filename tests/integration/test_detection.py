import pytest
import tempfile
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models.monitored_directory import MonitoredDirectory
from app.models.baseline import BaselineEntry
from app.services.baseline_service import BaselineService

@pytest.fixture
def app():
    """Create test Flask application"""
    app = create_app('default')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

class TestChangeDetection:
    """Integration tests for change detection"""

    def test_detect_added_file(self, app):
        """Test detection of newly added file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create initial file and baseline
            initial_file = Path(temp_dir) / 'initial.txt'
            initial_file.write_text('Initial content')

            # Add directory and create baseline
            directory = MonitoredDirectory(path=temp_dir, is_enabled=True)
            db.session.add(directory)
            db.session.commit()

            baseline_service = BaselineService()
            result = baseline_service.create_baseline(directory.id, 'test')

            assert result['success'] is True
            assert result['file_count'] == 1

            # Add new file
            new_file = Path(temp_dir) / 'added.txt'
            new_file.write_text('New content')

            # Detect changes
            from app.services.detection_engine import DetectionEngine
            detection_engine = DetectionEngine()
            changes = detection_engine.detect_changes(directory.id)

            assert changes['scan_complete'] is True
            assert len(changes['added']) == 1
            assert changes['added'][0]['path'] == 'added.txt'
            assert len(changes['modified']) == 0
            assert len(changes['deleted']) == 0

    def test_detect_modified_file(self, app):
        """Test detection of modified file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create initial file
            test_file = Path(temp_dir) / 'test.txt'
            test_file.write_text('Original content')

            # Create baseline
            directory = MonitoredDirectory(path=temp_dir, is_enabled=True)
            db.session.add(directory)
            db.session.commit()

            baseline_service = BaselineService()
            baseline_service.create_baseline(directory.id, 'test')

            # Modify file
            test_file.write_text('Modified content')

            # Detect changes
            from app.services.detection_engine import DetectionEngine
            detection_engine = DetectionEngine()
            changes = detection_engine.detect_changes(directory.id)

            assert changes['scan_complete'] is True
            assert len(changes['modified']) == 1
            assert changes['modified'][0]['path'] == 'test.txt'
            assert changes['modified'][0]['previous_hash'] is not None
            assert changes['modified'][0]['current_hash'] is not None
            assert changes['modified'][0]['previous_hash'] != changes['modified'][0]['current_hash']

    def test_detect_deleted_file(self, app):
        """Test detection of deleted file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create initial file
            test_file = Path(temp_dir) / 'to_delete.txt'
            test_file.write_text('Will be deleted')

            # Create baseline
            directory = MonitoredDirectory(path=temp_dir, is_enabled=True)
            db.session.add(directory)
            db.session.commit()

            baseline_service = BaselineService()
            baseline_service.create_baseline(directory.id, 'test')

            # Delete file
            test_file.unlink()

            # Detect changes
            from app.services.detection_engine import DetectionEngine
            detection_engine = DetectionEngine()
            changes = detection_engine.detect_changes(directory.id)

            assert changes['scan_complete'] is True
            assert len(changes['deleted']) == 1
            assert changes['deleted'][0]['path'] == 'to_delete.txt'
            assert changes['deleted'][0]['previous_hash'] is not None

    def test_detect_unchanged_file(self, app):
        """Test that unchanged files are counted correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create file
            test_file = Path(temp_dir) / 'unchanged.txt'
            test_file.write_text('Stable content')

            # Create baseline
            directory = MonitoredDirectory(path=temp_dir, is_enabled=True)
            db.session.add(directory)
            db.session.commit()

            baseline_service = BaselineService()
            baseline_service.create_baseline(directory.id, 'test')

            # Scan again without changes
            from app.services.detection_engine import DetectionEngine
            detection_engine = DetectionEngine()
            changes = detection_engine.detect_changes(directory.id)

            assert changes['scan_complete'] is True
            assert len(changes['added']) == 0
            assert len(changes['modified']) == 0
            assert len(changes['deleted']) == 0
            assert changes['unchanged'] == 1
