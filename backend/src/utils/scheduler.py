"""
Task scheduling module for automated satellite imagery downloading and processing.

This module provides scheduling functionality to automatically check for new
satellite images and perform deforestation detection analysis at regular intervals.
"""

import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any
import logging
from pathlib import Path
import json

from .logger import LoggerMixin, log_function_call
from .config import get_config


class TaskScheduler(LoggerMixin):
    """
    Task scheduler for automated deforestation monitoring.
    
    This class manages the scheduling of image downloads, processing tasks,
    and change detection analysis at configurable intervals.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize task scheduler.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = get_config(config_path)
        self.is_running = False
        self.scheduler_thread = None
        
        # Scheduling parameters from config
        self.update_interval_days = self.config.get('scheduler.update_interval_days', 5)
        self.check_time = self.config.get('scheduler.check_time', '02:00')
        self.max_images_per_update = self.config.get('scheduler.max_images_per_update', 10)
        
        # Task status tracking
        self.last_run_file = self.config.get_data_dir('metadata') / 'last_run.json'
        self.task_history = []
        
        # Callback functions
        self.download_callback = None
        self.processing_callback = None
        self.notification_callback = None
        
        self.logger.info("Task scheduler initialized")
    
    def set_download_callback(self, callback: Callable[[], Any]) -> None:
        """
        Set callback function for image downloading.
        
        Args:
            callback: Function to call for downloading images
        """
        self.download_callback = callback
        self.logger.info("Download callback set")
    
    def set_processing_callback(self, callback: Callable[[Any], Any]) -> None:
        """
        Set callback function for image processing.
        
        Args:
            callback: Function to call for processing downloaded images
        """
        self.processing_callback = callback
        self.logger.info("Processing callback set")
    
    def set_notification_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Set callback function for notifications.
        
        Args:
            callback: Function to call for sending notifications
        """
        self.notification_callback = callback
        self.logger.info("Notification callback set")
    
    @log_function_call
    def schedule_regular_updates(self) -> None:
        """Schedule regular updates based on configuration."""
        # Schedule daily check at specified time
        schedule.every().day.at(self.check_time).do(self._check_for_updates)
        
        # Schedule weekly maintenance
        schedule.every().sunday.at("01:00").do(self._weekly_maintenance)
        
        self.logger.info(f"Scheduled regular updates: daily at {self.check_time}, weekly maintenance on Sunday")
    
    def _check_for_updates(self) -> None:
        """Check if updates are needed and perform them."""
        try:
            self.logger.info("Starting scheduled update check")
            
            # Check if enough time has passed since last update
            last_run_info = self._load_last_run_info()
            
            if last_run_info:
                last_update = datetime.fromisoformat(last_run_info['last_update'])
                days_since_update = (datetime.now() - last_update).days
                
                if days_since_update < self.update_interval_days:
                    self.logger.info(f"Skipping update - only {days_since_update} days since last update")
                    return
            
            # Perform update
            update_result = self._perform_update()
            
            # Save update info
            self._save_last_run_info(update_result)
            
            # Send notification if configured
            if self.notification_callback:
                self.notification_callback("scheduled_update", update_result)
            
            self.logger.info("Scheduled update completed successfully")
            
        except Exception as e:
            self.logger.error(f"Scheduled update failed: {e}")
            
            # Send error notification
            if self.notification_callback:
                self.notification_callback("update_error", {"error": str(e)})
    
    def _perform_update(self) -> Dict[str, Any]:
        """Perform the actual update process."""
        update_result = {
            'timestamp': datetime.now().isoformat(),
            'status': 'success',
            'downloaded_images': 0,
            'processed_images': 0,
            'detected_changes': 0,
            'errors': []
        }
        
        try:
            # Step 1: Download new images
            if self.download_callback:
                self.logger.info("Downloading new images...")
                download_result = self.download_callback()
                
                if isinstance(download_result, list):
                    update_result['downloaded_images'] = len(download_result)
                    downloaded_paths = download_result
                elif isinstance(download_result, dict):
                    update_result['downloaded_images'] = download_result.get('count', 0)
                    downloaded_paths = download_result.get('paths', [])
                else:
                    downloaded_paths = []
                
                self.logger.info(f"Downloaded {update_result['downloaded_images']} new images")
            else:
                self.logger.warning("No download callback set")
                downloaded_paths = []
            
            # Step 2: Process downloaded images
            if self.processing_callback and downloaded_paths:
                self.logger.info("Processing downloaded images...")
                processing_result = self.processing_callback(downloaded_paths)
                
                if isinstance(processing_result, dict):
                    update_result['processed_images'] = processing_result.get('processed_count', 0)
                    update_result['detected_changes'] = processing_result.get('change_count', 0)
                else:
                    update_result['processed_images'] = len(downloaded_paths)
                
                self.logger.info(f"Processed {update_result['processed_images']} images")
            
        except Exception as e:
            update_result['status'] = 'error'
            update_result['errors'].append(str(e))
            self.logger.error(f"Update process failed: {e}")
            raise
        
        return update_result
    
    def _weekly_maintenance(self) -> None:
        """Perform weekly maintenance tasks."""
        try:
            self.logger.info("Starting weekly maintenance")
            
            # Clean up old temporary files
            self._cleanup_temp_files()
            
            # Compress old log files
            self._compress_old_logs()
            
            # Generate weekly report
            self._generate_weekly_report()
            
            self.logger.info("Weekly maintenance completed")
            
        except Exception as e:
            self.logger.error(f"Weekly maintenance failed: {e}")
    
    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files older than 7 days."""
        temp_dirs = [
            self.config.get_data_dir('raw_images'),
            self.config.get_data_dir('processed_images')
        ]
        
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for temp_dir in temp_dirs:
            if temp_dir.exists():
                for file_path in temp_dir.rglob('*'):
                    if file_path.is_file():
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_time < cutoff_date and file_path.suffix in ['.tmp', '.temp', '.zip']:
                            try:
                                file_path.unlink()
                                self.logger.debug(f"Deleted temporary file: {file_path}")
                            except Exception as e:
                                self.logger.warning(f"Failed to delete {file_path}: {e}")
    
    def _compress_old_logs(self) -> None:
        """Compress log files older than 30 days."""
        # This would compress log files - implementation depends on log file location
        self.logger.debug("Log compression not implemented yet")
    
    def _generate_weekly_report(self) -> None:
        """Generate a weekly summary report."""
        # This would generate a summary of the week's activities
        self.logger.debug("Weekly report generation not implemented yet")
    
    def _load_last_run_info(self) -> Optional[Dict[str, Any]]:
        """Load information about the last run."""
        try:
            if self.last_run_file.exists():
                with open(self.last_run_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load last run info: {e}")
        
        return None
    
    def _save_last_run_info(self, update_result: Dict[str, Any]) -> None:
        """Save information about the current run."""
        try:
            # Ensure metadata directory exists
            self.last_run_file.parent.mkdir(parents=True, exist_ok=True)
            
            run_info = {
                'last_update': datetime.now().isoformat(),
                'update_result': update_result
            }
            
            with open(self.last_run_file, 'w') as f:
                json.dump(run_info, f, indent=2)
            
            # Add to task history
            self.task_history.append(run_info)
            
            # Keep only last 100 entries
            if len(self.task_history) > 100:
                self.task_history = self.task_history[-100:]
            
        except Exception as e:
            self.logger.error(f"Failed to save last run info: {e}")
    
    @log_function_call
    def start_scheduler(self) -> None:
        """Start the scheduler in a separate thread."""
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("Scheduler started")
    
    @log_function_call
    def stop_scheduler(self) -> None:
        """Stop the scheduler."""
        if not self.is_running:
            self.logger.warning("Scheduler is not running")
            return
        
        self.is_running = False
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        # Clear all scheduled jobs
        schedule.clear()
        
        self.logger.info("Scheduler stopped")
    
    def force_update_check(self) -> Dict[str, Any]:
        """Force an immediate update check."""
        self.logger.info("Forcing immediate update check")
        
        try:
            update_result = self._perform_update()
            self._save_last_run_info(update_result)
            
            if self.notification_callback:
                self.notification_callback("manual_update", update_result)
            
            return update_result
            
        except Exception as e:
            self.logger.error(f"Forced update failed: {e}")
            
            error_result = {
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'errors': [str(e)]
            }
            
            if self.notification_callback:
                self.notification_callback("update_error", error_result)
            
            return error_result
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        last_run_info = self._load_last_run_info()
        
        return {
            'is_running': self.is_running,
            'update_interval_days': self.update_interval_days,
            'check_time': self.check_time,
            'last_run': last_run_info['last_update'] if last_run_info else None,
            'last_run_status': last_run_info['update_result']['status'] if last_run_info else None,
            'scheduled_jobs': len(schedule.jobs),
            'task_history_count': len(self.task_history)
        }
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Get the time of the next scheduled run."""
        if not schedule.jobs:
            return None
        
        next_job = schedule.next_run()
        return next_job if next_job else None
    
    def update_schedule_config(
        self,
        update_interval_days: Optional[int] = None,
        check_time: Optional[str] = None,
        max_images_per_update: Optional[int] = None
    ) -> None:
        """
        Update scheduler configuration.
        
        Args:
            update_interval_days: New update interval in days
            check_time: New check time in HH:MM format
            max_images_per_update: New maximum images per update
        """
        if update_interval_days is not None:
            self.update_interval_days = update_interval_days
            self.config.set('scheduler.update_interval_days', update_interval_days)
        
        if check_time is not None:
            self.check_time = check_time
            self.config.set('scheduler.check_time', check_time)
        
        if max_images_per_update is not None:
            self.max_images_per_update = max_images_per_update
            self.config.set('scheduler.max_images_per_update', max_images_per_update)
        
        # Reschedule with new settings
        if self.is_running:
            schedule.clear()
            self.schedule_regular_updates()
        
        self.logger.info("Scheduler configuration updated")


