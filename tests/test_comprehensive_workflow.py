import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

from app.models.monitored_directory import MonitoredDirectory
from app.models.baseline import BaselineEntry
from app.models.exclusion import Exclusion
from app.models.audit_log import AuditLog
from app.models.integrity_event import IntegrityEvent
from app.services.hasher import FileHasher
from app.services.scanner import DirectoryScanner
from app.services.baseline_service import BaselineService
from app.services.detection_engine import DetectionEngine
from app.services.report_service import ReportService
from app.services.scheduler import MonitoringScheduler
from app.extensions import db


class TestBaselineGuardsAndIntegrity:
    """Tests for baseline replacement confirmation, preservation on failure, and false deletion prevention"""

    def test_baseline_creation_and_versioning(self, app):
        """Test that initial baseline creates version 1 entries"""
        with app.app_context():
            with tempfile.TemporaryDirectory() as temp_dir:
                f1 = Path(temp_dir) / 'file1.txt'
                f1.write_text('content 1')

                mon_dir = MonitoredDirectory(path=temp_dir, is_enabled=True)
                db.session.add(mon_dir)
                db.session.commit()

                baseline_service = BaselineService()
                result = baseline_service.create_baseline(mon_dir.id, 'admin')

                assert result['success'] is True
                assert result['file_count'] == 1

                info = baseline_service.get_baseline_info(mon_dir.id)
                assert info['exists'] is True
                assert info['version'] == 1
                assert info['file_count'] == 1

    def test_baseline_preserved_when_replacement_scan_fails(self, app, monkeypatch):
        """Test that if creating a new baseline fails, the existing baseline is preserved"""
        with app.app_context():
            with tempfile.TemporaryDirectory() as temp_dir:
                f1 = Path(temp_dir) / 'file1.txt'
                f1.write_text('content 1')

                mon_dir = MonitoredDirectory(path=temp_dir, is_enabled=True)
                db.session.add(mon_dir)
                db.session.commit()

                baseline_service = BaselineService()
                res1 = baseline_service.create_baseline(mon_dir.id, 'admin')
                assert res1['success'] is True

                # Verify version 1 exists
                v1_entries = BaselineEntry.query.filter_by(directory_id=mon_dir.id).all()
                assert len(v1_entries) == 1
                v1_hash = v1_entries[0].sha256_hash

                # Now simulate a scanner error on replacement
                def fake_scan(*args, **kwargs):
                    return {
                        'files': {},
                        'errors': ['Simulated disk read error'],
                        'scan_complete': False,
                        'total_files': 0,
                        'failed_files': 1
                    }

                monkeypatch.setattr(baseline_service.scanner, 'scan_directory', fake_scan)

                res_fail = baseline_service.replace_baseline(mon_dir.id, 'admin', 'Testing failure')
                assert res_fail['success'] is False

                # Ensure previous baseline entries still exist intact!
                remaining_entries = BaselineEntry.query.filter_by(directory_id=mon_dir.id).all()
                assert len(remaining_entries) == 1
                assert remaining_entries[0].sha256_hash == v1_hash

    def test_incomplete_scan_prevents_false_deletions(self, app, monkeypatch):
        """Verify that when a scan is incomplete, files are NOT falsely marked as deleted"""
        with app.app_context():
            with tempfile.TemporaryDirectory() as temp_dir:
                f1 = Path(temp_dir) / 'file1.txt'
                f1.write_text('content 1')

                mon_dir = MonitoredDirectory(path=temp_dir, is_enabled=True)
                db.session.add(mon_dir)
                db.session.commit()

                baseline_service = BaselineService()
                baseline_service.create_baseline(mon_dir.id, 'admin')

                engine = DetectionEngine()

                # Simulate incomplete scan where file1 couldn't be scanned
                def incomplete_scan(*args, **kwargs):
                    return {
                        'files': {},
                        'errors': ['Permission denied reading directory'],
                        'scan_complete': False,
                        'total_files': 0,
                        'failed_files': 1
                    }

                monkeypatch.setattr(engine.scanner, 'scan_directory', incomplete_scan)

                changes = engine.detect_changes(mon_dir.id)
                assert changes['scan_complete'] is False
                # Crucial requirement: No deletions reported!
                assert len(changes['deleted']) == 0
                assert any('avoid false deletions' in err for err in changes['errors'])

    def test_file_read_error_does_not_report_deletion(self, app, monkeypatch):
        """Verify that a single file with read error is not reported as deleted"""
        with app.app_context():
            with tempfile.TemporaryDirectory() as temp_dir:
                f1 = Path(temp_dir) / 'file1.txt'
                f1.write_text('content 1')

                mon_dir = MonitoredDirectory(path=temp_dir, is_enabled=True)
                db.session.add(mon_dir)
                db.session.commit()

                baseline_service = BaselineService()
                baseline_service.create_baseline(mon_dir.id, 'admin')

                engine = DetectionEngine()

                # Simulate scan where file1 has an error
                def scan_with_file_error(*args, **kwargs):
                    return {
                        'files': {
                            'file1.txt': {
                                'hash': None,
                                'size': 9,
                                'mtime': None,
                                'error': 'Permission denied'
                            }
                        },
                        'errors': ['file1.txt: Permission denied'],
                        'scan_complete': True,
                        'total_files': 1,
                        'failed_files': 1
                    }

                monkeypatch.setattr(engine.scanner, 'scan_directory', scan_with_file_error)

                changes = engine.detect_changes(mon_dir.id)
                # Should NOT mark file1.txt as deleted
                assert len(changes['deleted']) == 0


