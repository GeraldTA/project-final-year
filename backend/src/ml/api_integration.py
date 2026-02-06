"""
ML API Integration

STEP 9: Backend Integration
Exposes ML detection endpoints for the frontend
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import logging
from typing import Optional, List
import json
from datetime import datetime
import numpy as np

# Import ML modules
from src.ml.bigearthnet_detector import BigEarthNetForestChangeDetector, BIGEARTHNET_REPO_ID
from src.ml.gee_export import Bounds, export_s2_10band_geotiff

logger = logging.getLogger(__name__)

# Create router
ml_router = APIRouter(prefix="/api/ml", tags=["Machine Learning"])

# Global detector instance (loaded on startup)
detector: Optional[BigEarthNetForestChangeDetector] = None
post_processor = None

# Paths
MODEL_PATH = Path("models/best_model.pth")
DETECTIONS_DIR = Path("data/ml_detections")
DETECTIONS_DIR.mkdir(parents=True, exist_ok=True)


def initialize_ml_system():
    """
    Initialize the ML detection system.
    Called on app startup.
    """
    global detector, post_processor

    try:
        # Factory-ready path: use pretrained BigEarthNet weights (download on first run).
        logger.info("Initializing BigEarthNet pretrained detector (%s)...", BIGEARTHNET_REPO_ID)
        detector = BigEarthNetForestChangeDetector(
            forest_drop_threshold=0.20,
            min_forest_before=0.40,
            max_forest_after=0.30,
            ndvi_drop_threshold=0.10,
        )
        post_processor = None
        logger.info("✓ ML system initialized successfully (BigEarthNet)")
    except Exception as e:
        logger.error(f"Failed to initialize ML system: {e}")
        detector = None
        post_processor = None


@ml_router.get("/status")
async def ml_status():
    """
    Get ML system status.
    
    Returns status of model loading and availability.
    """
    return {
        "model_loaded": detector is not None,
        "model_type": "bigearthnet-resnet50-s2" if detector is not None else None,
        "pretrained_repo": BIGEARTHNET_REPO_ID,
        "local_trained_model_path": str(MODEL_PATH),
        "local_trained_model_exists": MODEL_PATH.exists(),
        "timestamp": datetime.now().isoformat(),
    }


@ml_router.post("/run-ml-detection")
async def run_ml_detection(
    image_path: str = Query(..., description="Path to Sentinel-2 image file"),
    return_geojson: bool = Query(False, description="Return GeoJSON of detections")
):
    """
    Run ML-based deforestation detection on a Sentinel-2 image.
    
    STEP 9: API endpoint /run-ml-detection
    
    Args:
        image_path: Path to the image file
        return_geojson: Whether to return detailed GeoJSON
    
    Returns:
        Detection results with coordinates, confidence, and NDVI changes
    """
    if detector is None:
        raise HTTPException(status_code=503, detail="ML model not loaded")
    
    try:
        logger.info(f"Running ML detection on {image_path}")
        
        # Run detection
        result = detector.predict_from_file(image_path)
        
        # STEP 9: API response format
        response = {
            "status": "success",
            "prediction": "Forest" if result["forest_probability"] >= 0.5 else "Non-Forest",
            "forest_probability": result["forest_probability"],
            "coordinates": {
                "latitude": None,  # Would be extracted from image metadata
                "longitude": None
            },
            "ndvi_mean": result.get('ndvi_mean'),
            "detection_date": result['timestamp'],
            "image_path": image_path
        }

        # Include bbox for mapping if available
        if result.get("bbox_wgs84"):
            response["bbox_wgs84"] = result["bbox_wgs84"]

        # Optional: include per-class probabilities
        response["class_probabilities"] = result.get("class_probabilities", {})
        
        # Save result
        result_file = DETECTIONS_DIR / f"detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w') as f:
            json.dump(response, f, indent=2)
        
        logger.info(
            "Detection complete: forest_probability=%.3f ndvi=%.3f",
            response["forest_probability"],
            response.get("ndvi_mean") if response.get("ndvi_mean") is not None else float("nan"),
        )
        
        return response
        
    except Exception as e:
        logger.error(f"ML detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.post("/detect-change")
async def detect_change(
    before_image: str = Query(..., description="Path to before image"),
    after_image: str = Query(..., description="Path to after image"),
    before_date: str = Query(..., description="Date of before image (YYYY-MM-DD)"),
    after_date: str = Query(..., description="Date of after image (YYYY-MM-DD)")
):
    """
    Detect deforestation change between two time periods.
    
    STEP 9: Change detection endpoint
    
    Returns:
        Change detection results with before/after comparison
    """
    if detector is None:
        raise HTTPException(status_code=503, detail="ML model not loaded")
    
    try:
        logger.info(f"Running change detection: {before_date} -> {after_date}")
        
        response = detector.detect_change_from_files(
            before_image=before_image,
            after_image=after_image,
            before_date=before_date,
            after_date=after_date,
        )

        logger.info(
            "Change detection: deforestation=%s forest_drop=%.3f",
            response.get("deforestation_detected"),
            response.get("change", {}).get("forest_drop", float("nan")),
        )

        return response
        
    except Exception as e:
        logger.error(f"Change detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def detect_change_auto_internal(
    before_date: str,
    after_date: str,
    west: float,
    south: float,
    east: float,
    north: float,
    window_days: int = 30,
    max_cloud_cover: float = 30.0,
    scale: int = 10,
    dimensions: int = 512,
    force_download: bool = False,
    ignore_seasonal_check: bool = False,
):
    """Internal function for change detection - can be called from Python code.
    
    This is the actual implementation that can be safely called from other Python modules.
    """
    if detector is None:
        raise ValueError("ML model not loaded")

    try:
        # Lazy import to avoid pulling EE at FastAPI startup.
        from datetime import timedelta

        bounds = Bounds(west=west, south=south, east=east, north=north)
        export_dir = Path("data/raw/gee_exports")
        
        # Seasonal validation: warn if dates are from different seasons
        before_dt = datetime.fromisoformat(before_date)
        after_dt = datetime.fromisoformat(after_date)
        month_diff = abs((after_dt.month - before_dt.month) + 12 * (after_dt.year - before_dt.year))
        
        seasonal_warning = None
        if not ignore_seasonal_check and month_diff > 1:
            seasonal_warning = (
                f"WARNING: Comparing dates from different seasons (month diff={month_diff}). "
                "This may produce false positives due to natural vegetation cycles. "
                "For accurate deforestation detection, compare same-season images (e.g., Jan→Jan or Jun→Jun)."
            )
            logger.warning(seasonal_warning)

        # Create date ranges: center the window around the specified dates
        # For before_date, look back from that date
        before_start = (datetime.fromisoformat(before_date) - timedelta(days=window_days)).strftime("%Y-%m-%d")
        before_end = before_date
        # For after_date, look forward from that date  
        after_start = after_date
        after_end = (datetime.fromisoformat(after_date) + timedelta(days=window_days)).strftime("%Y-%m-%d")

        logger.info(
            "Auto-exporting Sentinel-2 composites: before=%s..%s (centered on %s) after=%s..%s (centered on %s)",
            before_start,
            before_end,
            before_date,
            after_start,
            after_end,
            after_date,
        )

        before_export = export_s2_10band_geotiff(
            bounds=bounds,
            start_date=before_start,
            end_date=before_end,
            output_dir=export_dir,
            max_cloud_cover=max_cloud_cover,
            scale=scale,
            dimensions=dimensions,
            force=force_download,
        )
        after_export = export_s2_10band_geotiff(
            bounds=bounds,
            start_date=after_start,
            end_date=after_end,
            output_dir=export_dir,
            max_cloud_cover=max_cloud_cover,
            scale=scale,
            dimensions=dimensions,
            force=force_download,
        )

        response = detector.detect_change_from_files(
            before_image=before_export["path"],
            after_image=after_export["path"],
            before_date=before_date,
            after_date=after_date,
        )

        response["inputs"] = {
            "bounds": bounds.__dict__,
            "window_days": window_days,
            "max_cloud_cover": max_cloud_cover,
            "scale": scale,
            "dimensions": dimensions,
        }
        response["exports"] = {
            "before": before_export,
            "after": after_export,
        }
        
        if seasonal_warning:
            response["seasonal_warning"] = seasonal_warning
            response["month_difference"] = month_diff
        
        return response

    except Exception as e:
        logger.error(f"Auto change detection failed: {e}")
        raise ValueError(str(e))


@ml_router.post("/detect-change-auto")
async def detect_change_auto(
    before_date: str = Query(..., description="Before date (YYYY-MM-DD)"),
    after_date: str = Query(..., description="After date (YYYY-MM-DD)"),
    west: float = Query(..., description="Bounding box west (lng)"),
    south: float = Query(..., description="Bounding box south (lat)"),
    east: float = Query(..., description="Bounding box east (lng)"),
    north: float = Query(..., description="Bounding box north (lat)"),
    window_days: int = Query(30, ge=1, le=90, description="Composite window in days"),
    max_cloud_cover: float = Query(30.0, ge=0.0, le=100.0, description="Max cloud cover %"),
    scale: int = Query(10, ge=10, le=60, description="Export pixel size in meters"),
    dimensions: int = Query(512, ge=64, le=2048, description="Export image size in pixels (square)"),
    force_download: bool = Query(False, description="Ignore cache and re-download"),
    ignore_seasonal_check: bool = Query(False, description="Skip seasonal comparison validation"),
):
    """HTTP endpoint for change detection without file paths.

    Automatically creates two 10-band GeoTIFFs from Earth Engine (cached locally),
    then runs BigEarthNet forest-probability change detection.
    
    IMPORTANT: To avoid false positives from seasonal vegetation changes,
    before and after dates should be from the same season (ideally same month ±30 days).
    """
    try:
        return await detect_change_auto_internal(
            before_date=before_date,
            after_date=after_date,
            west=west,
            south=south,
            east=east,
            north=north,
            window_days=window_days,
            max_cloud_cover=max_cloud_cover,
            scale=scale,
            dimensions=dimensions,
            force_download=force_download,
            ignore_seasonal_check=ignore_seasonal_check,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Auto change detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.post("/run-ml-detection-auto")
async def run_ml_detection_auto(
    date: str = Query(..., description="Date (YYYY-MM-DD)"),
    west: float = Query(..., description="Bounding box west (lng)"),
    south: float = Query(..., description="Bounding box south (lat)"),
    east: float = Query(..., description="Bounding box east (lng)"),
    north: float = Query(..., description="Bounding box north (lat)"),
    window_days: int = Query(15, ge=1, le=60, description="Composite window in days"),
    max_cloud_cover: float = Query(30.0, ge=0.0, le=100.0, description="Max cloud cover %"),
    scale: int = Query(10, ge=10, le=60, description="Export pixel size in meters"),
    dimensions: int = Query(512, ge=64, le=2048, description="Export image size in pixels (square)"),
    force_download: bool = Query(False, description="Ignore cache and re-download"),
):
    """Single-date inference without file paths."""
    if detector is None:
        raise HTTPException(status_code=503, detail="ML model not loaded")

    try:
        from datetime import timedelta

        bounds = Bounds(west=west, south=south, east=east, north=north)
        export_dir = Path("data/raw/gee_exports")

        start_date = (datetime.fromisoformat(date) - timedelta(days=window_days)).strftime("%Y-%m-%d")
        end_date = (datetime.fromisoformat(date) + timedelta(days=window_days)).strftime("%Y-%m-%d")

        export = export_s2_10band_geotiff(
            bounds=bounds,
            start_date=start_date,
            end_date=end_date,
            output_dir=export_dir,
            max_cloud_cover=max_cloud_cover,
            scale=scale,
            dimensions=dimensions,
            force=force_download,
        )

        result = detector.predict_from_file(export["path"])
        return {
            "status": "success",
            "date": date,
            "inputs": {"bounds": bounds.__dict__, "window_days": window_days, "max_cloud_cover": max_cloud_cover, "scale": scale, "dimensions": dimensions},
            "export": export,
            "result": result,
        }

    except Exception as e:
        logger.error(f"Auto ML detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.get("/detections/recent")
async def get_recent_detections(limit: int = Query(50, le=500)):
    """
    Get recent ML detections.
    
    Returns:
        List of recent detection results
    """
    try:
        # Load detection files
        detection_files = sorted(
            DETECTIONS_DIR.glob("detection_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:limit]
        
        detections = []
        for file_path in detection_files:
            with open(file_path, 'r') as f:
                detection = json.load(f)
                detections.append(detection)
        
        return {
            "count": len(detections),
            "detections": detections,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to load detections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.get("/model/info")
async def get_model_info():
    """
    Get information about the loaded ML model.
    
    Returns:
        Model architecture and parameters info
    """
    if detector is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        model_info = {
            "architecture": "ResNet-50",
            "input_channels": detector.model.input_channels,
            "num_classes": detector.model.num_classes,
            "total_parameters": detector.model.get_num_total_params(),
            "trainable_parameters": detector.model.get_num_trainable_params(),
            "confidence_threshold": detector.confidence_threshold,
            "ndvi_drop_threshold": detector.ndvi_drop_threshold,
            "device": str(detector.device),
            "model_path": str(MODEL_PATH)
        }
        
        return model_info
        
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.get("/statistics")
async def get_ml_statistics():
    """
    Get ML detection statistics.
    
    Returns:
        Statistics about ML detections
    """
    try:
        # Load all detection files
        detection_files = list(DETECTIONS_DIR.glob("detection_*.json"))
        
        if not detection_files:
            return {
                "total_detections": 0,
                "deforested_count": 0,
                "forest_count": 0,
                "average_confidence": 0
            }
        
        deforested = 0
        forest = 0
        confidences = []
        
        for file_path in detection_files:
            with open(file_path, 'r') as f:
                detection = json.load(f)
                if detection['prediction'] == 'Deforested':
                    deforested += 1
                else:
                    forest += 1
                confidences.append(detection['confidence'])
        
        return {
            "total_detections": len(detection_files),
            "deforested_count": deforested,
            "forest_count": forest,
            "deforestation_rate": deforested / len(detection_files) * 100,
            "average_confidence": sum(confidences) / len(confidences),
            "min_confidence": min(confidences),
            "max_confidence": max(confidences)
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.post("/scan-area-grid")
async def scan_area_grid(
    location_name: str = Query(..., description="Name of the location to scan"),
    west: float = Query(..., description="Bounding box west"),
    south: float = Query(..., description="Bounding box south"),
    east: float = Query(..., description="Bounding box east"),
    north: float = Query(..., description="Bounding box north"),
    before_date: str = Query(..., description="Before date (YYYY-MM-DD)"),
    after_date: str = Query(..., description="After date (YYYY-MM-DD)"),
    grid_size: int = Query(3, ge=2, le=5, description="Grid dimensions (2-5)"),
    window_days: int = Query(30, ge=7, le=90, description="Composite window"),
    max_cloud_cover: float = Query(50.0, ge=0.0, le=100.0, description="Max cloud %"),
    dimensions: int = Query(256, ge=64, le=512, description="Export size")
):
    """
    Scan an area using a grid and mark cells with deforestation.
    Returns grid cells with detection results and image paths for visualization.
    """
    if detector is None:
        raise HTTPException(status_code=503, detail="ML model not loaded")
    
    try:
        from src.ml.grid_scanner import create_grid, scan_grid_for_deforestation, GridCell
        from datetime import timedelta
        
        logger.info(
            f"Starting grid scan for {location_name}: "
            f"{grid_size}x{grid_size} grid, dates {before_date} to {after_date}"
        )
        
        # Create grid cells
        cells = create_grid(west, south, east, north, grid_size)
        
        # Don't adjust dates here - the scanner will create the proper windows
        # Just pass the target dates directly
        
        # Scan each cell
        from src.ml.gee_export import export_s2_10band_geotiff
        
        results = await scan_grid_for_deforestation(
            cells=cells,
            before_date=before_date,
            after_date=after_date,
            detector=detector,
            export_function=export_s2_10band_geotiff,
            window_days=window_days,
            max_cloud_cover=max_cloud_cover,
            dimensions=dimensions
        )
        
        # Convert results to JSON-serializable format
        cells_data = []
        for cell in results:
            cells_data.append({
                "id": cell.id,
                "center": {"lat": cell.center_lat, "lng": cell.center_lng},
                "bounds": {
                    "west": cell.west,
                    "south": cell.south,
                    "east": cell.east,
                    "north": cell.north
                },
                "deforestation_detected": cell.deforestation_detected,
                "forest_drop": cell.forest_drop,
                "ndvi_drop": cell.ndvi_drop,
                "before_forest_probability": cell.before_forest_prob,
                "after_forest_probability": cell.after_forest_prob,
                "before_image_file": cell.before_image_file,
                "after_image_file": cell.after_image_file,
                "error": cell.error
            })
        
        deforested_count = sum(1 for c in cells_data if c["deforestation_detected"])
        
        return {
            "status": "success",
            "location_name": location_name,
            "grid_size": grid_size,
            "total_cells": len(cells_data),
            "deforested_cells": deforested_count,
            "cells": cells_data,
            "scan_dates": {
                "before": before_date,
                "after": after_date
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Grid scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.post("/test-with-cached")
async def test_with_cached():
    """
    Test ML detection using cached imagery files.
    This demonstrates the ML model works without needing Earth Engine auth.
    """
    if detector is None:
        raise HTTPException(status_code=503, detail="ML model not loaded")
    
    try:
        import glob
        from pathlib import Path
        
        # Get cached files
        cache_dir = Path("data/raw/gee_exports")
        tif_files = sorted(cache_dir.glob("s2_10band_*.tif"))
        
        if len(tif_files) < 2:
            raise HTTPException(
                status_code=404,
                detail=f"Need at least 2 cached files, found {len(tif_files)}"
            )
        
        # Use first two files
        before_file = str(tif_files[0])
        after_file = str(tif_files[1])
        
        logger.info(f"Testing with cached files: {before_file}, {after_file}")
        
        # Run detection
        result = detector.detect_change_from_files(
            before_image=before_file,
            after_image=after_file,
            before_date="2024-01-01",
            after_date="2024-06-01"
        )
        
        # Add file info to response
        result["test_mode"] = True
        result["files_used"] = {
            "before": Path(before_file).name,
            "after": Path(after_file).name
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export router
__all__ = ['ml_router', 'initialize_ml_system']
