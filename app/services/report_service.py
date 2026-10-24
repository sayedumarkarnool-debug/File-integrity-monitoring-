import csv
import json
from io import StringIO
from datetime import datetime
from typing import List, Dict

from app.models.integrity_event import IntegrityEvent
from app.models.monitored_directory import MonitoredDirectory
from app.extensions import db

class ReportService:
    """Service for generating reports"""

    @staticmethod
    def generate_csv_report(directory_id: int = None, start_date: datetime = None, end_date: datetime = None) -> str:
        """
        Generate CSV report of integrity events.

        Args:
            directory_id: Optional filter by directory
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            CSV string
        """
        query = IntegrityEvent.query

        if directory_id:
            query = query.filter_by(directory_id=directory_id)
        if start_date:
            query = query.filter(IntegrityEvent.detected_at >= start_date)
        if end_date:
            query = query.filter(IntegrityEvent.detected_at <= end_date)

        events = query.order_by(IntegrityEvent.detected_at.desc()).all()

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            'Detected At (UTC)',
            'Directory',
            'File Path',
            'Event Type',
            'Previous Hash',
            'Current Hash',
            'File Size',
            'Status'
        ])

        # Write data
        for event in events:
            # Escape values to prevent CSV injection
            file_path = ReportService._escape_csv_value(event.file_path)
            directory_path = ReportService._escape_csv_value(event.directory.path) if event.directory else ''

            writer.writerow([
                event.detected_at.strftime('%Y-%m-%d %H:%M:%S'),
                directory_path,
                file_path,
                event.event_type,
                event.previous_hash or '',
                event.current_hash or '',
                event.file_size or '',
                event.status
            ])

        return output.getvalue()

    @staticmethod
    def generate_json_report(directory_id: int = None, start_date: datetime = None, end_date: datetime = None) -> str:
        """
        Generate JSON report of integrity events.

        Args:
            directory_id: Optional filter by directory
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            JSON string
        """
        query = IntegrityEvent.query

        if directory_id:
            query = query.filter_by(directory_id=directory_id)
        if start_date:
            query = query.filter(IntegrityEvent.detected_at >= start_date)
        if end_date:
            query = query.filter(IntegrityEvent.detected_at <= end_date)

        events = query.order_by(IntegrityEvent.detected_at.desc()).all()

        # Build report structure
        report = {
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'filters': {
                'directory_id': directory_id,
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            },
            'summary': {
                'total_events': len(events),
                'added': sum(1 for e in events if e.event_type == 'added'),
                'modified': sum(1 for e in events if e.event_type == 'modified'),
                'deleted': sum(1 for e in events if e.event_type == 'deleted')
            },
            'events': []
        }

        for event in events:
            report['events'].append({
                'detected_at': event.detected_at.isoformat() + 'Z',
                'directory': event.directory.path if event.directory else None,
                'file_path': event.file_path,
                'event_type': event.event_type,
                'previous_hash': event.previous_hash,
                'current_hash': event.current_hash,
                'file_size': event.file_size,
                'status': event.status
            })

        return json.dumps(report, indent=2)

    @staticmethod
    def get_dashboard_stats() -> Dict:
        """
        Get statistics for dashboard overview.

        Returns:
            Dictionary with dashboard statistics
        """
        total_directories = MonitoredDirectory.query.filter_by(is_enabled=True).count()

        # Get total files from monitored directories
        total_files = db.session.query(db.func.sum(MonitoredDirectory.file_count)).scalar() or 0

        # Get last successful scan
        last_scan = db.session.query(db.func.max(MonitoredDirectory.last_scan)).scalar()

        # Count events by type (last 30 days)
        thirty_days_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        thirty_days_ago = datetime(thirty_days_ago.year, thirty_days_ago.month, thirty_days_ago.day)

        recent_events = IntegrityEvent.query.filter(
            IntegrityEvent.detected_at >= thirty_days_ago
        ).all()

        added_count = sum(1 for e in recent_events if e.event_type == 'added')
        modified_count = sum(1 for e in recent_events if e.event_type == 'modified')
        deleted_count = sum(1 for e in recent_events if e.event_type == 'deleted')

        # Get recent events (last 10)
        recent_events_list = IntegrityEvent.query.order_by(
            IntegrityEvent.detected_at.desc()
        ).limit(10).all()

        # Check monitoring status
        enabled_dirs = MonitoredDirectory.query.filter_by(is_enabled=True).count()
        monitoring_status = 'active' if enabled_dirs > 0 else 'inactive'

        return {
            'total_monitored_files': int(total_files),
            'total_monitored_directories': total_directories,
            'last_scan': last_scan,
            'monitoring_status': monitoring_status,
            'added_files': added_count,
            'modified_files': modified_count,
            'deleted_files': deleted_count,
            'recent_events': [
                {
                    'id': e.id,
                    'file_path': e.file_path,
                    'event_type': e.event_type,
                    'detected_at': e.detected_at,
                    'directory': e.directory.path if e.directory else None
                }
                for e in recent_events_list
            ]
        }

    @staticmethod
    def _escape_csv_value(value: str) -> str:
        """
        Escape CSV value to prevent formula injection.

        Args:
            value: Value to escape

        Returns:
            Escaped value
        """
        if not value:
            return value

        # Check for formula injection characters
        dangerous_chars = ['=', '+', '-', '@', '\t', '\r']

        if any(value.startswith(char) for char in dangerous_chars):
            # Prepend with single quote to treat as text
            return "'" + value

        return value
