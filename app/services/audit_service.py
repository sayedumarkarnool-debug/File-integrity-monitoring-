from datetime import datetime
from typing import Optional

from app.extensions import db
from app.models.audit_log import AuditLog

class AuditService:
    """Service for audit logging"""

    @staticmethod
    def log_action(
        actor: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        file_path: Optional[str] = None,
        event_type: Optional[str] = None,
        previous_hash: Optional[str] = None,
        current_hash: Optional[str] = None,
        outcome: Optional[str] = None,
        error_details: Optional[str] = None,
        details: Optional[str] = None
    ):
        """
        Log an action to the audit log.

        Args:
            actor: Username or 'system'
            action: Action performed
            resource_type: Type of resource affected
            resource_id: ID of resource
            file_path: File path if applicable
            event_type: Event type for file integrity events
            previous_hash: Previous hash value
            current_hash: Current hash value
            outcome: 'success' or 'failed'
            error_details: Error details if failed
            details: Additional details
        """
        log_entry = AuditLog(
            timestamp=datetime.utcnow(),
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            file_path=file_path,
            event_type=event_type,
            previous_hash=previous_hash,
            current_hash=current_hash,
            outcome=outcome,
            error_details=error_details,
            details=details
        )

        db.session.add(log_entry)
        db.session.commit()
