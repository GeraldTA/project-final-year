"""
Google Earth Engine alternative for Sentinel-2 data access.
This processes data in the cloud without downloading large files.
"""

import ee
import requests
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
import sys

# Add utils to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(src_dir))

from src.utils.config import get_config
from src.utils.logger import LoggerMixin

class GEESentinelProcessor(LoggerMixin):
    """
    Google Earth Engine-based Sentinel-2 processor.
    Processes data in the cloud and downloads only results.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize GEE processor."""
        self.config = get_config(config_path)
        
        try:
            # Get project ID
            project_id_file = Path(__file__).parent / 'gee_project_id.txt'
            if project_id_file.exists():
                project_id = project_id_file.read_text().strip()
                ee.Initialize(project=project_id)
                self.logger.info(f"Google Earth Engine initialized with project: {project_id}")
            else:
                ee.Initialize()
                self.logger.info("Google Earth Engine initialized successfully")
        except Exception as e:
            self.logger.error(f"GEE initialization failed: {e}")
            self.logger.info("Please run: earthengine authenticate")
            raise
        
        # Setup output directory
        try:
            self.output_dir = self.config.get_data_dir('gee_results')
        except KeyError:
            # Fallback if gee_results not in config
            self.output_dir = Path('data/processed')
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_sentinel2_collection(
        self,
        start_date: str,
        end_date: str,
        max_cloud_cover: float = 20
    ) -> ee.ImageCollection:
        """
        Get Sentinel-2 image collection for the region.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_cloud_cover: Maximum cloud cover percentage
            
        Returns:
            Earth Engine ImageCollection
        """
        bounds = self.config.get_region_bounds()
        
        # Create region of interest
        roi = ee.Geometry.Rectangle([
            bounds['west'], bounds['south'],
            bounds['east'], bounds['north']
        ])
        
        # Get Sentinel-2 Surface Reflectance collection
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                     .filterDate(start_date, end_date)
                     .filterBounds(roi)
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_cloud_cover))
                     .sort('system:time_start', False))
        
        return collection
    
    def calculate_ndvi_timeseries(
        self,
        start_date: str,
        end_date: str,
        max_cloud_cover: float = 20
    ) -> Dict[str, Any]:
        """
        Calculate NDVI time series for the region.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_cloud_cover: Maximum cloud cover percentage
            
        Returns:
            Dictionary with NDVI statistics
        """
        collection = self.get_sentinel2_collection(start_date, end_date, max_cloud_cover)
        
        # Function to calculate NDVI
        def add_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return image.addBands(ndvi)
        
        # Calculate NDVI for each image
        collection_with_ndvi = collection.map(add_ndvi)
        
        # Get region bounds
        bounds = self.config.get_region_bounds()
        roi = ee.Geometry.Rectangle([
            bounds['west'], bounds['south'],
            bounds['east'], bounds['north']
        ])
        
        # Calculate mean NDVI for each image
        ndvi_timeseries = []
        
        image_list = collection_with_ndvi.limit(50).getInfo()['features']
        
        for img_info in image_list:
            img_id = img_info['id']
            img = ee.Image(img_id)
            
            # Get NDVI band
            ndvi = img.select('NDVI')
            
            # Calculate statistics
            stats = ndvi.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), '', True
                ).combine(
                    ee.Reducer.min(), '', True
                ).combine(
                    ee.Reducer.max(), '', True
                ),
                geometry=roi,
                scale=20,  # 20m resolution
                maxPixels=1e9
            ).getInfo()
            
            # Get image properties
            properties = img.getInfo()['properties']
            
            ndvi_timeseries.append({
                'date': properties.get('system:time_start'),
                'cloud_cover': properties.get('CLOUDY_PIXEL_PERCENTAGE'),
                'ndvi_mean': stats.get('NDVI_mean'),
                'ndvi_std': stats.get('NDVI_stdDev'),
                'ndvi_min': stats.get('NDVI_min'),
                'ndvi_max': stats.get('NDVI_max'),
                'image_id': img_id
            })
        
        return {
            'timeseries': ndvi_timeseries,
            'region': bounds,
            'processed_date': datetime.now().isoformat()
        }
    
    def detect_deforestation_changes(
        self,
        before_date: str,
        after_date: str,
        ndvi_threshold: float = -0.2
    ) -> Dict[str, Any]:
        """
        Detect potential deforestation by comparing NDVI before and after.
        
        Args:
            before_date: Date before potential deforestation (YYYY-MM-DD)
            after_date: Date after potential deforestation (YYYY-MM-DD)
            ndvi_threshold: NDVI change threshold for deforestation
            
        Returns:
            Change detection results
        """
        bounds = self.config.get_region_bounds()
        roi = ee.Geometry.Rectangle([
            bounds['west'], bounds['south'],
            bounds['east'], bounds['north']
        ])
        
        # Get before and after collections
        before_collection = self.get_sentinel2_collection(
            (datetime.fromisoformat(before_date) - timedelta(days=30)).strftime('%Y-%m-%d'),
            before_date,
            max_cloud_cover=30
        )
        
        after_collection = self.get_sentinel2_collection(
            after_date,
            (datetime.fromisoformat(after_date) + timedelta(days=30)).strftime('%Y-%m-%d'),
            max_cloud_cover=30
        )
        
        # Function to add NDVI
        def add_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return image.addBands(ndvi)
        
        # Calculate median NDVI for before and after periods
        before_ndvi = before_collection.map(add_ndvi).select('NDVI').median()
        after_ndvi = after_collection.map(add_ndvi).select('NDVI').median()
        
        # Calculate change
        ndvi_change = after_ndvi.subtract(before_ndvi)
        
        # Identify potential deforestation areas
        deforestation_mask = ndvi_change.lt(ndvi_threshold)
        
        # Calculate statistics
        change_stats = ndvi_change.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.stdDev(), '', True
            ).combine(
                ee.Reducer.min(), '', True
            ).combine(
                ee.Reducer.max(), '', True
            ),
            geometry=roi,
            scale=20,
            maxPixels=1e9
        ).getInfo()
        
        # Calculate deforestation area
        deforestation_area = deforestation_mask.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=20,
            maxPixels=1e9
        ).getInfo()
        
        return {
            'before_date': before_date,
            'after_date': after_date,
            'region': bounds,
            'change_statistics': change_stats,
            'deforestation_area_m2': deforestation_area.get('NDVI', 0),
            'deforestation_area_hectares': deforestation_area.get('NDVI', 0) / 10000,
            'threshold_used': ndvi_threshold,
            'processed_date': datetime.now().isoformat()
        }
    
    def export_ndvi_image(
        self,
        date: str,
        output_name: str = None
    ) -> str:
        """
        Export NDVI image to Google Drive.
        
        Args:
            date: Date to export (YYYY-MM-DD)
            output_name: Output file name
            
        Returns:
            Export task ID
        """
        if not output_name:
            output_name = f"ndvi_{date.replace('-', '_')}"
        
        # Get collection for the date
        collection = self.get_sentinel2_collection(
            date,
            (datetime.fromisoformat(date) + timedelta(days=1)).strftime('%Y-%m-%d'),
            max_cloud_cover=50
        )
        
        if collection.size().getInfo() == 0:
            raise ValueError(f"No images found for date {date}")
        
        # Get first image and calculate NDVI
        image = collection.first()
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        bounds = self.config.get_region_bounds()
        roi = ee.Geometry.Rectangle([
            bounds['west'], bounds['south'],
            bounds['east'], bounds['north']
        ])
        
        # Start export task
        task = ee.batch.Export.image.toDrive(
            image=ndvi,
            description=output_name,
            folder='deforestation_detection',
            region=roi,
            scale=10,  # 10m resolution
            crs='EPSG:4326',
            maxPixels=1e9
        )
        
        task.start()
        
        self.logger.info(f"Export task started: {task.id}")
        return task.id

    def create_ndvi_map_tiles(
        self,
        before_date: str = "2025-03-15",
        after_date: str = "2025-09-10"
    ) -> Dict[str, str]:
        """
        Create NDVI map tiles for visualization.
        
        Args:
            before_date: Before date for comparison (YYYY-MM-DD)
            after_date: After date for comparison (YYYY-MM-DD)
            
        Returns:
            Dictionary with tile URLs for before, after, and change maps
        """
        try:
            bounds = self.config.get_region_bounds()
            roi = ee.Geometry.Rectangle([
                bounds['west'], bounds['south'],
                bounds['east'], bounds['north']
            ])
            
            # Get before and after collections
            before_collection = self.get_sentinel2_collection(
                (datetime.fromisoformat(before_date) - timedelta(days=30)).strftime('%Y-%m-%d'),
                before_date,
                max_cloud_cover=30
            )
            
            after_collection = self.get_sentinel2_collection(
                after_date,
                (datetime.fromisoformat(after_date) + timedelta(days=30)).strftime('%Y-%m-%d'),
                max_cloud_cover=30
            )
            
            # Function to add NDVI
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            # Calculate median NDVI for before and after periods
            before_ndvi = before_collection.map(add_ndvi).select('NDVI').median().clip(roi)
            after_ndvi = after_collection.map(add_ndvi).select('NDVI').median().clip(roi)
            
            # Calculate change
            ndvi_change = after_ndvi.subtract(before_ndvi)
            
            # Visualization parameters
            ndvi_vis = {
                'min': 0,
                'max': 1,
                'palette': ['red', 'orange', 'yellow', 'yellowgreen', 'green']
            }
            
            change_vis = {
                'min': -0.5,
                'max': 0.5,
                'palette': ['red', 'orange', 'yellow', 'white', 'lightgreen', 'green']
            }
            
            # Get map IDs for tile URLs
            before_map = before_ndvi.getMapId(ndvi_vis)
            after_map = after_ndvi.getMapId(ndvi_vis)
            change_map = ndvi_change.getMapId(change_vis)
            
            tile_urls = {
                'ndvi_before': f"https://earthengine.googleapis.com/v1/{before_map['mapid']}/tiles/{{z}}/{{x}}/{{y}}",
                'ndvi_after': f"https://earthengine.googleapis.com/v1/{after_map['mapid']}/tiles/{{z}}/{{x}}/{{y}}",
                'ndvi_change': f"https://earthengine.googleapis.com/v1/{change_map['mapid']}/tiles/{{z}}/{{x}}/{{y}}"
            }
            
            self.logger.info("Successfully created NDVI map tiles")
            return tile_urls
            
        except Exception as e:
            self.logger.error(f"Failed to create map tiles: {e}")
            return {}


def test_gee_processor():
    """Test the GEE processor."""
    print("🌍 Testing Google Earth Engine Processor")
    print("=" * 50)
    
    try:
        processor = GEESentinelProcessor()
        
        # Test NDVI calculation
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        print(f"📊 Calculating NDVI timeseries from {start_date} to {end_date}")
        
        results = processor.calculate_ndvi_timeseries(start_date, end_date, max_cloud_cover=50)
        
        print(f"✅ Found {len(results['timeseries'])} images")
        
        if results['timeseries']:
            first_result = results['timeseries'][0]
            print(f"📸 Latest image NDVI: {first_result['ndvi_mean']:.3f}")
            print(f"☁️ Cloud cover: {first_result['cloud_cover']:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_gee_processor()
