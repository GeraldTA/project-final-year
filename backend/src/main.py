"""
Main deforestation detection pipeline orchestrator.

This module integrates all components of the deforestation detection system
and provides a unified interface for downloading, processing, and analyzing
satellite imagery for deforestation monitoring.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import json
import logging

# Add src directory to path for imports
src_dir = Path(__file__).parent
project_root = src_dir.parent
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(project_root))

from data.sentinel_downloader import SentinelDownloader
from data.gee_client import GEEClient
from processing.ndvi_calculator import NDVICalculator
from processing.change_detector import ChangeDetector
from utils.config import get_config
from utils.logger import LoggerMixin, log_function_call, initialize_logging
from utils.scheduler import TaskScheduler, NotificationManager


class DeforestationPipeline(LoggerMixin):
    """
    Main deforestation detection pipeline.
    
    This class orchestrates the entire deforestation detection workflow,
    from satellite imagery downloading to change detection and reporting.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the deforestation detection pipeline.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = get_config(config_path)
        
        # Initialize logging
        initialize_logging(self.config)
        
        # Initialize components
        self.sentinel_downloader = SentinelDownloader(config_path)
        
        # Initialize GEE client if credentials are available
        try:
            self.gee_client = GEEClient(config_path)
            self.gee_available = True
        except Exception as e:
            self.logger.warning(f"Google Earth Engine not available: {e}")
            self.gee_client = None
            self.gee_available = False
        
        self.ndvi_calculator = NDVICalculator(config_path)
        self.change_detector = ChangeDetector(config_path)
        self.scheduler = TaskScheduler(config_path)
        self.notification_manager = NotificationManager(config_path)
        
        # Set up scheduler callbacks
        self.scheduler.set_download_callback(self.download_latest_images)
        self.scheduler.set_processing_callback(self._process_downloaded_images)
        self.scheduler.set_notification_callback(self.notification_manager.send_notification)
        
        # Pipeline state
        self.last_processed_images = []
        self.change_history = []
        
        self.logger.info("Deforestation detection pipeline initialized")
    
    @log_function_call
    def download_latest_images(self, days_back: int = 30, max_images: int = 10) -> List[Path]:
        """
        Download the latest satellite images.
        
        Args:
            days_back: Number of days to look back for images
            max_images: Maximum number of images to download
            
        Returns:
            List of paths to downloaded images
        """
        try:
            self.logger.info(f"Downloading latest images (last {days_back} days, max {max_images})")
            
            # Download images using Sentinel downloader
            downloaded_paths = self.sentinel_downloader.download_latest_images(
                days_back=days_back,
                max_images=max_images
            )
            
            # Update last processed images list
            self.last_processed_images = downloaded_paths
            
            # Save download metadata
            self._save_download_metadata(downloaded_paths)
            
            self.logger.info(f"Successfully downloaded {len(downloaded_paths)} images")
            return downloaded_paths
            
        except Exception as e:
            self.logger.error(f"Failed to download latest images: {e}")
            raise
    
    def _save_download_metadata(self, downloaded_paths: List[Path]) -> None:
        """Save metadata about downloaded images."""
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'downloaded_count': len(downloaded_paths),
            'paths': [str(path) for path in downloaded_paths]
        }
        
        metadata_file = self.config.get_data_dir('metadata') / 'download_history.json'
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Load existing metadata
            existing_metadata = []
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    existing_metadata = json.load(f)
            
            # Add new metadata
            existing_metadata.append(metadata)
            
            # Keep only last 100 entries
            if len(existing_metadata) > 100:
                existing_metadata = existing_metadata[-100:]
            
            # Save updated metadata
            with open(metadata_file, 'w') as f:
                json.dump(existing_metadata, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to save download metadata: {e}")
    
    def _process_downloaded_images(self, image_paths: List[Path]) -> Dict[str, Any]:
        """
        Process downloaded images for change detection.
        
        Args:
            image_paths: List of paths to downloaded images
            
        Returns:
            Dictionary with processing results
        """
        processing_results = {
            'processed_count': 0,
            'change_count': 0,
            'ndvi_results': [],
            'change_events': [],
            'errors': []
        }
        
        try:
            # Calculate NDVI for all images
            self.logger.info(f"Processing {len(image_paths)} images")
            
            ndvi_results = self.ndvi_calculator.batch_calculate_ndvi(
                [str(path) for path in image_paths],
                create_visualizations=True
            )
            
            processing_results['ndvi_results'] = ndvi_results
            processing_results['processed_count'] = len([r for r in ndvi_results if 'error' not in r])
            
            # Perform change detection if we have multiple time points
            if len(ndvi_results) >= 2:
                change_events = self._detect_changes_from_ndvi_results(ndvi_results)
                processing_results['change_events'] = change_events
                processing_results['change_count'] = len(change_events)
                
                # Send deforestation alert if significant changes detected
                if change_events:
                    self._send_deforestation_alert(change_events)
            
            # Save processing results
            self._save_processing_results(processing_results)
            
            self.logger.info(f"Processing completed: {processing_results['processed_count']} images processed, "
                           f"{processing_results['change_count']} changes detected")
            
        except Exception as e:
            self.logger.error(f"Failed to process downloaded images: {e}")
            processing_results['errors'].append(str(e))
        
        return processing_results
    
    def _detect_changes_from_ndvi_results(self, ndvi_results: List[Dict[str, Any]]) -> List[Any]:
        """Detect changes from NDVI calculation results."""
        # This is a simplified implementation
        # In practice, you would need to load the actual NDVI arrays and perform change detection
        change_events = []
        
        try:
            # Sort results by date (if available in metadata)
            valid_results = [r for r in ndvi_results if 'error' not in r]
            
            if len(valid_results) >= 2:
                # Compare the two most recent images
                # This is a placeholder - you would need to implement actual change detection
                # using the NDVI arrays and change detector
                
                self.logger.info("Change detection analysis would be performed here")
                # change_events = self.change_detector.detect_time_series_changes(...)
            
        except Exception as e:
            self.logger.error(f"Failed to detect changes: {e}")
        
        return change_events
    
    def _send_deforestation_alert(self, change_events: List[Any]) -> None:
        """Send deforestation alert notification."""
        if not change_events:
            return
        
        alert_data = {
            'event_count': len(change_events),
            'detection_date': datetime.now().isoformat(),
            'total_area_hectares': sum(getattr(event, 'area_hectares', 0) for event in change_events),
            'severity_distribution': {}
        }
        
        # Calculate severity distribution
        severities = [getattr(event, 'severity', 'unknown') for event in change_events]
        for severity in ['high', 'medium', 'low']:
            alert_data['severity_distribution'][severity] = severities.count(severity)
        
        self.notification_manager.send_notification('deforestation_detected', alert_data)
    
    def _save_processing_results(self, results: Dict[str, Any]) -> None:
        """Save processing results to file."""
        results_file = self.config.get_data_dir('metadata') / 'processing_history.json'
        results_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Load existing results
            existing_results = []
            if results_file.exists():
                with open(results_file, 'r') as f:
                    existing_results = json.load(f)
            
            # Add timestamp and append
            results['timestamp'] = datetime.now().isoformat()
            existing_results.append(results)
            
            # Keep only last 100 entries
            if len(existing_results) > 100:
                existing_results = existing_results[-100:]
            
            # Save updated results
            with open(results_file, 'w') as f:
                json.dump(existing_results, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.warning(f"Failed to save processing results: {e}")
    
    @log_function_call
    def detect_changes(
        self,
        start_date: str,
        end_date: str,
        create_visualizations: bool = True
    ) -> Dict[str, Any]:
        """
        Detect changes in the specified time period.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            create_visualizations: Whether to create visualization plots
            
        Returns:
            Dictionary with change detection results
        """
        try:
            self.logger.info(f"Detecting changes between {start_date} and {end_date}")
            
            # Query images for the time period
            max_cloud_cover = self.config.get('sentinel.max_cloud_cover')
            images = self.sentinel_downloader.query_images(
                start_date=start_date,
                end_date=end_date,
                max_cloud_cover=max_cloud_cover
            )
            
            if len(images) < 2:
                self.logger.warning("Insufficient images for change detection")
                return {
                    'status': 'insufficient_data',
                    'image_count': len(images),
                    'change_events': []
                }
            
            # Sort images by date
            images.sort(key=lambda x: x.date)
            
            # Download images if not already available
            downloaded_paths = []
            for image in images:
                try:
                    path = self.sentinel_downloader.download_image(image, extract=True)
                    downloaded_paths.append(path)
                except Exception as e:
                    self.logger.warning(f"Failed to download image {image.title}: {e}")
                    continue
            
            if len(downloaded_paths) < 2:
                self.logger.warning("Insufficient downloaded images for change detection")
                return {
                    'status': 'download_failed',
                    'downloaded_count': len(downloaded_paths),
                    'change_events': []
                }
            
            # Calculate NDVI for all images
            ndvi_results = self.ndvi_calculator.batch_calculate_ndvi(
                [str(path) for path in downloaded_paths],
                create_visualizations=create_visualizations
            )
            
            # Perform change detection (simplified implementation)
            change_events = self._detect_changes_from_ndvi_results(ndvi_results)
            
            results = {
                'status': 'success',
                'period': {'start': start_date, 'end': end_date},
                'image_count': len(images),
                'downloaded_count': len(downloaded_paths),
                'processed_count': len([r for r in ndvi_results if 'error' not in r]),
                'change_events': change_events,
                'ndvi_results': ndvi_results
            }
            
            # Save results
            self._save_change_detection_results(results)
            
            self.logger.info(f"Change detection completed: {len(change_events)} changes detected")
            return results
            
        except Exception as e:
            self.logger.error(f"Change detection failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'change_events': []
            }
    
    def _save_change_detection_results(self, results: Dict[str, Any]) -> None:
        """Save change detection results."""
        results_file = self.config.get_data_dir('metadata') / 'change_detection_history.json'
        results_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Load existing results
            existing_results = []
            if results_file.exists():
                with open(results_file, 'r') as f:
                    existing_results = json.load(f)
            
            # Add timestamp and append
            results['timestamp'] = datetime.now().isoformat()
            existing_results.append(results)
            
            # Keep only last 50 entries
            if len(existing_results) > 50:
                existing_results = existing_results[-50:]
            
            # Save updated results
            with open(results_file, 'w') as f:
                json.dump(existing_results, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.warning(f"Failed to save change detection results: {e}")
    
    @log_function_call
    def start_monitoring(self) -> None:
        """Start automated monitoring system."""
        try:
            self.logger.info("Starting automated deforestation monitoring")
            
            # Schedule regular updates
            self.scheduler.schedule_regular_updates()
            
            # Start the scheduler
            self.scheduler.start_scheduler()
            
            self.logger.info("Automated monitoring started successfully")
            self.logger.info(f"Next update scheduled for: {self.scheduler.get_next_run_time()}")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            raise
    
    @log_function_call
    def stop_monitoring(self) -> None:
        """Stop automated monitoring system."""
        try:
            self.logger.info("Stopping automated deforestation monitoring")
            
            # Stop the scheduler
            self.scheduler.stop_scheduler()
            
            self.logger.info("Automated monitoring stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop monitoring: {e}")
            raise
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring system status."""
        return {
            'pipeline_status': 'active',
            'scheduler_status': self.scheduler.get_scheduler_status(),
            'gee_available': self.gee_available,
            'last_processed_images': len(self.last_processed_images),
            'change_history_count': len(self.change_history),
            'config_region': self.config.get('region.name', 'Unknown')
        }
    
    def force_update(self) -> Dict[str, Any]:
        """Force an immediate update check and processing."""
        self.logger.info("Forcing immediate update")
        
        try:
            return self.scheduler.force_update_check()
        except Exception as e:
            self.logger.error(f"Forced update failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def generate_summary_report(self, output_path: Optional[str] = None) -> str:
        """
        Generate a comprehensive summary report.
        
        Args:
            output_path: Optional path to save the report
            
        Returns:
            Path to the generated report
        """
        if output_path is None:
            output_path = str(self.config.get_data_dir('metadata') / 
                            f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        
        try:
            # Gather data for the report
            monitoring_status = self.get_monitoring_status()
            
            # Load historical data
            download_history = self._load_historical_data('download_history.json')
            processing_history = self._load_historical_data('processing_history.json')
            change_history = self._load_historical_data('change_detection_history.json')
            
            # Generate HTML report
            self._generate_html_summary_report(
                output_path,
                monitoring_status,
                download_history,
                processing_history,
                change_history
            )
            
            self.logger.info(f"Summary report generated: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate summary report: {e}")
            raise
    
    def _load_historical_data(self, filename: str) -> List[Dict[str, Any]]:
        """Load historical data from JSON file."""
        try:
            file_path = self.config.get_data_dir('metadata') / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load {filename}: {e}")
        
        return []
    
    def _generate_html_summary_report(
        self,
        output_path: str,
        status: Dict[str, Any],
        download_history: List[Dict[str, Any]],
        processing_history: List[Dict[str, Any]],
        change_history: List[Dict[str, Any]]
    ) -> None:
        """Generate HTML summary report."""
        
        # Calculate summary statistics
        total_downloads = sum(entry.get('downloaded_count', 0) for entry in download_history)
        total_processed = sum(entry.get('processed_count', 0) for entry in processing_history)
        total_changes = sum(entry.get('change_count', 0) for entry in processing_history)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Deforestation Monitoring Summary Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                .header {{ background-color: #2c3e50; color: white; padding: 30px; text-align: center; border-radius: 10px; }}
                .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0; }}
                .stat-card {{ background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #3498db; }}
                .stat-label {{ color: #7f8c8d; margin-top: 10px; }}
                .section {{ background-color: white; padding: 30px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .status-badge {{ padding: 5px 10px; border-radius: 5px; color: white; font-weight: bold; }}
                .status-active {{ background-color: #27ae60; }}
                .status-inactive {{ background-color: #e74c3c; }}
                .history-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .history-table th, .history-table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                .history-table th {{ background-color: #34495e; color: white; }}
                .history-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🛰️ Deforestation Monitoring System</h1>
                <h2>Summary Report</h2>
                <p>Region: {status.get('config_region', 'Unknown')}</p>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary-grid">
                <div class="stat-card">
                    <div class="stat-number">{total_downloads}</div>
                    <div class="stat-label">Total Images Downloaded</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_processed}</div>
                    <div class="stat-label">Total Images Processed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_changes}</div>
                    <div class="stat-label">Changes Detected</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(download_history)}</div>
                    <div class="stat-label">Update Sessions</div>
                </div>
            </div>
            
            <div class="section">
                <h3>🔧 System Status</h3>
                <p>Pipeline Status: <span class="status-badge status-active">ACTIVE</span></p>
                <p>Scheduler Running: <span class="status-badge {'status-active' if status['scheduler_status']['is_running'] else 'status-inactive'}">
                   {'YES' if status['scheduler_status']['is_running'] else 'NO'}</span></p>
                <p>Google Earth Engine: <span class="status-badge {'status-active' if status['gee_available'] else 'status-inactive'}">
                   {'AVAILABLE' if status['gee_available'] else 'NOT AVAILABLE'}</span></p>
                <p>Update Interval: {status['scheduler_status']['update_interval_days']} days</p>
                <p>Check Time: {status['scheduler_status']['check_time']}</p>
            </div>
            
            <div class="section">
                <h3>📥 Recent Download Activity</h3>
                <table class="history-table">
                    <tr>
                        <th>Date</th>
                        <th>Images Downloaded</th>
                        <th>Status</th>
                    </tr>
        """
        
        # Add recent download history
        for entry in download_history[-10:]:  # Last 10 entries
            timestamp = entry.get('timestamp', 'Unknown')
            try:
                date_str = datetime.fromisoformat(timestamp.replace('Z', '')).strftime('%Y-%m-%d %H:%M')
            except:
                date_str = timestamp
            
            html_content += f"""
                    <tr>
                        <td>{date_str}</td>
                        <td>{entry.get('downloaded_count', 0)}</td>
                        <td>Success</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
            
            <div class="section">
                <h3>🔍 Recent Processing Activity</h3>
                <table class="history-table">
                    <tr>
                        <th>Date</th>
                        <th>Images Processed</th>
                        <th>Changes Detected</th>
                        <th>Status</th>
                    </tr>
        """
        
        # Add recent processing history
        for entry in processing_history[-10:]:  # Last 10 entries
            timestamp = entry.get('timestamp', 'Unknown')
            try:
                date_str = datetime.fromisoformat(timestamp.replace('Z', '')).strftime('%Y-%m-%d %H:%M')
            except:
                date_str = timestamp
            
            html_content += f"""
                    <tr>
                        <td>{date_str}</td>
                        <td>{entry.get('processed_count', 0)}</td>
                        <td>{entry.get('change_count', 0)}</td>
                        <td>{'Success' if not entry.get('errors') else 'Error'}</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
            
            <div class="section">
                <h3>📊 System Performance</h3>
                <p>This section would contain performance metrics and charts if implemented.</p>
                <ul>
                    <li>Average processing time per image</li>
                    <li>Change detection accuracy metrics</li>
                    <li>System resource usage</li>
                    <li>Error rates and reliability statistics</li>
                </ul>
            </div>
            
            <div class="section">
                <h3>⚠️ Recommendations</h3>
                <ul>
        """
        
        # Add recommendations based on system status
        if not status['gee_available']:
            html_content += "<li>Consider setting up Google Earth Engine for additional processing capabilities</li>"
        
        if not status['scheduler_status']['is_running']:
            html_content += "<li>Automated monitoring is not running - consider starting the scheduler</li>"
        
        if total_changes > 0:
            html_content += f"<li>⚠️ {total_changes} potential deforestation events detected - review and verify</li>"
        
        html_content += """
                    <li>Regularly backup processing results and metadata</li>
                    <li>Monitor system logs for errors and warnings</li>
                    <li>Verify satellite image quality before processing</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        # Save the HTML report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)


def main():
    """Main function for running the deforestation detection pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deforestation Detection Pipeline')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--download', action='store_true', help='Download latest images')
    parser.add_argument('--detect-changes', action='store_true', help='Perform change detection')
    parser.add_argument('--start-monitoring', action='store_true', help='Start automated monitoring')
    parser.add_argument('--stop-monitoring', action='store_true', help='Stop automated monitoring')
    parser.add_argument('--status', action='store_true', help='Show system status')
    parser.add_argument('--report', action='store_true', help='Generate summary report')
    parser.add_argument('--start-date', type=str, help='Start date for change detection (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date for change detection (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = DeforestationPipeline(args.config)
    
    try:
        if args.download:
            images = pipeline.download_latest_images()
            print(f"Downloaded {len(images)} images")
        
        elif args.detect_changes:
            if not args.start_date or not args.end_date:
                print("Error: --start-date and --end-date are required for change detection")
                return
            
            results = pipeline.detect_changes(args.start_date, args.end_date)
            print(f"Change detection completed: {results['status']}")
            print(f"Changes detected: {len(results['change_events'])}")
        
        elif args.start_monitoring:
            pipeline.start_monitoring()
            print("Automated monitoring started")
            print("Press Ctrl+C to stop monitoring")
            
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                pipeline.stop_monitoring()
                print("\nMonitoring stopped")
        
        elif args.stop_monitoring:
            pipeline.stop_monitoring()
            print("Monitoring stopped")
        
        elif args.status:
            status = pipeline.get_monitoring_status()
            print("System Status:")
            print(f"  Pipeline: {status['pipeline_status']}")
            print(f"  Scheduler Running: {status['scheduler_status']['is_running']}")
            print(f"  GEE Available: {status['gee_available']}")
            print(f"  Last Processed Images: {status['last_processed_images']}")
        
        elif args.report:
            report_path = pipeline.generate_summary_report()
            print(f"Summary report generated: {report_path}")
        
        else:
            print("No action specified. Use --help for available options.")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
