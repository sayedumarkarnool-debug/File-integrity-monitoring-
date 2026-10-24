from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy import func

from app.extensions import db
from app.models.baseline import BaselineEntry
from app.models.monitored_directory import MonitoredDirectory
from app.services.scanner import DirectoryScanner
from app.services.audit_service import AuditService

class BaselineService:
    """Service for managing baseline snapshots"""

    def __init__(self):
        self.scanner = DirectoryScanner()
        self.audit_service = AuditService()

    def create_baseline(self, directory_id: int, actor: str = 'system') -> Dict:
        """
        Create a new baseline for a monitored directory.

        Args:
            directory_id: ID of the monitored directory
            actor: Username or 'system'

        Returns:
            Dictionary with:
                - success: Boolean
                - message: Status message
                - file_count: Number of files in baseline
                - errors: List of errors encountered
        """
        directory = db.session.get(MonitoredDirectory, directory_id)

        if not directory:
            return {
                'success': False,
                'message': 'Directory not found',
                'file_count': 0,
                'errors': ['Directory not found']
            }

        # Scan the directory
        scan_result = self.scanner.scan_directory(directory.path, recursive=True)

        if not scan_result['scan_complete']:
            # Log failed baseline creation
            self.audit_service.log_action(
                actor=actor,
                action='baseline_creation_failed',
                resource_type='baseline',
                resource_id=str(directory_id),
                outcome='failed',
                error_details='; '.join(scan_result['errors']),
                details=f"Incomplete scan for directory: {directory.path}"
            )

            return {
                'success': False,
                'message': 'Scan incomplete - baseline not created',
                'file_count': 0,
                'errors': scan_result['errors']
            }

        # Get current baseline version
        current_version = db.session.query(func.max(BaselineEntry.baseline_version)).filter_by(
            directory_id=directory_id
        ).scalar() or 0

        new_version = current_version + 1

        # Create baseline entries
        file_count = 0
        for relative_path, file_info in scan_result['files'].items():
            # Skip files with errors
            if file_info['error'] or not file_info['hash']:
                continue

            entry = BaselineEntry(
                directory_id=directory_id,
                relative_path=relative_path,
                sha256_hash=file_info['hash'],
                file_size=file_info['size'],
                modification_time=file_info['mtime'],
                baseline_version=new_version
            )
            db.session.add(entry)
            file_count += 1

        # Update directory metadata
        directory.file_count = file_count
        directory.last_scan = datetime.utcnow()
        directory.last_scan_status = 'success'
        directory.last_scan_error = None

        db.session.commit()

        # Log successful baseline creation
        self.audit_service.log_action(
            actor=actor,
            action='baseline_created',
            resource_type='baseline',
            resource_id=str(directory_id),
            outcome='success',
            details=f"Created baseline v{new_version} with {file_count} files for: {directory.path}"
        )

        return {
            'success': True,
            'message': f'Baseline created with {file_count} files',
            'file_count': file_count,
            'errors': scan_result['errors']
        }

    def replace_baseline(self, directory_id: int, actor: str, reason: str) -> Dict:
        """
        Replace existing baseline with a new one.
        This requires explicit confirmation from the caller.

        Args:
            directory_id: ID of the monitored directory
            actor: Username performing the action
            reason: Reason for baseline replacement

        Returns:
            Dictionary with success status and details
        """
        directory = db.session.get(MonitoredDirectory, directory_id)

        if not directory:
            return {
                'success': False,
                'message': 'Directory not found'
            }

        # Check if baseline exists
        existing_count = BaselineEntry.query.filter_by(directory_id=directory_id).count()

        # Log the replacement attempt
        self.audit_service.log_action(
            actor=actor,
            action='baseline_replacement_initiated',
            resource_type='baseline',
            resource_id=str(directory_id),
            details=f"Replacing baseline for: {directory.path}. Reason: {reason}. Previous entries: {existing_count}"
        )

        # Create new baseline first (safely versions new entries)
        result = self.create_baseline(directory_id, actor)

        if result['success']:
            # Clean up old baseline versions only after successful new baseline creation
            new_version = db.session.query(func.max(BaselineEntry.baseline_version)).filter_by(
                directory_id=directory_id
            ).scalar()
            if new_version:
                BaselineEntry.query.filter(
                    BaselineEntry.directory_id == directory_id,
                    BaselineEntry.baseline_version < new_version
                ).delete()
                db.session.commit()

            self.audit_service.log_action(
                actor=actor,
                action='baseline_replaced',
                resource_type='baseline',
                resource_id=str(directory_id),
                outcome='success',
                details=f"Replaced baseline for: {directory.path}. New entries: {result['file_count']}. Reason: {reason}"
            )
        else:
            self.audit_service.log_action(
                actor=actor,
                action='baseline_replacement_failed',
                resource_type='baseline',
                resource_id=str(directory_id),
                outcome='failed',
                error_details='; '.join(result['errors']),
                details=f"Failed to replace baseline for: {directory.path}. Previous baseline preserved."
            )
        return result

    def get_baseline_info(self, directory_id: int) -> Optional[Dict]:
        """
        Get information about the current baseline.

        Returns:
            Dictionary with baseline information or None
        """
        directory = db.session.get(MonitoredDirectory, directory_id)

        if not directory:
            return None

        # Get current baseline version
        current_version = db.session.query(func.max(BaselineEntry.baseline_version)).filter_by(
            directory_id=directory_id
        ).scalar()

        if not current_version:
            return {
                'exists': False,
                'directory': directory.path,
                'file_count': 0
            }

        # Get baseline creation timestamp
        first_entry = BaselineEntry.query.filter_by(
            directory_id=directory_id,
            baseline_version=current_version
        ).order_by(BaselineEntry.created_at).first()

        file_count = BaselineEntry.query.filter_by(
            directory_id=directory_id,
            baseline_version=current_version
        ).count()

        return {
            'exists': True,
            'directory': directory.path,
            'version': current_version,
            'file_count': file_count,
            'created_at': first_entry.created_at if first_entry else None,
            'last_scan': directory.last_scan,
            'last_scan_status': directory.last_scan_status
        }

    def get_baseline_entries(self, directory_id: int) -> List[BaselineEntry]:
        """Get all baseline entries for a directory"""
        # Get current baseline version
        current_version = db.session.query(func.max(BaselineEntry.baseline_version)).filter_by(
            directory_id=directory_id
        ).scalar()

        if not current_version:
            return []

        return BaselineEntry.query.filter_by(
            directory_id=directory_id,
            baseline_version=current_version
        ).all()
