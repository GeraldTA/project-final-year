"""
Post-Processing for ML Detection Results

STEP 8: Post-Processing
- Convert pixel predictions to geo-referenced polygons
- Calculate affected area (hectares)
- Attach GPS coordinates and dates
- Generate detection reports
"""

import numpy as np
import geopandas as gpd
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import unary_union
import rasterio
from rasterio.features import shapes
from pathlib import Path
import json
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DetectionPostProcessor:
    """
    Post-processes ML detection results into usable geographic data.
    
    STEP 8: Complete post-processing pipeline
    """
    
    def __init__(self, min_area_hectares: float = 0.5, simplify_tolerance: float = 0.0001):
        """
        Initialize post-processor.
        
        Args:
            min_area_hectares: Minimum area to consider (filters small detections)
            simplify_tolerance: Tolerance for polygon simplification
        """
        self.min_area_hectares = min_area_hectares
        self.simplify_tolerance = simplify_tolerance
        
        logger.info(f"Post-processor initialized: min_area={min_area_hectares}ha, "
                   f"simplify={simplify_tolerance}")
    
    def predictions_to_polygons(
        self,
        predictions: np.ndarray,
        confidence_map: np.ndarray,
        transform,
        confidence_threshold: float = 0.7
    ) -> List[Dict]:
        """
        Convert pixel predictions to georeferenced polygons.
        
        STEP 8: Convert pixel predictions into geo-referenced polygons
        
        Args:
            predictions: Array of pixel-wise class predictions (0=forest, 1=deforested)
            confidence_map: Array of confidence scores
            transform: Rasterio affine transform (maps pixels to coordinates)
            confidence_threshold: Minimum confidence to include
        
        Returns:
            List of polygon dictionaries with metadata
        """
        logger.info("Converting predictions to polygons...")
        
        # Create binary mask for high-confidence deforestation
        deforestation_mask = (predictions == 1) & (confidence_map >= confidence_threshold)
        
        # Extract shapes from mask
        polygon_data = []
        for geom, value in shapes(deforestation_mask.astype(np.uint8), transform=transform):
            if value == 1:  # Deforestation detected
                polygon = shape(geom)
                
                # Get confidence stats for this polygon
                # This is a simplified version - in practice, you'd extract per-polygon stats
                avg_confidence = float(np.mean(confidence_map[deforestation_mask]))
                
                polygon_data.append({
                    'geometry': polygon,
                    'confidence': avg_confidence,
                    'detection_class': 'deforested'
                })
        
        logger.info(f"Extracted {len(polygon_data)} deforestation polygons")
        return polygon_data
    
    def calculate_area_hectares(self, geometry) -> float:
        """
        Calculate area in hectares.
        
        STEP 8: Calculate area affected (hectares)
        
        Args:
            geometry: Shapely geometry (should be in a projected CRS)
        
        Returns:
            Area in hectares
        """
        # Area is in square meters for projected CRS
        # Convert to hectares (1 hectare = 10,000 m²)
        area_sqm = geometry.area
        area_hectares = area_sqm / 10000.0
        return area_hectares
    
    def extract_coordinates(self, geometry) -> Dict:
        """
        Extract GPS coordinates from geometry.
        
        STEP 8: Attach GPS coordinates
        
        Args:
            geometry: Shapely geometry
        
        Returns:
            Dictionary with centroid and bounds coordinates
        """
        centroid = geometry.centroid
        bounds = geometry.bounds  # (minx, miny, maxx, maxy)
        
        return {
            'centroid': {
                'latitude': centroid.y,
                'longitude': centroid.x
            },
            'bounds': {
                'south': bounds[1],
                'north': bounds[3],
                'west': bounds[0],
                'east': bounds[2]
            }
        }
    
    def create_detection_geodataframe(
        self,
        polygon_data: List[Dict],
        crs: str = 'EPSG:4326',
        detection_date: Optional[str] = None
    ) -> gpd.GeoDataFrame:
        """
        Create a GeoDataFrame from detection polygons.
        
        Args:
            polygon_data: List of polygon dictionaries
            crs: Coordinate reference system
            detection_date: Date of detection
        
        Returns:
            GeoDataFrame with all detection information
        """
        if not polygon_data:
            logger.warning("No polygons to process")
            return gpd.GeoDataFrame()
        
        # Extract geometries
        geometries = [p['geometry'] for p in polygon_data]
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame({
            'geometry': geometries,
            'confidence': [p['confidence'] for p in polygon_data],
            'detection_class': [p['detection_class'] for p in polygon_data]
        }, crs=crs)
        
        # Calculate areas
        # Project to equal-area CRS for accurate area calculation
        gdf_projected = gdf.to_crs('ESRI:54009')  # World Mollweide
        gdf['area_hectares'] = gdf_projected.geometry.apply(self.calculate_area_hectares)
        
        # Filter by minimum area
        gdf = gdf[gdf['area_hectares'] >= self.min_area_hectares].copy()
        logger.info(f"Filtered to {len(gdf)} polygons >= {self.min_area_hectares}ha")
        
        # Extract coordinates
        coords = gdf.geometry.apply(self.extract_coordinates)
        gdf['centroid_lat'] = coords.apply(lambda x: x['centroid']['latitude'])
        gdf['centroid_lon'] = coords.apply(lambda x: x['centroid']['longitude'])
        
        # Add metadata
        if detection_date is None:
            detection_date = datetime.now().isoformat()
        gdf['detection_date'] = detection_date
        gdf['detection_id'] = [f"DEFOR_{i+1}_{datetime.now().strftime('%Y%m%d')}" 
                               for i in range(len(gdf))]
        
        # Simplify geometries
        if self.simplify_tolerance > 0:
            gdf['geometry'] = gdf.geometry.simplify(self.simplify_tolerance)
        
        logger.info(f"Created GeoDataFrame with {len(gdf)} detections")
        logger.info(f"Total affected area: {gdf['area_hectares'].sum():.2f} hectares")
        
        return gdf
    
    def generate_detection_report(
        self,
        gdf: gpd.GeoDataFrame,
        output_path: str,
        include_metadata: Dict = None
    ) -> Dict:
        """
        Generate a comprehensive detection report.
        
        STEP 8 & 11: Results & Reporting
        
        Args:
            gdf: GeoDataFrame with detections
            output_path: Path to save report JSON
            include_metadata: Additional metadata to include
        
        Returns:
            Report dictionary
        """
        if gdf.empty:
            logger.warning("No detections to report")
            report = {
                'status': 'no_detections',
                'total_detections': 0,
                'total_area_hectares': 0,
                'timestamp': datetime.now().isoformat()
            }
        else:
            # Calculate statistics
            total_area = gdf['area_hectares'].sum()
            avg_confidence = gdf['confidence'].mean()
            
            # Create report
            report = {
                'status': 'detections_found',
                'summary': {
                    'total_detections': len(gdf),
                    'total_area_hectares': float(total_area),
                    'average_confidence': float(avg_confidence),
                    'min_area_hectares': float(gdf['area_hectares'].min()),
                    'max_area_hectares': float(gdf['area_hectares'].max()),
                    'median_area_hectares': float(gdf['area_hectares'].median())
                },
                'detections': [],
                'timestamp': datetime.now().isoformat()
            }
            
            # Add individual detections
            for idx, row in gdf.iterrows():
                detection = {
                    'id': row['detection_id'],
                    'coordinates': {
                        'latitude': float(row['centroid_lat']),
                        'longitude': float(row['centroid_lon'])
                    },
                    'area_hectares': float(row['area_hectares']),
                    'confidence': float(row['confidence']),
                    'detection_date': row['detection_date'],
                    'severity': self._calculate_severity(row['area_hectares'])
                }
                report['detections'].append(detection)
            
            # Add metadata
            if include_metadata:
                report['metadata'] = include_metadata
        
        # Save report
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Detection report saved to {output_path}")
        
        return report
    
    def _calculate_severity(self, area_hectares: float) -> str:
        """
        Calculate severity level based on affected area.
        
        Args:
            area_hectares: Area in hectares
        
        Returns:
            Severity level string
        """
        if area_hectares < 1:
            return 'low'
        elif area_hectares < 5:
            return 'medium'
        elif area_hectares < 20:
            return 'high'
        else:
            return 'critical'
    
    def save_detections(
        self,
        gdf: gpd.GeoDataFrame,
        output_dir: str,
        formats: List[str] = ['geojson', 'shapefile']
    ):
        """
        Save detections in multiple formats.
        
        Args:
            gdf: GeoDataFrame with detections
            output_dir: Output directory
            formats: List of formats to save ('geojson', 'shapefile', 'kml')
        """
        if gdf.empty:
            logger.warning("No detections to save")
            return
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save in requested formats
        if 'geojson' in formats:
            geojson_path = output_dir / f'detections_{timestamp}.geojson'
            gdf.to_file(geojson_path, driver='GeoJSON')
            logger.info(f"Saved GeoJSON to {geojson_path}")
        
        if 'shapefile' in formats:
            shp_path = output_dir / f'detections_{timestamp}.shp'
            gdf.to_file(shp_path, driver='ESRI Shapefile')
            logger.info(f"Saved Shapefile to {shp_path}")
        
        if 'kml' in formats:
            kml_path = output_dir / f'detections_{timestamp}.kml'
            gdf.to_file(kml_path, driver='KML')
            logger.info(f"Saved KML to {kml_path}")
        
        # Save coordinates as CSV
        csv_path = output_dir / f'detections_{timestamp}.csv'
        coords_df = gdf[['detection_id', 'centroid_lat', 'centroid_lon', 
                        'area_hectares', 'confidence', 'detection_date']].copy()
        coords_df.to_csv(csv_path, index=False)
        logger.info(f"Saved coordinates CSV to {csv_path}")
    
    def merge_detections(
        self,
        gdf: gpd.GeoDataFrame,
        buffer_distance: float = 0.001
    ) -> gpd.GeoDataFrame:
        """
        Merge nearby detections into larger zones.
        
        Args:
            gdf: GeoDataFrame with detections
            buffer_distance: Distance to buffer polygons before merging
        
        Returns:
            GeoDataFrame with merged detections
        """
        if gdf.empty or len(gdf) == 1:
            return gdf
        
        logger.info(f"Merging {len(gdf)} detections...")
        
        # Buffer slightly to connect nearby polygons
        buffered = gdf.geometry.buffer(buffer_distance)
        
        # Merge overlapping polygons
        merged = unary_union(buffered)
        
        # Remove buffer
        if buffer_distance > 0:
            merged = merged.buffer(-buffer_distance)
        
        # Convert to GeoDataFrame
        if isinstance(merged, Polygon):
            merged = [merged]
        elif isinstance(merged, MultiPolygon):
            merged = list(merged.geoms)
        
        merged_gdf = gpd.GeoDataFrame({
            'geometry': merged
        }, crs=gdf.crs)
        
        # Recalculate attributes
        merged_gdf_projected = merged_gdf.to_crs('ESRI:54009')
        merged_gdf['area_hectares'] = merged_gdf_projected.geometry.apply(
            self.calculate_area_hectares
        )
        
        coords = merged_gdf.geometry.apply(self.extract_coordinates)
        merged_gdf['centroid_lat'] = coords.apply(lambda x: x['centroid']['latitude'])
        merged_gdf['centroid_lon'] = coords.apply(lambda x: x['centroid']['longitude'])
        
        merged_gdf['detection_date'] = datetime.now().isoformat()
        merged_gdf['confidence'] = gdf['confidence'].mean()  # Average confidence
        merged_gdf['detection_id'] = [f"MERGED_{i+1}_{datetime.now().strftime('%Y%m%d')}" 
                                      for i in range(len(merged_gdf))]
        
        logger.info(f"Merged into {len(merged_gdf)} zones")
        logger.info(f"Total area: {merged_gdf['area_hectares'].sum():.2f} hectares")
        
        return merged_gdf


def create_post_processor(
    min_area_hectares: float = 0.5,
    simplify_tolerance: float = 0.0001
) -> DetectionPostProcessor:
    """Factory function to create a post-processor."""
    return DetectionPostProcessor(min_area_hectares, simplify_tolerance)


if __name__ == "__main__":
    # Test post-processing
    logging.basicConfig(level=logging.INFO)
    
    print("Post-processing module test...")
    processor = create_post_processor()
    print(f"Processor ready: min_area={processor.min_area_hectares}ha")
