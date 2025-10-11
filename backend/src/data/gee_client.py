"""
Google Earth Engine client for Sentinel-2 data access.

This module provides an alternative method to access Sentinel-2 imagery
using Google Earth Engine's Python API, offering additional processing
capabilities and easier cloud-based computation.
"""

import ee
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass
import sys

# Add utils to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.insert(0, str(src_dir))

from utils.logger import LoggerMixin, log_function_call
from utils.config import get_config


@dataclass
class GEEImage:
    """Data class for Google Earth Engine image metadata."""
    id: str
    date: datetime
    cloud_cover: float
    system_index: str
    image: 'ee.Image'
    bounds: Dict[str, float]


class GEEClient(LoggerMixin):
    """
    Google Earth Engine client for Sentinel-2 data access.
    
    This class handles authentication with GEE and provides methods to
    query and download Sentinel-2 imagery using Earth Engine's cloud
    computing platform.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Google Earth Engine client.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = get_config(config_path)
        self.service_account_key = self.config.get('apis.google_earth_engine.service_account_key')
        self.project_id = self.config.get('apis.google_earth_engine.project_id')
        
        # Initialize Earth Engine
        self._initialize_ee()
        
        # Get region of interest
        self.region = self._get_region_geometry()
        
        self.logger.info("Google Earth Engine client initialized")
    
    def _initialize_ee(self) -> None:
        """Initialize Google Earth Engine with authentication."""
        try:
            # Read project ID from file if not configured
            if not self.project_id:
                project_file = Path(__file__).parent.parent.parent / "gee_project_id.txt"
                if project_file.exists():
                    self.project_id = project_file.read_text().strip()
                    self.logger.info(f"Read GEE project ID from file: {self.project_id}")
            
            if self.service_account_key and os.path.exists(self.service_account_key):
                # Service account authentication
                credentials = ee.ServiceAccountCredentials(
                    email=None,  # Will be read from the key file
                    key_file=self.service_account_key
                )
                ee.Initialize(credentials, project=self.project_id)
                self.logger.info("Authenticated with GEE using service account")
                
            else:
                # Interactive authentication (for development)
                try:
                    ee.Initialize(project=self.project_id)
                    self.logger.info("Authenticated with GEE using stored credentials")
                except:
                    self.logger.info("Initializing GEE authentication...")
                    ee.Authenticate()
                    ee.Initialize(project=self.project_id)
                    self.logger.info("GEE authentication completed")
                    
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Earth Engine: {e}")
            raise
    
    def _get_region_geometry(self) -> ee.Geometry:
        """Get region of interest as Earth Engine geometry."""
        bounds = self.config.get_region_bounds()
        
        # Create polygon from bounds
        coords = [
            [bounds['west'], bounds['south']],
            [bounds['west'], bounds['north']],
            [bounds['east'], bounds['north']],
            [bounds['east'], bounds['south']],
            [bounds['west'], bounds['south']]
        ]
        
        return ee.Geometry.Polygon(coords)
    
    @log_function_call
    def get_sentinel2_collection(
        self,
        start_date: str,
        end_date: str,
        max_cloud_cover: Optional[float] = None
    ) -> ee.ImageCollection:
        """
        Get Sentinel-2 Surface Reflectance collection for the region and date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_cloud_cover: Maximum cloud cover percentage (0-100)
            
        Returns:
            Earth Engine ImageCollection
        """
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                     .filterBounds(self.region)
                     .filterDate(start_date, end_date))
        
        # Apply cloud cover filter if specified
        if max_cloud_cover is not None:
            collection = collection.filter(
                ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_cloud_cover)
            )
        
        # Sort by date (most recent first)
        collection = collection.sort('system:time_start', False)
        
        self.logger.info(f"Created Sentinel-2 collection for {start_date} to {end_date}")
        return collection
    
    @log_function_call
    def query_images(
        self,
        start_date: str,
        end_date: str,
        max_cloud_cover: Optional[float] = None,
        max_results: int = 100
    ) -> List[GEEImage]:
        """
        Query available Sentinel-2 images in the collection.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_cloud_cover: Maximum cloud cover percentage (0-100)
            max_results: Maximum number of results to return
            
        Returns:
            List of GEEImage objects
        """
        collection = self.get_sentinel2_collection(start_date, end_date, max_cloud_cover)
        
        # Limit the number of results
        collection = collection.limit(max_results)
        
        # Get image list
        image_list = collection.getInfo()['features']
        
        images = []
        for img_info in image_list:
            try:
                # Parse image metadata
                properties = img_info['properties']
                image_id = img_info['id']
                
                # Get Earth Engine image object
                ee_image = ee.Image(image_id)
                
                # Extract metadata
                date_ms = properties['system:time_start']
                date = datetime.fromtimestamp(date_ms / 1000)
                cloud_cover = properties.get('CLOUDY_PIXEL_PERCENTAGE', 0)
                system_index = properties['system:index']
                
                # Get image bounds
                bounds = self._get_image_bounds(ee_image)
                
                gee_image = GEEImage(
                    id=image_id,
                    date=date,
                    cloud_cover=cloud_cover,
                    system_index=system_index,
                    image=ee_image,
                    bounds=bounds
                )
                
                images.append(gee_image)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse image metadata: {e}")
                continue
        
        self.logger.info(f"Found {len(images)} images matching criteria")
        return images
    
    def _get_image_bounds(self, image: ee.Image) -> Dict[str, float]:
        """Get bounds of an Earth Engine image."""
        try:
            geometry = image.geometry()
            bounds = geometry.bounds().getInfo()['coordinates'][0]
            
            lons = [coord[0] for coord in bounds]
            lats = [coord[1] for coord in bounds]
            
            return {
                'west': min(lons),
                'east': max(lons),
                'south': min(lats),
                'north': max(lats)
            }
        except:
            # Fallback to region bounds
            return self.config.get_region_bounds()
    
    @log_function_call
    def download_image(
        self,
        gee_image: GEEImage,
        bands: Optional[List[str]] = None,
        scale: int = 10,
        format: str = 'GeoTIFF'
    ) -> str:
        """
        Download a single image from Google Earth Engine.
        
        Args:
            gee_image: GEEImage object to download
            bands: List of bands to download. If None, uses config default
            scale: Resolution in meters per pixel
            format: Export format ('GeoTIFF', 'TFRecord', etc.)
            
        Returns:
            Download URL for the image
        """
        if bands is None:
            bands = self.config.get('sentinel.bands', ['B2', 'B3', 'B4', 'B8'])
        
        # Select bands
        image = gee_image.image.select(bands)
        
        # Clip to region of interest
        image = image.clip(self.region)
        
        # Create export parameters
        export_params = {
            'image': image,
            'description': f'sentinel2_{gee_image.system_index}',
            'scale': scale,
            'region': self.region,
            'fileFormat': format,
            'maxPixels': 1e9
        }
        
        try:
            # Export to Google Drive (can be modified to export to Google Cloud Storage)
            task = ee.batch.Export.image.toDrive(**export_params)
            task.start()
            
            self.logger.info(f"Started export task for image {gee_image.id}")
            return task.id
            
        except Exception as e:
            self.logger.error(f"Failed to export image {gee_image.id}: {e}")
            raise
    
    @log_function_call
    def get_latest_image(self, days_back: int = 7) -> Optional[GEEImage]:
        """
        Get the latest available image from Google Earth Engine.
        
        Args:
            days_back: Number of days to look back for images
            
        Returns:
            GEEImage object for the latest image, or None if not found
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        max_cloud_cover = self.config.get('sentinel.max_cloud_cover')
        images = self.query_images(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            max_cloud_cover=max_cloud_cover,
            max_results=1
        )
        
        return images[0] if images else None
    
    @log_function_call
    def calculate_ndvi(self, gee_image: GEEImage) -> ee.Image:
        """
        Calculate NDVI for a Sentinel-2 image.
        
        Args:
            gee_image: GEEImage object
            
        Returns:
            Earth Engine image with NDVI band
        """
        # Select NIR (B8) and Red (B4) bands
        nir = gee_image.image.select('B8')
        red = gee_image.image.select('B4')
        
        # Calculate NDVI: (NIR - Red) / (NIR + Red)
        ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
        
        return ndvi
    
    @log_function_call
    def mask_clouds(self, gee_image: GEEImage) -> ee.Image:
        """
        Apply cloud mask to Sentinel-2 image using SCL band.
        
        Args:
            gee_image: GEEImage object
            
        Returns:
            Cloud-masked Earth Engine image
        """
        # Get Scene Classification Layer (SCL)
        scl = gee_image.image.select('SCL')
        
        # Create cloud mask (SCL values: 3=cloud shadows, 8=medium clouds, 9=high clouds, 10=cirrus)
        cloud_mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
        
        # Apply mask
        masked_image = gee_image.image.updateMask(cloud_mask)
        
        return masked_image
    
    @log_function_call
    def create_composite(
        self,
        start_date: str,
        end_date: str,
        max_cloud_cover: Optional[float] = None
    ) -> ee.Image:
        """
        Create a cloud-free composite image for the specified time period.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_cloud_cover: Maximum cloud cover percentage per image
            
        Returns:
            Composite Earth Engine image
        """
        collection = self.get_sentinel2_collection(start_date, end_date, max_cloud_cover)
        
        # Apply cloud masking to each image
        def mask_clouds_func(image):
            scl = image.select('SCL')
            cloud_mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
            return image.updateMask(cloud_mask)
        
        masked_collection = collection.map(mask_clouds_func)
        
        # Create median composite
        composite = masked_collection.median().clip(self.region)
        
        self.logger.info(f"Created composite image for {start_date} to {end_date}")
        return composite
    
    @log_function_call
    def detect_changes(
        self,
        before_start: str,
        before_end: str,
        after_start: str,
        after_end: str,
        threshold: float = -0.3
    ) -> ee.Image:
        """
        Detect changes between two time periods using NDVI difference.
        
        Args:
            before_start: Start date for 'before' period (YYYY-MM-DD)
            before_end: End date for 'before' period (YYYY-MM-DD)
            after_start: Start date for 'after' period (YYYY-MM-DD)
            after_end: End date for 'after' period (YYYY-MM-DD)
            threshold: Change threshold (negative values indicate vegetation loss)
            
        Returns:
            Change detection image
        """
        # Create composites for before and after periods
        before_composite = self.create_composite(before_start, before_end)
        after_composite = self.create_composite(after_start, after_end)
        
        # Calculate NDVI for both periods
        before_ndvi = before_composite.normalizedDifference(['B8', 'B4']).rename('NDVI_before')
        after_ndvi = after_composite.normalizedDifference(['B8', 'B4']).rename('NDVI_after')
        
        # Calculate NDVI difference (after - before)
        ndvi_diff = after_ndvi.subtract(before_ndvi).rename('NDVI_change')
        
        # Create change mask (areas with significant vegetation loss)
        change_mask = ndvi_diff.lt(threshold).rename('deforestation_mask')
        
        # Combine results
        change_image = ee.Image.cat([
            before_ndvi,
            after_ndvi,
            ndvi_diff,
            change_mask
        ])
        
        self.logger.info(f"Change detection completed for periods {before_start}-{before_end} vs {after_start}-{after_end}")
        return change_image
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of an Earth Engine export task.
        
        Args:
            task_id: Task ID returned from export operation
            
        Returns:
            Task status information
        """
        try:
            tasks = ee.batch.Task.list()
            for task in tasks:
                if task.id == task_id:
                    return {
                        'id': task.id,
                        'state': task.state,
                        'description': task.config.get('description', ''),
                        'creation_time': task.creation_timestamp_ms,
                        'start_time': task.start_timestamp_ms,
                        'update_time': task.update_timestamp_ms
                    }
            
            return {'error': 'Task not found'}
            
        except Exception as e:
            self.logger.error(f"Failed to get task status: {e}")
            return {'error': str(e)}