class TestExclusionsAndReports:
    """Tests for exclusion patterns, CSV/JSON report exports, and injection prevention"""

    def test_exclusion_filters_glob_and_directory(self, app):
        """Test that excluded files and directories are omitted from scans"""
        with app.app_context():
            with tempfile.TemporaryDirectory() as temp_dir:
                # Normal file
                (Path(temp_dir) / 'app.py').write_text('print("hello")')
                # Excluded log file
                (Path(temp_dir) / 'debug.log').write_text('error log')
                # Excluded dir
                log_dir = Path(temp_dir) / 'temp_cache'
                log_dir.mkdir()
                (log_dir / 'cache.bin').write_text('cached data')

                # Add exclusions to DB
                ex1 = Exclusion(pattern='*.log', pattern_type='glob', created_by='admin', is_enabled=True)
                ex2 = Exclusion(pattern='temp_cache', pattern_type='directory', created_by='admin', is_enabled=True)
                db.session.add_all([ex1, ex2])
                db.session.commit()

                scanner = DirectoryScanner()
                result = scanner.scan_directory(temp_dir)

                assert result['scan_complete'] is True
                assert 'app.py' in result['files']
                assert 'debug.log' not in result['files']
                assert not any('temp_cache' in p for p in result['files'])

    def test_report_service_csv_formula_injection(self):
        """Test CSV export sanitizes formulas starting with dangerous characters"""
        for dangerous in ['=cmd|', '+123', '-SUM', '@SUM', '\tcalc']:
            sanitized = ReportService._escape_csv_value(dangerous)
            assert sanitized.startswith("'"), f"Failed for {dangerous}"

        safe = ReportService._escape_csv_value('normal_file.txt')
        assert safe == 'normal_file.txt'

    def test_report_generation_csv_and_json(self, app):
        """Test generating CSV and JSON reports"""
        with app.app_context():
            with tempfile.TemporaryDirectory() as temp_dir:
                mon_dir = MonitoredDirectory(path=temp_dir, is_enabled=True)
                db.session.add(mon_dir)
                db.session.commit()

                event = IntegrityEvent(
                    directory_id=mon_dir.id,
                    file_path='test.txt',
                    event_type='modified',
                    previous_hash='a' * 64,
                    current_hash='b' * 64,
                    file_size=100,
                    status='detected'
                )
                db.session.add(event)
                db.session.commit()

                csv_report = ReportService.generate_csv_report()
                assert 'test.txt' in csv_report
                assert 'modified' in csv_report
                assert 'a' * 64 in csv_report

                json_report = ReportService.generate_json_report()
                assert 'test.txt' in json_report
                assert '"event_type": "modified"' in json_report


class TestSchedulerConcurrency:
    """Test scheduler lock and overlap avoidance"""

    def test_scheduler_lock_prevents_overlap(self, app):
        """Test that if a scan cycle is running, another cycle skips"""
        scheduler = MonitoringScheduler(app)
        # Manually acquire the lock to simulate long-running scan
        assert scheduler._scan_lock.acquire(blocking=False) is True

        # Second attempt should return without executing
        scheduler._run_scheduled_scans()

        # Release lock
        scheduler._scan_lock.release()
