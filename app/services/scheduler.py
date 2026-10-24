from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import threading
import logging

from app.models.monitored_directory import MonitoredDirectory
from app.services.detection_engine import DetectionEngine

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    """Service for scheduling automatic file integrity scans"""

    def __init__(self, app=None):
        self.scheduler = None
        self.detection_engine = DetectionEngine()
        self.app = app
        self._scan_lock = threading.Lock()

    def init_app(self, app):
        """Initialize scheduler with Flask app"""
        self.app = app
        scan_interval = app.config.get('SCAN_INTERVAL_SECONDS', 60)

        # Create scheduler
        self.scheduler = BackgroundScheduler(daemon=True)

        # Add job to run scans at configured interval
        self.scheduler.add_job(
            func=self._run_scheduled_scans,
            trigger=IntervalTrigger(seconds=scan_interval),
            id='integrity_scan',
            name='File Integrity Scan',
            replace_existing=True
        )

        logger.info(f'Monitoring scheduler initialized with {scan_interval}s interval')

    def start(self):
        """Start the scheduler"""
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            logger.info('Monitoring scheduler started')

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info('Monitoring scheduler stopped')

    def _run_scheduled_scans(self):
        """Run scans on all enabled directories"""
        if not self.app:
            logger.error('Scheduler not initialized with Flask app')
            return

        if not self._scan_lock.acquire(blocking=False):
            logger.warning('Previous scan cycle is still executing. Skipping this interval to avoid overlap.')
            return

        try:
            with self.app.app_context():
                # Get all enabled directories
                directories = MonitoredDirectory.query.filter_by(is_enabled=True).all()

                if not directories:
                    logger.debug('No enabled directories to scan')
                    return

                logger.info(f'Running scheduled scan on {len(directories)} directories')

                for directory in directories:
                    try:
                        # Check if baseline exists
                        from app.services.baseline_service import BaselineService
                        baseline_service = BaselineService()
                        baseline_info = baseline_service.get_baseline_info(directory.id)

                        if not baseline_info or not baseline_info['exists']:
                            logger.warning(f'No baseline for directory {directory.id}: {directory.path}')
                            continue

                        # Run scan and detection
                        result = self.detection_engine.scan_and_detect(directory.id, 'system')

                        if result['scan_complete']:
                            logger.info(
                                f'Scan complete for {directory.path}: '
                                f'Added={len(result["added"])}, '
                                f'Modified={len(result["modified"])}, '
                                f'Deleted={len(result["deleted"])}, '
                                f'Events={result.get("events_recorded", 0)}'
                            )
                        else:
                            logger.warning(f'Incomplete scan for {directory.path}: {result.get("errors", [])}')

                    except Exception as e:
                        logger.error(f'Error scanning directory {directory.id}: {str(e)}')
                        continue

        except Exception as e:
            logger.error(f'Error in scheduled scan: {str(e)}')
        finally:
            self._scan_lock.release()

# Global scheduler instance
scheduler = MonitoringScheduler()