class NotificationManager(LoggerMixin):
    """
    Notification manager for sending alerts and updates.
    
    This class handles sending notifications via email and other channels
    when important events occur in the deforestation monitoring system.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize notification manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = get_config(config_path)
        
        # Email configuration
        self.email_enabled = self.config.get('notifications.email.enabled', False)
        self.smtp_server = self.config.get('notifications.email.smtp_server', '')
        self.smtp_port = self.config.get('notifications.email.smtp_port', 587)
        self.email_username = self.config.get('notifications.email.username', '')
        self.email_password = self.config.get('notifications.email.password', '')
        self.recipients = self.config.get('notifications.email.recipients', [])
        
        # Notification settings
        self.send_on_new_images = self.config.get('notifications.send_on_new_images', True)
        self.send_on_deforestation = self.config.get('notifications.send_on_deforestation_detected', True)
        self.send_on_errors = self.config.get('notifications.send_on_errors', True)
        
        self.logger.info("Notification manager initialized")
    
    @log_function_call
    def send_notification(self, notification_type: str, data: Dict[str, Any]) -> None:
        """
        Send notification based on type and data.
        
        Args:
            notification_type: Type of notification (e.g., 'scheduled_update', 'deforestation_detected')
            data: Notification data
        """
        try:
            if notification_type == "scheduled_update" and self.send_on_new_images:
                self._send_update_notification(data)
            
            elif notification_type == "deforestation_detected" and self.send_on_deforestation:
                self._send_deforestation_alert(data)
            
            elif notification_type == "update_error" and self.send_on_errors:
                self._send_error_notification(data)
            
            elif notification_type == "manual_update":
                self._send_manual_update_notification(data)
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
    
    def _send_update_notification(self, data: Dict[str, Any]) -> None:
        """Send notification about scheduled update results."""
        subject = "Deforestation Monitoring - Update Complete"
        
        message = f"""
        Automated deforestation monitoring update completed.
        
        Update Summary:
        - Status: {data.get('status', 'Unknown')}
        - New images downloaded: {data.get('downloaded_images', 0)}
        - Images processed: {data.get('processed_images', 0)}
        - Changes detected: {data.get('detected_changes', 0)}
        - Timestamp: {data.get('timestamp', 'Unknown')}
        
        {'Errors occurred during update:' if data.get('errors') else 'No errors reported.'}
        {chr(10).join(data.get('errors', []))}
        
        This is an automated notification from the deforestation monitoring system.
        """
        
        if self.email_enabled:
            self._send_email(subject, message)
    
    def _send_deforestation_alert(self, data: Dict[str, Any]) -> None:
        """Send alert about detected deforestation."""
        subject = "ALERT: Deforestation Detected"
        
        message = f"""
        DEFORESTATION ALERT
        
        New deforestation activity has been detected in the monitoring area.
        
        Alert Details:
        - Number of change events: {data.get('event_count', 0)}
        - Total affected area: {data.get('total_area_hectares', 0)} hectares
        - Detection date: {data.get('detection_date', 'Unknown')}
        - Severity levels: {data.get('severity_distribution', {})}
        
        Please review the detailed analysis and take appropriate action.
        
        This is an automated alert from the deforestation monitoring system.
        """
        
        if self.email_enabled:
            self._send_email(subject, message)
    
    def _send_error_notification(self, data: Dict[str, Any]) -> None:
        """Send notification about errors."""
        subject = "Deforestation Monitoring - Error Occurred"
        
        message = f"""
        An error occurred in the deforestation monitoring system.
        
        Error Details:
        - Timestamp: {data.get('timestamp', 'Unknown')}
        - Errors: {chr(10).join(data.get('errors', ['Unknown error']))}
        
        Please check the system logs and take appropriate action.
        
        This is an automated error notification from the deforestation monitoring system.
        """
        
        if self.email_enabled:
            self._send_email(subject, message)
    
    def _send_manual_update_notification(self, data: Dict[str, Any]) -> None:
        """Send notification about manual update results."""
        subject = "Deforestation Monitoring - Manual Update Complete"
        
        message = f"""
        Manual deforestation monitoring update completed.
        
        Update Summary:
        - Status: {data.get('status', 'Unknown')}
        - New images downloaded: {data.get('downloaded_images', 0)}
        - Images processed: {data.get('processed_images', 0)}
        - Changes detected: {data.get('detected_changes', 0)}
        - Timestamp: {data.get('timestamp', 'Unknown')}
        
        This was a manually triggered update.
        """
        
        if self.email_enabled:
            self._send_email(subject, message)
    
    def _send_email(self, subject: str, message: str) -> None:
        """Send email notification."""
        if not self.email_enabled or not self.recipients:
            self.logger.debug("Email notifications disabled or no recipients configured")
            return
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_username
            msg['Subject'] = subject
            
            # Add message body
            msg.attach(MIMEText(message, 'plain'))
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_username, self.email_password)
                
                for recipient in self.recipients:
                    msg['To'] = recipient
                    server.send_message(msg)
                    del msg['To']
            
            self.logger.info(f"Email notification sent to {len(self.recipients)} recipients")
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
    
    def test_email_configuration(self) -> bool:
        """Test email configuration by sending a test message."""
        if not self.email_enabled:
            self.logger.info("Email notifications are disabled")
            return False
        
        try:
            self._send_email(
                "Deforestation Monitoring - Test Email",
                "This is a test email to verify the notification system is working correctly."
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Email configuration test failed: {e}")
            return False
