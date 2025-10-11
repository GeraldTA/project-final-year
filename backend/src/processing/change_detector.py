"""
Change detection algorithms for deforestation monitoring.

This module implements various change detection techniques to identify
deforestation and vegetation changes from time-series satellite imagery.
"""

import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import shape, Polygon
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import logging
from dataclasses import dataclass
from scipy import ndimage
from sklearn.cluster import KMeans
from skimage import morphology, measure
import sys

# Add utils to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.insert(0, str(src_dir))

from utils.logger import LoggerMixin, log_function_call
from utils.config import get_config


@dataclass
class ChangeEvent:
    """Data class for detected change events."""
    id: str
    date_detected: datetime
    area_hectares: float
    severity: str  # 'low', 'medium', 'high'
    confidence: float  # 0-1
    centroid: Tuple[float, float]  # (longitude, latitude)
    bounds: Dict[str, float]  # {'west', 'east', 'south', 'north'}
    change_type: str  # 'deforestation', 'degradation', 'regrowth'
    ndvi_change: float
    geometry: Any  # Shapely geometry


class ChangeDetector(LoggerMixin):
    """
    Change detection system for monitoring deforestation and vegetation changes.
    
    This class implements multiple change detection algorithms including
    NDVI differencing, time-series analysis, and machine learning approaches.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize change detector.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = get_config(config_path)
        self.output_dir = self.config.get_data_dir('processed_images')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Change detection parameters from config
        self.min_change_threshold = self.config.get('processing.change_detection.min_change_threshold', -0.3)
        self.min_change_area_pixels = self.config.get('processing.change_detection.min_change_area_pixels', 100)
        self.temporal_window_months = self.config.get('processing.change_detection.temporal_window_months', 6)
        
        self.logger.info("Change detector initialized")
    
    @log_function_call
    def detect_ndvi_changes(
        self,
        before_ndvi: np.ndarray,
        after_ndvi: np.ndarray,
        before_date: datetime,
        after_date: datetime,
        geotransform: Any = None,
        crs: Any = None
    ) -> Tuple[np.ndarray, List[ChangeEvent]]:
        """
        Detect changes using NDVI differencing approach.
        
        Args:
            before_ndvi: NDVI array from earlier time period
            after_ndvi: NDVI array from later time period
            before_date: Date of before image
            after_date: Date of after image
            geotransform: Geotransform for coordinate conversion
            crs: Coordinate reference system
            
        Returns:
            Tuple of (change mask array, list of ChangeEvent objects)
        """
        if before_ndvi.shape != after_ndvi.shape:
            raise ValueError("NDVI arrays must have the same shape")
        
        # Calculate NDVI difference (after - before)
        # Negative values indicate vegetation loss
        ndvi_diff = after_ndvi - before_ndvi
        
        # Create change mask for significant vegetation loss
        change_mask = (ndvi_diff < self.min_change_threshold) & \
                     (~np.isnan(before_ndvi)) & \
                     (~np.isnan(after_ndvi))
        
        # Apply morphological operations to reduce noise
        change_mask = self._clean_change_mask(change_mask)
        
        # Find connected components (change polygons)
        labeled_changes, num_changes = ndimage.label(change_mask)
        
        # Extract change events
        change_events = []
        for change_id in range(1, num_changes + 1):
            try:
                change_event = self._extract_change_event(
                    labeled_changes == change_id,
                    ndvi_diff,
                    change_id,
                    after_date,
                    geotransform,
                    crs
                )
                
                if change_event and change_event.area_hectares * 10000 >= self.min_change_area_pixels:  # Convert ha to pixels
                    change_events.append(change_event)
                    
            except Exception as e:
                self.logger.warning(f"Failed to extract change event {change_id}: {e}")
                continue
        
        self.logger.info(f"Detected {len(change_events)} change events between {before_date.date()} and {after_date.date()}")
        return change_mask, change_events
    
    def _clean_change_mask(self, change_mask: np.ndarray) -> np.ndarray:
        """Apply morphological operations to clean the change mask."""
        # Remove small isolated pixels (noise)
        cleaned = morphology.binary_opening(change_mask, morphology.disk(2))
        
        # Fill small holes
        cleaned = morphology.binary_closing(cleaned, morphology.disk(3))
        
        # Remove very small areas
        cleaned = morphology.remove_small_objects(cleaned, min_size=self.min_change_area_pixels)
        
        return cleaned
    
    def _extract_change_event(
        self,
        change_area: np.ndarray,
        ndvi_diff: np.ndarray,
        change_id: int,
        detection_date: datetime,
        geotransform: Any = None,
        crs: Any = None
    ) -> Optional[ChangeEvent]:
        """Extract change event information from a change area."""
        if not np.any(change_area):
            return None
        
        # Calculate area in pixels and convert to hectares
        area_pixels = np.sum(change_area)
        
        # Approximate conversion: assuming 10m resolution Sentinel-2 pixels
        # 1 pixel = 100 m², 1 hectare = 10,000 m²
        area_hectares = area_pixels * 100 / 10000
        
        # Calculate mean NDVI change in the area
        mean_ndvi_change = np.mean(ndvi_diff[change_area])
        
        # Determine change severity based on NDVI change magnitude
        if mean_ndvi_change < -0.5:
            severity = 'high'
        elif mean_ndvi_change < -0.3:
            severity = 'medium'
        else:
            severity = 'low'
        
        # Calculate confidence based on consistency of change
        ndvi_change_values = ndvi_diff[change_area]
        consistency = np.sum(ndvi_change_values < self.min_change_threshold) / len(ndvi_change_values)
        confidence = min(consistency, 1.0)
        
        # Find centroid
        y_coords, x_coords = np.where(change_area)
        centroid_y = np.mean(y_coords)
        centroid_x = np.mean(x_coords)
        
        # Convert to geographic coordinates if geotransform is provided
        if geotransform:
            centroid_lon = geotransform[0] + centroid_x * geotransform[1]
            centroid_lat = geotransform[3] + centroid_y * geotransform[5]
            
            # Calculate bounds
            min_x, max_x = np.min(x_coords), np.max(x_coords)
            min_y, max_y = np.min(y_coords), np.max(y_coords)
            
            west = geotransform[0] + min_x * geotransform[1]
            east = geotransform[0] + max_x * geotransform[1]
            north = geotransform[3] + min_y * geotransform[5]
            south = geotransform[3] + max_y * geotransform[5]
            
            bounds = {'west': west, 'east': east, 'south': south, 'north': north}
        else:
            centroid_lon, centroid_lat = centroid_x, centroid_y
            bounds = {
                'west': np.min(x_coords),
                'east': np.max(x_coords),
                'south': np.min(y_coords),
                'north': np.max(y_coords)
            }
        
        # Create geometry from change area
        geometry = self._create_change_geometry(change_area, geotransform)
        
        # Determine change type
        if mean_ndvi_change < -0.4:
            change_type = 'deforestation'
        elif mean_ndvi_change < -0.2:
            change_type = 'degradation'
        else:
            change_type = 'minor_change'
        
        return ChangeEvent(
            id=f"change_{detection_date.strftime('%Y%m%d')}_{change_id:04d}",
            date_detected=detection_date,
            area_hectares=area_hectares,
            severity=severity,
            confidence=confidence,
            centroid=(centroid_lon, centroid_lat),
            bounds=bounds,
            change_type=change_type,
            ndvi_change=mean_ndvi_change,
            geometry=geometry
        )
    
    def _create_change_geometry(self, change_area: np.ndarray, geotransform: Any = None) -> Any:
        """Create a Shapely geometry from the change area."""
        try:
            # Create a temporary raster profile for geometry extraction
            if geotransform is None:
                # Use pixel coordinates
                geotransform = (0, 1, 0, change_area.shape[0], 0, -1)
            
            # Extract polygons from the change area
            results = list(shapes(change_area.astype(np.uint8), transform=geotransform))
            
            if results:
                # Take the largest polygon if multiple exist
                largest_poly = max(results, key=lambda x: shape(x[0]).area)
                return shape(largest_poly[0])
            else:
                return None
                
        except Exception as e:
            self.logger.warning(f"Failed to create geometry: {e}")
            return None
    
    @log_function_call
    def detect_time_series_changes(
        self,
        ndvi_time_series: List[Tuple[np.ndarray, datetime]],
        geotransform: Any = None,
        crs: Any = None
    ) -> List[ChangeEvent]:
        """
        Detect changes using time-series analysis.
        
        Args:
            ndvi_time_series: List of (NDVI array, date) tuples sorted by date
            geotransform: Geotransform for coordinate conversion
            crs: Coordinate reference system
            
        Returns:
            List of ChangeEvent objects
        """
        if len(ndvi_time_series) < 2:
            raise ValueError("At least 2 time points required for time-series analysis")
        
        all_change_events = []
        
        # Detect changes between consecutive time periods
        for i in range(len(ndvi_time_series) - 1):
            before_ndvi, before_date = ndvi_time_series[i]
            after_ndvi, after_date = ndvi_time_series[i + 1]
            
            # Skip if images are too close in time
            time_diff = (after_date - before_date).days
            if time_diff < 30:  # Minimum 30 days between images
                continue
            
            change_mask, change_events = self.detect_ndvi_changes(
                before_ndvi, after_ndvi, before_date, after_date, geotransform, crs
            )
            
            all_change_events.extend(change_events)
        
        # Remove duplicate changes (same location, similar time)
        filtered_events = self._filter_duplicate_changes(all_change_events)
        
        self.logger.info(f"Time-series analysis detected {len(filtered_events)} unique change events")
        return filtered_events
    
    def _filter_duplicate_changes(
        self,
        change_events: List[ChangeEvent],
        spatial_threshold: float = 1000,  # meters
        temporal_threshold: int = 60  # days
    ) -> List[ChangeEvent]:
        """Filter out duplicate change events based on spatial and temporal proximity."""
        if not change_events:
            return []
        
        # Sort events by confidence (highest first)
        sorted_events = sorted(change_events, key=lambda x: x.confidence, reverse=True)
        
        filtered_events = []
        
        for event in sorted_events:
            is_duplicate = False
            
            for existing_event in filtered_events:
                # Check temporal proximity
                time_diff = abs((event.date_detected - existing_event.date_detected).days)
                
                # Check spatial proximity (rough distance between centroids)
                spatial_diff = np.sqrt(
                    (event.centroid[0] - existing_event.centroid[0]) ** 2 +
                    (event.centroid[1] - existing_event.centroid[1]) ** 2
                ) * 111000  # Rough conversion to meters
                
                if time_diff <= temporal_threshold and spatial_diff <= spatial_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered_events.append(event)
        
        return filtered_events
    
    @log_function_call
    def create_change_visualization(
        self,
        before_ndvi: np.ndarray,
        after_ndvi: np.ndarray,
        change_mask: np.ndarray,
        change_events: List[ChangeEvent],
        output_path: str,
        before_date: datetime,
        after_date: datetime
    ) -> None:
        """
        Create visualization of detected changes.
        
        Args:
            before_ndvi: NDVI array from before period
            after_ndvi: NDVI array from after period
            change_mask: Binary change detection mask
            change_events: List of detected change events
            output_path: Path to save visualization
            before_date: Date of before image
            after_date: Date of after image
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Plot 1: Before NDVI
        im1 = axes[0, 0].imshow(before_ndvi, cmap='RdYlGn', vmin=-1, vmax=1)
        axes[0, 0].set_title(f'NDVI Before\n{before_date.strftime("%Y-%m-%d")}')
        axes[0, 0].axis('off')
        plt.colorbar(im1, ax=axes[0, 0], shrink=0.8)
        
        # Plot 2: After NDVI
        im2 = axes[0, 1].imshow(after_ndvi, cmap='RdYlGn', vmin=-1, vmax=1)
        axes[0, 1].set_title(f'NDVI After\n{after_date.strftime("%Y-%m-%d")}')
        axes[0, 1].axis('off')
        plt.colorbar(im2, ax=axes[0, 1], shrink=0.8)
        
        # Plot 3: NDVI Difference
        ndvi_diff = after_ndvi - before_ndvi
        im3 = axes[1, 0].imshow(ndvi_diff, cmap='RdBu_r', vmin=-1, vmax=1)
        axes[1, 0].set_title('NDVI Change\n(After - Before)')
        axes[1, 0].axis('off')
        plt.colorbar(im3, ax=axes[1, 0], shrink=0.8)
        
        # Plot 4: Change Detection Results
        # Show NDVI difference with change areas highlighted
        change_overlay = np.ma.masked_where(~change_mask, np.ones_like(change_mask))
        
        axes[1, 1].imshow(ndvi_diff, cmap='RdBu_r', vmin=-1, vmax=1, alpha=0.7)
        axes[1, 1].imshow(change_overlay, cmap='Reds', alpha=0.8)
        axes[1, 1].set_title(f'Detected Changes\n({len(change_events)} events)')
        axes[1, 1].axis('off')
        
        # Add change event markers
        for event in change_events:
            y, x = event.centroid[1], event.centroid[0]
            # Convert geographic coordinates to pixel coordinates if needed
            axes[1, 1].plot(x, y, 'ro', markersize=8, markeredgecolor='white', markeredgewidth=2)
        
        plt.tight_layout()
        
        # Add summary text
        total_area = sum(event.area_hectares for event in change_events)
        summary_text = (
            f"Change Detection Summary:\n"
            f"Period: {before_date.strftime('%Y-%m-%d')} to {after_date.strftime('%Y-%m-%d')}\n"
            f"Total events detected: {len(change_events)}\n"
            f"Total area affected: {total_area:.1f} hectares\n"
            f"Severity distribution:\n"
            f"  High: {sum(1 for e in change_events if e.severity == 'high')}\n"
            f"  Medium: {sum(1 for e in change_events if e.severity == 'medium')}\n"
            f"  Low: {sum(1 for e in change_events if e.severity == 'low')}"
        )
        
        plt.figtext(0.02, 0.02, summary_text, fontsize=10, 
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Change visualization saved to: {output_path}")
    
    @log_function_call
    def export_change_events_to_geojson(
        self,
        change_events: List[ChangeEvent],
        output_path: str,
        crs: str = "EPSG:4326"
    ) -> None:
        """
        Export change events to GeoJSON format.
        
        Args:
            change_events: List of ChangeEvent objects
            output_path: Path to save GeoJSON file
            crs: Coordinate reference system
        """
        if not change_events:
            self.logger.warning("No change events to export")
            return
        
        # Create GeoDataFrame
        features = []
        
        for event in change_events:
            feature = {
                'geometry': event.geometry.__geo_interface__ if event.geometry else None,
                'properties': {
                    'id': event.id,
                    'date_detected': event.date_detected.isoformat(),
                    'area_hectares': event.area_hectares,
                    'severity': event.severity,
                    'confidence': event.confidence,
                    'change_type': event.change_type,
                    'ndvi_change': event.ndvi_change,
                    'centroid_lon': event.centroid[0],
                    'centroid_lat': event.centroid[1]
                }
            }
            features.append(feature)
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(features, crs=crs)
        
        # Save to GeoJSON
        gdf.to_file(output_path, driver='GeoJSON')
        
        self.logger.info(f"Change events exported to GeoJSON: {output_path}")
    
    @log_function_call
    def generate_change_report(
        self,
        change_events: List[ChangeEvent],
        output_path: str,
        region_name: str = "Study Area"
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive change detection report.
        
        Args:
            change_events: List of ChangeEvent objects
            output_path: Path to save report
            region_name: Name of the study region
            
        Returns:
            Dictionary with report statistics
        """
        if not change_events:
            report_data = {
                'total_events': 0,
                'total_area_hectares': 0,
                'severity_distribution': {'high': 0, 'medium': 0, 'low': 0},
                'change_type_distribution': {},
                'temporal_distribution': {},
                'confidence_stats': {'mean': 0, 'std': 0}
            }
        else:
            # Calculate statistics
            total_area = sum(event.area_hectares for event in change_events)
            
            severity_counts = {}
            for severity in ['high', 'medium', 'low']:
                severity_counts[severity] = sum(1 for e in change_events if e.severity == severity)
            
            change_type_counts = {}
            for event in change_events:
                change_type_counts[event.change_type] = change_type_counts.get(event.change_type, 0) + 1
            
            # Temporal distribution by month
            temporal_counts = {}
            for event in change_events:
                month_key = event.date_detected.strftime('%Y-%m')
                temporal_counts[month_key] = temporal_counts.get(month_key, 0) + 1
            
            # Confidence statistics
            confidences = [event.confidence for event in change_events]
            
            report_data = {
                'total_events': len(change_events),
                'total_area_hectares': total_area,
                'severity_distribution': severity_counts,
                'change_type_distribution': change_type_counts,
                'temporal_distribution': temporal_counts,
                'confidence_stats': {
                    'mean': np.mean(confidences),
                    'std': np.std(confidences),
                    'min': np.min(confidences),
                    'max': np.max(confidences)
                }
            }
        
        # Generate HTML report
        self._generate_html_report(report_data, change_events, output_path, region_name)
        
        self.logger.info(f"Change detection report generated: {output_path}")
        return report_data
    
    def _generate_html_report(
        self,
        report_data: Dict[str, Any],
        change_events: List[ChangeEvent],
        output_path: str,
        region_name: str
    ) -> None:
        """Generate HTML report from report data."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Deforestation Detection Report - {region_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .summary {{ background-color: #ecf0f1; padding: 20px; margin: 20px 0; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat-box {{ background-color: #3498db; color: white; padding: 15px; text-align: center; border-radius: 5px; }}
                .events-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .events-table th, .events-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .events-table th {{ background-color: #34495e; color: white; }}
                .severity-high {{ background-color: #e74c3c; color: white; }}
                .severity-medium {{ background-color: #f39c12; color: white; }}
                .severity-low {{ background-color: #f1c40f; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Deforestation Detection Report</h1>
                <h2>{region_name}</h2>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <h3>Executive Summary</h3>
                <div class="stats">
                    <div class="stat-box">
                        <h4>{report_data['total_events']}</h4>
                        <p>Total Events</p>
                    </div>
                    <div class="stat-box">
                        <h4>{report_data['total_area_hectares']:.1f}</h4>
                        <p>Total Area (ha)</p>
                    </div>
                    <div class="stat-box">
                        <h4>{report_data['confidence_stats']['mean']:.2f}</h4>
                        <p>Avg Confidence</p>
                    </div>
                </div>
            </div>
            
            <h3>Severity Distribution</h3>
            <ul>
                <li>High Severity: {report_data['severity_distribution']['high']} events</li>
                <li>Medium Severity: {report_data['severity_distribution']['medium']} events</li>
                <li>Low Severity: {report_data['severity_distribution']['low']} events</li>
            </ul>
            
            <h3>Change Type Distribution</h3>
            <ul>
        """
        
        for change_type, count in report_data['change_type_distribution'].items():
            html_content += f"<li>{change_type.replace('_', ' ').title()}: {count} events</li>"
        
        html_content += """
            </ul>
            
            <h3>Detected Events</h3>
            <table class="events-table">
                <tr>
                    <th>Event ID</th>
                    <th>Date</th>
                    <th>Area (ha)</th>
                    <th>Severity</th>
                    <th>Confidence</th>
                    <th>Change Type</th>
                    <th>NDVI Change</th>
                </tr>
        """
        
        for event in change_events[:50]:  # Limit to first 50 events
            severity_class = f"severity-{event.severity}"
            html_content += f"""
                <tr>
                    <td>{event.id}</td>
                    <td>{event.date_detected.strftime('%Y-%m-%d')}</td>
                    <td>{event.area_hectares:.2f}</td>
                    <td><span class="{severity_class}">{event.severity.upper()}</span></td>
                    <td>{event.confidence:.2f}</td>
                    <td>{event.change_type.replace('_', ' ').title()}</td>
                    <td>{event.ndvi_change:.3f}</td>
                </tr>
            """
        
        html_content += """
            </table>
        </body>
        </html>
        """
        
        # Save HTML report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
