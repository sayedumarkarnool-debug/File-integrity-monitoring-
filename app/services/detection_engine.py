from datetime import datetime
from typing import Dict, List, Set
from collections import defaultdict

from app.extensions import db
from app.models.baseline import BaselineEntry
from app.models.integrity_event import IntegrityEvent
from app.models.monitored_directory import MonitoredDirectory
from app.services.scanner import DirectoryScanner
from app.services.audit_service import AuditService

class DetectionEngine:
    """Service for detecting file integrity changes"""

    def __init__(self):
        self.scanner = DirectoryScanner()
        self.audit_service = AuditService()

    def detect_changes(self, directory_id: int) -> Dict:
        """
        Detect changes by comparing current scan with baseline.

        Args:
            directory_id: ID of the monitored directory

        Returns:
            Dictionary with:
                - added: List of added files
                - modified: List of modified files
                - deleted: List of deleted files
                - unchanged: Count of unchanged files
                - scan_complete: Whether scan was complete
                - errors: List of errors
        """
        directory = db.session.get(MonitoredDirectory, directory_id)

        if not directory:
            return {
                'added': [],
                'modified': [],
                'deleted': [],
                'unchanged': 0,
                'scan_complete': False,
                'errors': ['Directory not found']
            }

        # Get current baseline version
        current_version = db.session.query(db.func.max(BaselineEntry.baseline_version)).filter_by(
            directory_id=directory_id
        ).scalar()

        if not current_version:
            return {
                'added': [],
                'modified': [],
                'deleted': [],
                'unchanged': 0,
                'scan_complete': False,
                'errors': ['No baseline exists for this directory']
            }

        # Get baseline entries for current version
        baseline_entries = {}
        for entry in BaselineEntry.query.filter_by(directory_id=directory_id, baseline_version=current_version).all():
            baseline_entries[entry.relative_path] = {
                'hash': entry.sha256_hash,
                'size': entry.file_size
            }

        if not baseline_entries:
            return {
                'added': [],
                'modified': [],
                'deleted': [],
                'unchanged': 0,
                'scan_complete': False,
                'errors': ['Baseline contains no files for this directory']
            }

        # Perform current scan
        scan_result = self.scanner.scan_directory(directory.path, recursive=True)

        # Update directory scan status
        directory.last_scan = datetime.utcnow()
        directory.last_scan_status = 'success' if scan_result['scan_complete'] else 'incomplete'
        if not scan_result['scan_complete']:
            directory.last_scan_error = '; '.join(scan_result['errors'][:5])  # Store first 5 errors

        db.session.commit()

        # If scan is incomplete, don't report deletions
        if not scan_result['scan_complete']:
            return {
                'added': [],
                'modified': [],
                'deleted': [],
                'unchanged': 0,
                'scan_complete': False,
                'errors': scan_result['errors'] + ['Scan incomplete - no changes reported to avoid false deletions']
            }

        added_files = []
        modified_files = []
        deleted_files = []
        unchanged_count = 0

        current_files = set()

        # Check for added and modified files
        for relative_path, file_info in scan_result['files'].items():
            # Skip files with errors
            if file_info['error'] or not file_info['hash']:
                continue

            current_files.add(relative_path)

            if relative_path not in baseline_entries:
                # ADDED: File in current scan but not in baseline
                added_files.append({
                    'path': relative_path,
                    'hash': file_info['hash'],
                    'size': file_info['size']
                })
            elif baseline_entries[relative_path]['hash'] != file_info['hash']:
                # MODIFIED: File exists in both but hash differs
                modified_files.append({
                    'path': relative_path,
                    'previous_hash': baseline_entries[relative_path]['hash'],
                    'current_hash': file_info['hash'],
                    'size': file_info['size']
                })
            else:
                # UNCHANGED: File exists in both and hash matches
                unchanged_count += 1

        # Check for deleted files
        # Only report deletions if scan was complete
        baseline_files = set(baseline_entries.keys())
        failed_files_set = {path for path, info in scan_result['files'].items() if info.get('error')}
        for relative_path in baseline_files - current_files:
            # If the file had a scan or read error, it is still on disk - do not report as deleted
            if relative_path in failed_files_set:
                continue
            # DELETED: File in baseline but not in current scan
            deleted_files.append({
                'path': relative_path,
                'previous_hash': baseline_entries[relative_path]['hash']
            })

        return {
            'added': added_files,
            'modified': modified_files,
            'deleted': deleted_files,
            'unchanged': unchanged_count,
            'scan_complete': scan_result['scan_complete'],
            'errors': scan_result['errors']
        }

    def record_events(self, directory_id: int, changes: Dict, actor: str = 'system') -> int:
        """
        Record detected changes as integrity events.

        Args:
            directory_id: ID of the monitored directory
            changes: Dictionary from detect_changes()
            actor: Username or 'system'

        Returns:
            Number of events recorded
        """
        events_recorded = 0
        timestamp = datetime.utcnow()

        # Record added files
        for file_info in changes['added']:
            event = IntegrityEvent(
                directory_id=directory_id,
                file_path=file_info['path'],
                event_type='added',
                detected_at=timestamp,
                previous_hash=None,
                current_hash=file_info['hash'],
                file_size=file_info.get('size'),
                status='detected'
            )
            db.session.add(event)

            # Log to audit
            self.audit_service.log_action(
                actor=actor,
                action='file_added',
                resource_type='file',
                file_path=file_info['path'],
                event_type='added',
                current_hash=file_info['hash'],
                outcome='success'
            )

            events_recorded += 1

        # Record modified files
        for file_info in changes['modified']:
            event = IntegrityEvent(
                directory_id=directory_id,
                file_path=file_info['path'],
                event_type='modified',
                detected_at=timestamp,
                previous_hash=file_info['previous_hash'],
                current_hash=file_info['current_hash'],
                file_size=file_info.get('size'),
                status='detected'
            )
            db.session.add(event)

            # Log to audit
            self.audit_service.log_action(
                actor=actor,
                action='file_modified',
                resource_type='file',
                file_path=file_info['path'],
                event_type='modified',
                previous_hash=file_info['previous_hash'],
                current_hash=file_info['current_hash'],
                outcome='success'
            )

            events_recorded += 1

        # Record deleted files
        for file_info in changes['deleted']:
            event = IntegrityEvent(
                directory_id=directory_id,
                file_path=file_info['path'],
                event_type='deleted',
                detected_at=timestamp,
                previous_hash=file_info['previous_hash'],
                current_hash=None,
                file_size=None,
                status='detected'
            )
            db.session.add(event)

            # Log to audit
            self.audit_service.log_action(
                actor=actor,
                action='file_deleted',
                resource_type='file',
                file_path=file_info['path'],
                event_type='deleted',
                previous_hash=file_info['previous_hash'],
                outcome='success'
            )

            events_recorded += 1

        db.session.commit()

        return events_recorded

    def scan_and_detect(self, directory_id: int, actor: str = 'system') -> Dict:
        """
        Convenience method to scan and detect changes in one call.

        Args:
            directory_id: ID of the monitored directory
            actor: Username or 'system'

        Returns:
            Dictionary with detection results and event count
        """
        changes = self.detect_changes(directory_id)

        if changes['scan_complete']:
            events_recorded = self.record_events(directory_id, changes, actor)
            changes['events_recorded'] = events_recorded
        else:
            changes['events_recorded'] = 0

        return changes
