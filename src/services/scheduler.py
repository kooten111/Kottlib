"""
Scheduler Service

Manages periodic tasks using APScheduler.
Handles library scanning schedules.
"""

import logging
import threading
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..database import Database, get_all_libraries, get_library_by_id
from ..scanner.threaded_scanner import ThreadedScanner
from pathlib import Path

logger = logging.getLogger(__name__)

class SchedulerService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SchedulerService, cls).__new__(cls)
            return cls._instance

    def __init__(self, db: Database):
        # Singleton check
        if hasattr(self, 'scheduler'):
            return

        self.db = db

        # Use memory-based job store (avoids Python 3.13 pickle issues with SQLAlchemy)
        # Jobs will be reloaded from DB on each server restart
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("Scheduler service started")

    def start(self):
        """Start the scheduler (idempotent)"""
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()

    def schedule_library_scan(self, library_id: int, interval_minutes: int):
        """
        Schedule a periodic scan for a library.
        If interval_minutes is 0, remove any existing schedule.
        """
        job_id = f"scan_library_{library_id}"
        
        # Remove existing job if any
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing scan schedule for library {library_id}")

        if interval_minutes > 0:
            self.scheduler.add_job(
                self._run_scan,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id=job_id,
                name=f"Scan Library {library_id}",
                replace_existing=True,
                args=[library_id]
            )
            logger.info(f"Scheduled scan for library {library_id} every {interval_minutes} minutes")

    def _run_scan(self, library_id: int):
        """Execute the library scan"""
        logger.info(f"Starting scheduled scan for library {library_id}")
        try:
            # Create a new scanner instance
            # Note: ThreadedScanner creates its own DB sessions
            scanner = ThreadedScanner(self.db, library_id)
            
            # Get library path
            with self.db.get_session() as session:
                library = get_library_by_id(session, library_id)
                if not library:
                    logger.error(f"Library {library_id} not found for scheduled scan")
                    return
                library_path = library.path
            
            scanner.scan_library(Path(library_path))
            logger.info(f"Scheduled scan completed for library {library_id}")
            
        except Exception as e:
            logger.error(f"Scheduled scan failed for library {library_id}: {e}", exc_info=True)

    def load_schedules_from_db(self):
        """Load scan schedules from library configurations on startup"""
        logger.info("Loading scan schedules from database...")
        with self.db.get_session() as session:
            libraries = get_all_libraries(session)
            for lib in libraries:
                if lib.scan_interval > 0:
                    self.schedule_library_scan(lib.id, lib.scan_interval)

# Global accessor
_scheduler_service: Optional[SchedulerService] = None
_scheduler_lock = threading.Lock()

def get_scheduler(db: Optional[Database] = None) -> SchedulerService:
    global _scheduler_service
    if _scheduler_service is not None:
        return _scheduler_service
    with _scheduler_lock:
        if _scheduler_service is None:
            if db is None:
                raise RuntimeError("Scheduler not initialized and no DB provided")
            _scheduler_service = SchedulerService(db)
        return _scheduler_service
