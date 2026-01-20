"""
Grid-based deforestation scanner for area analysis.
Divides a region into grid cells and detects deforestation in each cell.
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class GridCell:
    """Represents a single grid cell in the scan area."""
    id: str
    center_lat: float
    center_lng: float
    west: float
    south: float
    east: float
    north: float
    deforestation_detected: bool = False
    forest_drop: float = 0.0
    ndvi_drop: float = 0.0
    before_forest_prob: float = 0.0
    after_forest_prob: float = 0.0
    before_image_file: str = None
    after_image_file: str = None
    error: str = None


def create_grid(west: float, south: float, east: float, north: float, 
                grid_size: int = 3) -> List[GridCell]:
    """
    Divide a bounding box into a grid of cells.
    
    Args:
        west, south, east, north: Bounding box coordinates
        grid_size: Number of cells in each direction (e.g., 3 = 3x3 = 9 cells)
    
    Returns:
        List of GridCell objects
    """
    lat_step = (north - south) / grid_size
    lng_step = (east - west) / grid_size
    
    cells = []
    cell_id = 0
    
    for i in range(grid_size):
        for j in range(grid_size):
            cell_south = south + (i * lat_step)
            cell_north = cell_south + lat_step
            cell_west = west + (j * lng_step)
            cell_east = cell_west + lng_step
            
            cell = GridCell(
                id=f"cell_{cell_id}",
                center_lat=(cell_south + cell_north) / 2,
                center_lng=(cell_west + cell_east) / 2,
                west=cell_west,
                south=cell_south,
                east=cell_east,
                north=cell_north
            )
            cells.append(cell)
            cell_id += 1
    
    logger.info(f"Created {len(cells)} grid cells ({grid_size}x{grid_size})")
    return cells


async def scan_grid_for_deforestation(
    cells: List[GridCell],
    before_date: str,
    after_date: str,
    detector,
    export_function,
    window_days: int = 30,
    max_cloud_cover: float = 50.0,
    dimensions: int = 256
) -> List[GridCell]:
    """
    Scan each grid cell for deforestation.
    
    Args:
        cells: List of GridCell objects to scan
        before_date: Before date (YYYY-MM-DD) - this is the END of the before window
        after_date: After date (YYYY-MM-DD) - this is the END of the after window
        detector: ML detector instance
        export_function: Function to export satellite images
        window_days: Composite window in days (will go backwards from the dates)
        max_cloud_cover: Max cloud cover percentage
        dimensions: Export image size
    
    Returns:
        List of GridCell objects with detection results
    """
    from src.ml.gee_export import Bounds
    from pathlib import Path
    from datetime import datetime, timedelta
    
    export_dir = Path("data/raw/gee_exports")
    results = []
    
    # Calculate date ranges for the composite windows
    before_end = datetime.fromisoformat(before_date)
    before_start = (before_end - timedelta(days=window_days)).strftime("%Y-%m-%d")
    before_end_str = before_end.strftime("%Y-%m-%d")
    
    after_end = datetime.fromisoformat(after_date)
    after_start = (after_end - timedelta(days=window_days)).strftime("%Y-%m-%d")
    after_end_str = after_end.strftime("%Y-%m-%d")
    
    logger.info(f"Before window: {before_start} to {before_end_str}")
    logger.info(f"After window: {after_start} to {after_end_str}")
    
    for idx, cell in enumerate(cells):
        logger.info(f"Scanning cell {idx + 1}/{len(cells)}: {cell.id}")
        
        try:
            bounds = Bounds(
                west=cell.west,
                south=cell.south,
                east=cell.east,
                north=cell.north
            )
            
            # Export before image
            before_export = export_function(
                bounds=bounds,
                start_date=before_start,
                end_date=before_end_str,
                output_dir=export_dir,
                max_cloud_cover=max_cloud_cover,
                dimensions=dimensions,
                force=False
            )
            
            logger.info(f"Before export result: {before_export}")
            
            # Export after image
            after_export = export_function(
                bounds=bounds,
                start_date=after_start,
                end_date=after_end_str,
                output_dir=export_dir,
                max_cloud_cover=max_cloud_cover,
                dimensions=dimensions,
                force=False
            )
            
            logger.info(f"After export result: {after_export}")
            
            # Run detection
            result = detector.detect_change_from_files(
                before_image=before_export["path"],
                after_image=after_export["path"],
                before_date=before_date,
                after_date=after_date
            )
            
            # Store image filenames (just the filename, not full path)
            before_path = before_export.get("path", "")
            after_path = after_export.get("path", "")
            
            if before_path:
                cell.before_image_file = Path(before_path).name
                logger.info(f"Stored before_image_file: {cell.before_image_file}")
            else:
                logger.warning(f"No before_path in export result!")
                
            if after_path:
                cell.after_image_file = Path(after_path).name
                logger.info(f"Stored after_image_file: {cell.after_image_file}")
            else:
                logger.warning(f"No after_path in export result!")
            
            # Update cell with results
            cell.deforestation_detected = result.get("deforestation_detected", False)
            cell.forest_drop = result.get("change", {}).get("forest_drop", 0.0)
            cell.ndvi_drop = result.get("change", {}).get("ndvi_drop", 0.0)
            cell.before_forest_prob = result.get("before", {}).get("forest_probability", 0.0)
            cell.after_forest_prob = result.get("after", {}).get("forest_probability", 0.0)
            
            logger.info(
                f"Cell {cell.id}: deforestation={cell.deforestation_detected}, "
                f"forest_drop={cell.forest_drop:.3f}"
            )
            
        except Exception as e:
            logger.error(f"Error scanning cell {cell.id}: {e}")
            cell.error = str(e)
        
        results.append(cell)
    
    # Summary
    deforested_count = sum(1 for c in results if c.deforestation_detected)
    logger.info(
        f"Scan complete: {deforested_count}/{len(results)} cells "
        f"show deforestation"
    )
    
    return results
