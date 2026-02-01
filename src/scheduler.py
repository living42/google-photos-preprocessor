"""Scheduler module for daily execution."""

import time
import logging
from typing import Callable, Optional
from datetime import datetime

import schedule


class DailyScheduler:
    """Manages daily scheduled execution using the schedule library."""
    
    def __init__(
        self,
        schedule_time: str,
        job_func: Callable,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize scheduler.
        
        Args:
            schedule_time: Time to run daily (format: "HH:MM", 24-hour)
            job_func: Function to call at scheduled time
            logger: Logger instance
        """
        self.schedule_time = schedule_time
        self.job_func = job_func
        self.logger = logger or logging.getLogger(__name__)
        self._stop_flag = False
        
        # Validate and parse time
        try:
            datetime.strptime(schedule_time, "%H:%M")
        except ValueError:
            raise ValueError(f"Invalid schedule_time format: {schedule_time}. Expected HH:MM (24-hour format)")
        
        # Schedule the job
        schedule.every().day.at(schedule_time).do(self._run_job)
        
        self.logger.info(f"Scheduled daily job at {schedule_time}")
    
    def _run_job(self):
        """Wrapper to run the job."""
        self.logger.info("Starting scheduled job execution")
        self.job_func()
        self.logger.info("Scheduled job completed successfully")
    
    def start(self) -> None:
        """Start the scheduler loop."""
        self.logger.info("Scheduler started. Waiting for scheduled time...")
        
        while not self._stop_flag:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        
        self.logger.info("Scheduler stopped")
    
    def run_once(self) -> None:
        """Run the job immediately once."""
        self.logger.info("Running job immediately (RUN_ONCE mode)")
        self._run_job()
    
    def stop(self) -> None:
        """Signal the scheduler to stop."""
        self._stop_flag = True
        self.logger.info("Stop signal received")
    
    def get_next_run(self) -> Optional[str]:
        """
        Get the next scheduled run time.
        
        Returns:
            String representation of next run time, or None if not scheduled
        """
        next_run = schedule.next_run()
        if next_run:
            return str(next_run)
        return None
