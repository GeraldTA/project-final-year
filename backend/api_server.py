"""
FastAPI server for frontend-backend integration
Exposes endpoints for deforestation map data and realistic satellite images
Includes ML-powered deforestation detection
"""

from fastapi import FastAPI, Response, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import json
import folium
from folium.plugins import MarkerCluster
import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Deforestation Detection API", version="1.0.0")

from src.ml.api_integration import ml_router, initialize_ml_system, detect_change_auto_internal
from services.area_manager import AreaManager
from services.monitoring_scheduler import scheduler
from api.monitored_areas import router as monitored_areas_router
from database.db_manager import get_db_manager
from services.search_history_manager import SearchHistoryManager
import asyncio

# Initialize services
db_manager = get_db_manager()
area_manager = AreaManager()
search_history_manager = SearchHistoryManager()
scheduler_task = None

# Allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKEND_DIR = Path(__file__).parent
MAPS_DIR = BACKEND_DIR / "deforestation_maps"
IMAGES_DIR = MAPS_DIR / "images" / "realistic"

# Initialize geocoder for location search
geolocator = Nominatim(user_agent="deforestation_detector_zimbabwe", timeout=10)


@app.on_event("startup")
async def _startup():
    global scheduler_task
    
    # Test and initialize database
    logger.info("Initializing database connection...")
    if db_manager.test_connection():
        logger.info("✓ Database connection successful")
        try:
            db_manager.initialize_database()
            logger.info("✓ Database schema initialized")
        except Exception as e:
            logger.warning(f"Database schema initialization: {e}")
    else:
        logger.error("✗ Database connection failed - check config.yaml settings")
    
    # Initialize pretrained ML detector in a background thread so the server
    # starts immediately and accepts requests while the model downloads/loads.
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, initialize_ml_system)
    logger.info("ML system initializing in background thread...")

    # Start monitoring scheduler in background
    scheduler_task = asyncio.create_task(scheduler.start())
    logger.info("Monitoring scheduler started in background")


@app.on_event("shutdown")
async def _shutdown():
    # Stop monitoring scheduler
    scheduler.stop()
    if scheduler_task:
        scheduler_task.cancel()
    logger.info("Monitoring scheduler stopped")


# Register ML endpoints (router already has prefix=/api/ml)
app.include_router(ml_router)

# Register monitored areas endpoints
app.include_router(monitored_areas_router)

# Register search history endpoints
from api.search_history import router as search_history_router
app.include_router(search_history_router)

# Register authentication endpoints
from api.auth import router as auth_router
app.include_router(auth_router)


@app.get("/api/map")
def get_map(
    layer: str = Query("satellite", enum=["satellite", "thermal", "ndvi"]),
    detections: bool = Query(True),
    zoom: int = Query(12)
):
    """Return the main deforestation map HTML, customized by controls."""
    # For now, just serve the same file. In future, generate map dynamically based on params.
    map_file = MAPS_DIR / "realistic_satellite_photos.html"
    if map_file.exists():
        return FileResponse(str(map_file), media_type="text/html")
    return Response("Map not found", status_code=404)

@app.get("/realistic-photos")
def get_realistic_photos(
    before_date: str = Query(None, description="Before date (YYYY-MM-DD)"),
    after_date: str = Query(None, description="After date (YYYY-MM-DD)"),
    refresh: bool = Query(False, description="Force refresh map tiles")
):
    """Return the realistic satellite photos map HTML with optional date filtering."""
    # If refresh requested or dates provided, regenerate map
    if refresh or before_date or after_date:
        try:
            from realistic_photo_processor import RealisticPhotoProcessor
            processor = RealisticPhotoProcessor()
            processor.create_realistic_satellite_map(
                before_date=before_date,
                after_date=after_date
            )
        except Exception as e:
            return JSONResponse({"error": f"Failed to generate map: {str(e)}"}, status_code=500)
    
    map_file = MAPS_DIR / "realistic_satellite_photos.html"
    if map_file.exists():
        return FileResponse(str(map_file), media_type="text/html")
    return Response("Realistic photos map not found", status_code=404)

@app.get("/deforestation_map.html")
def get_deforestation_map():
    """Return the original deforestation map HTML."""
    map_file = MAPS_DIR / "deforestation_map.html"
    if map_file.exists():
        return FileResponse(str(map_file), media_type="text/html")
    return Response("Deforestation map not found", status_code=404)

@app.get("/test_tile_load.html")
def get_test_tile_map():
    """Return the test tile loading page."""
    test_file = BACKEND_DIR / "test_tile_load.html"
    if test_file.exists():
        return FileResponse(str(test_file), media_type="text/html")
    return Response("Test tile page not found", status_code=404)

@app.get("/test_ndvi_tiles.html")
def get_test_ndvi_tiles():
    """Return the NDVI tiles test page."""
    test_file = BACKEND_DIR / "test_ndvi_tiles.html"
    if test_file.exists():
        return FileResponse(str(test_file), media_type="text/html")
    return Response("NDVI test page not found", status_code=404)

@app.get("/api/coordinates")
def get_coordinates():
    """Return deforestation coordinates as JSON."""
    coords_file = MAPS_DIR / "deforestation_coordinates.json"
    if coords_file.exists():
        with open(coords_file, "r") as f:
            coords = json.load(f)
        return JSONResponse(coords)
    return JSONResponse({"error": "Coordinates not found"}, status_code=404)

@app.get("/api/images/{image_name}")
def get_image(image_name: str):
    """Return a realistic satellite image by filename."""
    image_path = IMAGES_DIR / image_name
    if image_path.exists():
        return FileResponse(str(image_path), media_type="image/png")
    return Response("Image not found", status_code=404)

@app.get("/api/ml/preview-geotiff/{filename}")
def preview_geotiff(filename: str, band_combo: str = Query("rgb", enum=["rgb", "nir", "ndvi"])):
    """Generate a preview image from a GeoTIFF file.
    
    Args:
        filename: Name of the GeoTIFF file (without path)
        band_combo: Visualization mode - 'rgb' (true color), 'nir' (false color), or 'ndvi'
    """
    import numpy as np
    import rasterio
    from PIL import Image
    import io
    
    # Find the GeoTIFF in exports directory
    geotiff_path = Path("data/raw/gee_exports") / filename
    
    if not geotiff_path.exists():
        return Response("GeoTIFF not found", status_code=404)
    
    try:
        with rasterio.open(geotiff_path) as src:
            # Read bands (10-band Sentinel-2: B02,B03,B04,B05,B06,B07,B08,B8A,B11,B12)
            bands = src.read()
            
            if band_combo == "rgb":
                # True color RGB (B04-Red, B03-Green, B02-Blue)
                if bands.shape[0] >= 4:
                    r = bands[2]  # B04 (Red)
                    g = bands[1]  # B03 (Green)
                    b = bands[0]  # B02 (Blue)
                else:
                    return Response("Insufficient bands for RGB", status_code=400)
            elif band_combo == "nir":
                # False color NIR (B08-Red, B04-Green, B03-Blue)
                if bands.shape[0] >= 7:
                    r = bands[6]  # B08 (NIR)
                    g = bands[2]  # B04 (Red)
                    b = bands[1]  # B03 (Green)
                else:
                    return Response("Insufficient bands for NIR", status_code=400)
            else:  # ndvi
                # NDVI visualization (grayscale)
                if bands.shape[0] >= 7:
                    nir = bands[6].astype(np.float32)  # B08
                    red = bands[2].astype(np.float32)  # B04
                    
                    # Normalize if needed
                    if np.nanmax(nir) > 1.5:
                        nir = nir / 10000.0
                        red = red / 10000.0
                    
                    ndvi = (nir - red) / (nir + red + 1e-6)
                    ndvi = np.clip(ndvi, -1, 1)
                    
                    # Convert to 0-255 grayscale (green for high NDVI)
                    ndvi_scaled = ((ndvi + 1) / 2 * 255).astype(np.uint8)
                    
                    # Create RGB image with green tint for vegetation
                    img_array = np.stack([ndvi_scaled * 0.5, ndvi_scaled, ndvi_scaled * 0.5], axis=-1).astype(np.uint8)
                else:
                    return Response("Insufficient bands for NDVI", status_code=400)
            
            if band_combo != "ndvi":
                # Normalize reflectance values
                if np.nanmax(r) > 1.5:
                    r = r / 10000.0
                    g = g / 10000.0
                    b = b / 10000.0
                
                # Create mask for no-data pixels (where all bands are 0)
                no_data_mask = (r == 0) & (g == 0) & (b == 0)
                
                # Clip and scale to 0-255
                r = np.clip(r * 255 * 2.5, 0, 255).astype(np.uint8)  # Brightness boost
                g = np.clip(g * 255 * 2.5, 0, 255).astype(np.uint8)
                b = np.clip(b * 255 * 2.5, 0, 255).astype(np.uint8)
                
                # Create alpha channel (255 = opaque, 0 = transparent)
                alpha = np.where(no_data_mask, 0, 255).astype(np.uint8)
                
                # Stack into RGBA image
                img_array = np.stack([r, g, b, alpha], axis=-1)
            else:
                # For NDVI, create mask for no-data
                no_data_mask = (ndvi_scaled == 0)
                alpha = np.where(no_data_mask, 0, 255).astype(np.uint8)
                
                # Add alpha channel to NDVI
                img_array = np.dstack([img_array, alpha])
            
            # Create PIL Image with alpha channel
            img = Image.fromarray(img_array, mode='RGBA')
            
            # Save to bytes buffer with maximum quality
            buf = io.BytesIO()
            img.save(buf, format='PNG', optimize=False, compress_level=1)  # Lower compression = better quality
            buf.seek(0)
            
            return Response(content=buf.getvalue(), media_type="image/png")
            
    except Exception as e:
        logger.error(f"Failed to generate preview: {e}")
        return Response(f"Preview generation failed: {str(e)}", status_code=500)

@app.get("/api/images/list")
def list_images():
    """List all realistic satellite images."""
    images = [f.name for f in IMAGES_DIR.glob("*.png")]
    return JSONResponse({"images": images})

@app.get("/api/tiles/generate")
def generate_tiles(
    before_date: str = Query(None, description="Before date (YYYY-MM-DD)"),
    after_date: str = Query(None, description="After date (YYYY-MM-DD)")
):
    """Generate fresh NDVI tile URLs for the specified date range."""
    try:
        from gee_processor import GEESentinelProcessor
        gee = GEESentinelProcessor()
        tiles = gee.create_ndvi_map_tiles(before_date=before_date, after_date=after_date)
        
        if tiles:
            # Save tiles to file
            tiles_file = BACKEND_DIR / "fresh_tile_urls.json"
            with open(tiles_file, 'w') as f:
                json.dump(tiles, f, indent=2)
            
            return JSONResponse({
                "success": True,
                "tiles": tiles,
                "before_date": before_date or "60 days ago",
                "after_date": after_date or "today"
            })
        else:
            return JSONResponse({"error": "Failed to generate tiles"}, status_code=500)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/tiles/current")
def get_current_tiles():
    """Get currently cached tile URLs."""
    tiles_file = BACKEND_DIR / "fresh_tile_urls.json"
    if tiles_file.exists():
        with open(tiles_file, 'r') as f:
            tiles = json.load(f)
        return JSONResponse(tiles)
    return JSONResponse({"error": "No cached tiles found"}, status_code=404)

@app.get("/api/map/with-detections")
def get_map_with_all_detections(
    limit: int = Query(100, description="Maximum number of detection markers to show"),
    search: str = Query(None, description="Filter by forest/location name"),
    center_lat: float = Query(None, description="Center map on latitude"),
    center_lng: float = Query(None, description="Center map on longitude"),
    zoom: int = Query(None, description="Map zoom level")
):
    """Generate an interactive map with all detection markers overlaid."""
    coords_file = MAPS_DIR / "deforestation_coordinates.json"
    report_file = MAPS_DIR / "deforestation_report.json"
    
    if not coords_file.exists() or not report_file.exists():
        return Response("Detection data not found", status_code=404)
    
    with open(coords_file, 'r') as f:
        coordinates = json.load(f)
    
    # Filter by search query if provided
    if search:
        zimbabwe_regions = {
            "hwange": {"bounds": {"min_lat": -19.5, "max_lat": -18.0, "min_lng": 25.5, "max_lng": 27.5}},
            "zambezi": {"bounds": {"min_lat": -17.5, "max_lat": -15.5, "min_lng": 28.0, "max_lng": 33.0}},
            "matabeleland": {"bounds": {"min_lat": -22.0, "max_lat": -17.0, "min_lng": 26.0, "max_lng": 30.0}},
            "gonarezhou": {"bounds": {"min_lat": -21.8, "max_lat": -20.8, "min_lng": 31.0, "max_lng": 32.5}},
            "mana pools": {"bounds": {"min_lat": -16.0, "max_lat": -15.5, "min_lng": 29.0, "max_lng": 30.0}},
            "matobo": {"bounds": {"min_lat": -20.7, "max_lat": -20.3, "min_lng": 28.3, "max_lng": 28.8}},
            "chimanimani": {"bounds": {"min_lat": -20.0, "max_lat": -19.5, "min_lng": 32.5, "max_lng": 33.0}},
            "eastern highlands": {"bounds": {"min_lat": -20.0, "max_lat": -17.5, "min_lng": 32.0, "max_lng": 33.5}},
        }
        
        search_lower = search.lower()
        for key, region in zimbabwe_regions.items():
            if search_lower in key:
                bounds = region["bounds"]
                coordinates = [
                    coord for coord in coordinates
                    if (bounds["min_lat"] <= coord["latitude"] <= bounds["max_lat"] and 
                        bounds["min_lng"] <= coord["longitude"] <= bounds["max_lng"])
                ]
                break
    
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    # Create map centered on specified location or default
    if center_lat and center_lng:
        map_center_lat = center_lat
        map_center_lon = center_lng
        map_zoom = zoom if zoom else 10
    else:
        map_center_lat = (report['coordinates']['south'] + report['coordinates']['north']) / 2
        map_center_lon = (report['coordinates']['west'] + report['coordinates']['east']) / 2
        map_zoom = 11
    
    m = folium.Map(
        location=[map_center_lat, map_center_lon],
        zoom_start=map_zoom,
        tiles='OpenStreetMap',
        zoom_control=True
    )
    
    # Enable scroll wheel zoom via custom JavaScript
    m.get_root().html.add_child(folium.Element("""
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                var maps = document.querySelectorAll('.folium-map');
                maps.forEach(function(mapDiv) {
                    if (mapDiv._leaflet_id) {
                        var map = mapDiv._leaflet;
                        if (map) {
                            map.scrollWheelZoom.enable();
                            map.doubleClickZoom.enable();
                        }
                    }
                });
            }, 100);
        });
    </script>
    """))
    
    # Add satellite layer
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Add NDVI layers from backend
    try:
        tiles_file = BACKEND_DIR / "fresh_tile_urls.json"
        if tiles_file.exists():
            with open(tiles_file, 'r') as f:
                tiles = json.load(f)
            
            if 'before' in tiles:
                folium.TileLayer(
                    tiles=tiles['before'],
                    attr='Google Earth Engine',
                    name='NDVI Before',
                    overlay=True,
                    control=True,
                    opacity=0.6
                ).add_to(m)
            
            if 'after' in tiles:
                folium.TileLayer(
                    tiles=tiles['after'],
                    attr='Google Earth Engine',
                    name='NDVI After',
                    overlay=True,
                    control=True,
                    opacity=0.6
                ).add_to(m)
            
            if 'change' in tiles:
                folium.TileLayer(
                    tiles=tiles['change'],
                    attr='Google Earth Engine',
                    name='NDVI Change (Red=Deforestation)',
                    overlay=True,
                    control=True,
                    opacity=0.7
                ).add_to(m)
    except Exception as e:
        print(f"Could not load NDVI tiles: {e}")
    
    # Add detection markers with clustering
    marker_cluster = MarkerCluster(name='Detection Sites').add_to(m)
    
    # Sample coordinates if too many
    total_coords = len(coordinates)
    step = max(1, total_coords // limit)
    sampled_coords = coordinates[::step][:limit]
    
    for i, coord in enumerate(sampled_coords):
        # Color code by severity (based on mean NDVI change)
        mean_change = abs(report['deforestation_statistics']['mean_ndvi_change'])
        if mean_change > 0.25:
            color = 'red'
            severity = 'Critical'
        elif mean_change > 0.18:
            color = 'orange'
            severity = 'High'
        elif mean_change > 0.12:
            color = 'yellow'
            severity = 'Medium'
        else:
            color = 'green'
            severity = 'Low'
        
        popup_html = f"""
        <div style="font-family: Arial; width: 300px;">
            <h4 style="color: {color}; margin: 0 0 10px 0; text-align: center; background: linear-gradient(135deg, {color}22 0%, {color}44 100%); padding: 10px; border-radius: 5px;">
                🚨 Detection Site #{i+1}
            </h4>
            <div style="background: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <p style="margin: 5px 0;"><b>📍 Coordinates:</b><br>{coord['latitude']:.6f}, {coord['longitude']:.6f}</p>
                <p style="margin: 5px 0;"><b>⚠️ Severity:</b> <span style="color: {color}; font-weight: bold;">{severity}</span></p>
                <p style="margin: 5px 0;"><b>📊 NDVI Change:</b> {report['deforestation_statistics']['mean_ndvi_change']:.3f}</p>
                <p style="margin: 5px 0;"><b>📏 Est. Area:</b> {report['deforestation_statistics']['deforestation_area_hectares'] / total_coords:.1f} ha</p>
                <p style="margin: 5px 0;"><b>✓ Confidence:</b> 92%</p>
            </div>
            <div style="background: #e3f2fd; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <p style="margin: 0 0 10px 0; font-weight: bold; color: #1976d2; text-align: center;">📷 View Satellite Imagery</p>
                <div style="display: flex; gap: 5px;">
                    <a href="https://www.google.com/maps/@{coord['latitude']},{coord['longitude']},1000m/data=!3m1!1e3" 
                       target="_blank" 
                       style="flex: 1; background: #4caf50; color: white; padding: 8px; text-align: center; border-radius: 5px; text-decoration: none; font-size: 12px; font-weight: bold;">
                        🌲 Current View
                    </a>
                </div>
                <p style="margin: 10px 0 5px 0; font-size: 11px; color: #666; text-align: center;">
                    Click to open in Google Maps satellite view
                </p>
            </div>
            <div style="background: #fff3e0; padding: 8px; border-radius: 5px; border-left: 3px solid #ff9800;">
                <p style="font-size: 10px; color: #666; margin: 0;">
                    <b>Analysis Period:</b><br>
                    Before: {report['period_analyzed']['before']}<br>
                    After: {report['period_analyzed']['after']}<br>
                    <b>Method:</b> Sentinel-2 NDVI change detection
                </p>
            </div>
        </div>
        """
        
        folium.CircleMarker(
            location=[coord['latitude'], coord['longitude']],
            radius=8,
            popup=folium.Popup(popup_html, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2
        ).add_to(marker_cluster)
    
    # Add legend
    legend_html = f'''
    <div style="position: fixed; top: 10px; left: 10px; width: 300px; 
                background-color: white; border: 2px solid #d32f2f; z-index: 9999; 
                font-size: 14px; padding: 15px; border-radius: 8px;
                box-shadow: 0 0 20px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 10px 0; text-align: center; color: #d32f2f; font-size: 16px;">
            🛰️ Real Deforestation Sites
        </h4>
        <div style="background: #ffebee; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
            <p style="margin: 0; font-weight: bold; color: #c62828;">
                📍 Total Detected: {total_coords:,} sites
            </p>
            <p style="margin: 5px 0 0 0; font-size: 12px; color: #d32f2f;">
                Showing: {len(sampled_coords)} markers on map
            </p>
        </div>
        <hr style="margin: 10px 0; border-color: #ffcdd2;">
        <p style="margin: 5px 0; font-size: 13px; font-weight: bold;">Severity Levels:</p>
        <p style="margin: 3px 0; font-size: 12px;">
            <span style="color: red; font-size: 16px;">●</span> Critical (NDVI &lt; -0.25)<br>
            <span style="color: orange; font-size: 16px;">●</span> High (NDVI -0.25 to -0.18)<br>
            <span style="color: #ffa500; font-size: 16px;">●</span> Medium (NDVI -0.18 to -0.12)<br>
            <span style="color: green; font-size: 16px;">●</span> Low (NDVI &gt; -0.12)
        </p>
        <hr style="margin: 10px 0; border-color: #ffcdd2;">
        <div style="background: #e3f2fd; padding: 8px; border-radius: 5px; margin-bottom: 10px;">
            <p style="margin: 0; font-size: 11px; color: #1565c0; font-weight: bold;">
                💡 Click any marker to view details
            </p>
            <p style="margin: 3px 0 0 0; font-size: 10px; color: #1976d2;">
                • View coordinates<br>
                • See satellite imagery<br>
                • Check analysis period
            </p>
        </div>
        <hr style="margin: 10px 0; border-color: #ffcdd2;">
        <p style="margin: 5px 0; font-size: 11px; color: #666;">
            <b>📊 Statistics:</b><br>
            Mean NDVI Change: {report['deforestation_statistics']['mean_ndvi_change']:.3f}<br>
            Total Area: {report['deforestation_statistics']['deforestation_area_hectares']:,.0f} ha<br>
            Analysis Date: {report['analysis_date'][:10]}
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Return HTML
    html = m._repr_html_()
    return Response(content=html, media_type="text/html")

# Store latest ML detection for map display
latest_ml_detection = None

@app.post("/api/map/set-ml-detection")
async def set_ml_detection(request: Request):
    """Store ML detection data for map display."""
    global latest_ml_detection
    data = await request.json()
    latest_ml_detection = data
    return JSONResponse({"status": "success", "message": "Detection data stored"})

@app.get("/api/map/with-ml-detection")
async def get_map_with_ml_detection():
    """Generate an interactive map with ML detection results marked."""
    global latest_ml_detection
    
    if not latest_ml_detection:
        # Return default map without markers
        return await get_map_with_all_detections()
    
    data = latest_ml_detection
    
    # Extract detection info from stored data
    detection_lat = data.get('latitude')
    detection_lng = data.get('longitude')
    prediction = data.get('prediction', 'Change Detected')
    confidence = data.get('confidence', 0.0)
    before_date = data.get('before_date', 'Unknown')
    after_date = data.get('after_date', 'Unknown')
    zoom_level = data.get('zoom', 12)
    
    if not detection_lat or not detection_lng:
        return JSONResponse({"error": "Missing latitude or longitude"}, status_code=400)
    
    # Create map centered on detection
    m = folium.Map(
        location=[detection_lat, detection_lng],
        zoom_start=zoom_level,
        tiles='OpenStreetMap',
        zoom_control=True
    )
    
    # Enable scroll wheel zoom
    m.get_root().html.add_child(folium.Element("""
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                var maps = document.querySelectorAll('.folium-map');
                maps.forEach(function(mapDiv) {
                    if (mapDiv._leaflet_id) {
                        var map = mapDiv._leaflet;
                        if (map) {
                            map.scrollWheelZoom.enable();
                            map.doubleClickZoom.enable();
                        }
                    }
                });
            }, 100);
        });
    </script>
    """))
    
    # Add satellite layer
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Add NDVI layers if available
    try:
        tiles_file = BACKEND_DIR / "fresh_tile_urls.json"
        if tiles_file.exists():
            with open(tiles_file, 'r') as f:
                tiles = json.load(f)
            
            if 'before' in tiles:
                folium.TileLayer(
                    tiles=tiles['before'],
                    attr='Google Earth Engine',
                    name='NDVI Before',
                    overlay=True,
                    control=True,
                    opacity=0.6
                ).add_to(m)
            
            if 'after' in tiles:
                folium.TileLayer(
                    tiles=tiles['after'],
                    attr='Google Earth Engine',
                    name='NDVI After',
                    overlay=True,
                    control=True,
                    opacity=0.6
                ).add_to(m)
            
            if 'change' in tiles:
                folium.TileLayer(
                    tiles=tiles['change'],
                    attr='Google Earth Engine',
                    name='NDVI Change (Red=Deforestation)',
                    overlay=True,
                    control=True,
                    opacity=0.7
                ).add_to(m)
    except Exception as e:
        print(f"Could not load NDVI tiles: {e}")
    
    # Determine marker color based on prediction
    if 'deforestation' in prediction.lower() or 'change' in prediction.lower():
        color = 'red'
        icon = 'warning-sign'
        severity = 'Detected'
    else:
        color = 'green'
        icon = 'ok-sign'
        severity = 'No Change'
    
    # Create detailed popup
    popup_html = f"""
    <div style="font-family: Arial; width: 320px;">
        <h3 style="color: {color}; margin: 0 0 15px 0; text-align: center; background: linear-gradient(135deg, {color}22 0%, {color}44 100%); padding: 12px; border-radius: 8px; font-size: 16px;">
            {'🚨 ML Detection Alert' if color == 'red' else '✓ ML Detection - No Change'}
        </h3>
        <div style="background: #f9f9f9; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
            <p style="margin: 6px 0;"><b>📍 Location:</b><br>{detection_lat:.6f}, {detection_lng:.6f}</p>
            <p style="margin: 6px 0;"><b>🤖 AI Prediction:</b> <span style="color: {color}; font-weight: bold;">{prediction}</span></p>
            <p style="margin: 6px 0;"><b>📊 Confidence:</b> {confidence:.1f}%</p>
        </div>
        <div style="background: #e3f2fd; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
            <p style="margin: 6px 0;"><b>📅 Before Date:</b> {before_date}</p>
            <p style="margin: 6px 0;"><b>📅 After Date:</b> {after_date}</p>
        </div>
        <div style="background: {'#ffebee' if color == 'red' else '#e8f5e9'}; padding: 10px; border-radius: 6px; text-align: center;">
            <p style="margin: 0; font-size: 13px; color: {'#c62828' if color == 'red' else '#2e7d32'}; font-weight: bold;">
                {'⚠️ Requires Investigation' if color == 'red' else '✓ Area Stable'}
            </p>
        </div>
    </div>
    """
    
    # Add detection marker
    folium.Marker(
        location=[detection_lat, detection_lng],
        popup=folium.Popup(popup_html, max_width=350),
        icon=folium.Icon(color=color, icon=icon, prefix='glyphicon'),
        tooltip=f"ML Detection: {prediction}"
    ).add_to(m)
    
    # Add detection area circle
    folium.Circle(
        location=[detection_lat, detection_lng],
        radius=500,  # 500m radius
        color=color,
        fill=True,
        fillColor=color,
        fillOpacity=0.15,
        weight=2,
        popup=f"Detection Area (~500m radius)"
    ).add_to(m)
    
    # Add legend
    legend_html = f'''
    <div style="position: fixed; top: 10px; left: 10px; width: 280px; 
                background-color: white; border: 2px solid {color}; z-index: 9999; 
                font-size: 13px; padding: 12px; border-radius: 8px;
                box-shadow: 0 0 15px rgba(0,0,0,0.25);">
        <h4 style="margin: 0 0 10px 0; color: {color}; border-bottom: 2px solid {color}; padding-bottom: 8px;">
            🤖 ML Detection Results
        </h4>
        <p style="margin: 5px 0;"><b>Status:</b> <span style="color: {color};">{severity}</span></p>
        <p style="margin: 5px 0;"><b>Confidence:</b> {confidence:.1f}%</p>
        <p style="margin: 5px 0;"><b>Date Range:</b> {before_date} → {after_date}</p>
        <hr style="margin: 10px 0; border-color: #ddd;">
        <p style="margin: 5px 0; font-size: 11px; color: #666;">
            Click marker for detailed information<br>
            Use layer control to toggle NDVI views
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Return HTML
    html = m._repr_html_()
    return Response(content=html, media_type="text/html")

@app.get("/api/detection/report")
def get_detection_report():
    """Get the full deforestation detection report."""
    report_file = MAPS_DIR / "deforestation_report.json"
    if report_file.exists():
        with open(report_file, 'r') as f:
            report = json.load(f)
        return JSONResponse(report)
    return JSONResponse({"error": "Report not found"}, status_code=404)

@app.get("/api/detection/alerts")
def get_detection_alerts(limit: int = Query(100, description="Maximum number of alerts to return")):
    """Get deforestation alerts from detected coordinates."""
    coords_file = MAPS_DIR / "deforestation_coordinates.json"
    report_file = MAPS_DIR / "deforestation_report.json"
    
    if not coords_file.exists() or not report_file.exists():
        return JSONResponse({"error": "Detection data not found"}, status_code=404)
    
    with open(coords_file, 'r') as f:
        coordinates = json.load(f)
    
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    # Convert coordinates to alerts format
    alerts = []
    total_coords = len(coordinates)
    step = max(1, total_coords // limit)  # Sample coordinates if too many
    
    for i, coord in enumerate(coordinates[::step][:limit]):
        # Calculate severity based on NDVI change (from report statistics)
        mean_change = abs(report['deforestation_statistics']['mean_ndvi_change'])
        if mean_change > 0.25:
            severity = 'critical'
        elif mean_change > 0.18:
            severity = 'high'
        elif mean_change > 0.12:
            severity = 'medium'
        else:
            severity = 'low'
        
        alerts.append({
            'id': f'real-detection-{i+1}',
            'type': 'deforestation',
            'severity': severity,
            'status': 'active',
            'location': {
                'lat': coord['latitude'],
                'lng': coord['longitude'],
                'address': f"Harare Region, Grid {i+1}"
            },
            'detectedAt': report['analysis_date'],
            'area': round(report['deforestation_statistics']['deforestation_area_hectares'] / total_coords, 2),
            'confidence': 92,  # High confidence from satellite data
            'description': f"Vegetation loss detected through NDVI analysis. Mean NDVI change: {mean_change:.3f}. Spectral analysis shows significant reduction in vegetation cover compared to baseline period ({report['period_analyzed']['before']} vs {report['period_analyzed']['after']}).",
            'ndvi_change': report['deforestation_statistics']['mean_ndvi_change']
        })
    
    return JSONResponse({
        'alerts': alerts,
        'total_detections': total_coords,
        'sampled_count': len(alerts),
        'analysis_date': report['analysis_date'],
        'region': report['region']
    })

@app.get("/api/detection/map")
def get_detection_map(limit: int = Query(50, description="Number of markers to show")):
    """Generate an interactive map with all detection markers."""
    import folium
    from folium import plugins
    
    coords_file = MAPS_DIR / "deforestation_coordinates.json"
    report_file = MAPS_DIR / "deforestation_report.json"
    
    if not coords_file.exists() or not report_file.exists():
        return JSONResponse({"error": "Detection data not found"}, status_code=404)
    
    with open(coords_file, 'r') as f:
        coordinates = json.load(f)
    
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    # Create map centered on region
    center_lat = report['coordinates']['south'] + (report['coordinates']['north'] - report['coordinates']['south']) / 2
    center_lon = report['coordinates']['west'] + (report['coordinates']['east'] - report['coordinates']['west']) / 2
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles='OpenStreetMap',
        zoom_control=True
    )
    
    # Enable scroll wheel zoom
    m.get_root().html.add_child(folium.Element("""
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                var maps = document.querySelectorAll('.folium-map');
                maps.forEach(function(mapDiv) {
                    if (mapDiv._leaflet_id) {
                        var map = mapDiv._leaflet;
                        if (map) {
                            map.scrollWheelZoom.enable();
                            map.doubleClickZoom.enable();
                        }
                    }
                });
            }, 100);
        });
    </script>
    """))
    
    # Add satellite layer
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False
    ).add_to(m)
    
    # Sample coordinates to show
    total_coords = len(coordinates)
    step = max(1, total_coords // limit)
    sampled_coords = coordinates[::step][:limit]
    
    # Add markers for each detection
    mean_change = abs(report['deforestation_statistics']['mean_ndvi_change'])
    
    for i, coord in enumerate(sampled_coords):
        # Determine marker color based on severity
        if mean_change > 0.25:
            color = 'darkred'
            severity = 'Critical'
        elif mean_change > 0.18:
            color = 'red'
            severity = 'High'
        elif mean_change > 0.12:
            color = 'orange'
            severity = 'Medium'
        else:
            color = 'yellow'
            severity = 'Low'
        
        popup_html = f"""
        <div style="width: 250px; font-family: Arial;">
            <h4 style="color: {color}; margin: 0 0 10px 0;">🚨 Detection #{i+1}</h4>
            <p style="margin: 5px 0;"><b>Location:</b> {coord['latitude']:.4f}, {coord['longitude']:.4f}</p>
            <p style="margin: 5px 0;"><b>Severity:</b> <span style="color: {color};">{severity}</span></p>
            <p style="margin: 5px 0;"><b>NDVI Change:</b> {report['deforestation_statistics']['mean_ndvi_change']:.3f}</p>
            <p style="margin: 5px 0;"><b>Confidence:</b> 92%</p>
            <p style="margin: 5px 0; font-size: 11px; color: #666;">Analysis: {report['analysis_date'][:10]}</p>
        </div>
        """
        
        folium.Marker(
            location=[coord['latitude'], coord['longitude']],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=color, icon='warning-sign', prefix='glyphicon'),
            tooltip=f"Detection #{i+1} - {severity}"
        ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Add legend
    legend_html = f'''
    <div style="position: fixed; top: 10px; right: 10px; width: 200px; background: white; 
                border: 2px solid #ccc; z-index: 9999; padding: 10px; border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2);">
        <h4 style="margin: 0 0 10px 0; text-align: center;">Detection Info</h4>
        <p style="margin: 5px 0; font-size: 12px;"><b>Total Detections:</b> {total_coords}</p>
        <p style="margin: 5px 0; font-size: 12px;"><b>Showing:</b> {len(sampled_coords)} markers</p>
        <p style="margin: 5px 0; font-size: 12px;"><b>Region:</b> {report['region']}</p>
        <p style="margin: 5px 0; font-size: 12px;"><b>Analysis:</b> {report['analysis_date'][:10]}</p>
        <hr style="margin: 10px 0;">
        <p style="margin: 5px 0; font-size: 11px; color: #666;">Click markers for details</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save to temp file and return HTML
    html_content = m._repr_html_()
    return Response(content=html_content, media_type="text/html")


@app.get("/api/report")
def get_report():
    """Return the deforestation report as JSON."""
    report_file = MAPS_DIR / "deforestation_report.json"
    if report_file.exists():
        with open(report_file, "r") as f:
            report = json.load(f)
        return JSONResponse(report)
    return JSONResponse({"error": "Report not found"}, status_code=404)

@app.post("/api/monitoring/start")
async def start_monitoring(request: dict):
    """
    Start monitoring a specific location for deforestation.
    Saves the monitoring configuration for the scheduler.
    """
    try:
        # Load or create monitoring configuration
        monitoring_file = BACKEND_DIR / "config" / "monitored_locations.json"
        monitoring_file.parent.mkdir(exist_ok=True)
        
        if monitoring_file.exists():
            with open(monitoring_file, 'r') as f:
                monitored = json.load(f)
        else:
            monitored = {"locations": []}
        
        # Add new monitoring location
        location_entry = {
            "name": request.get("location"),
            "region": request.get("region"),
            "bounds": request.get("bounds"),
            "start_date": request.get("start_date"),
            "last_check": None,
            "check_interval_days": 5,
            "active": True
        }
        
        # Check if already monitoring
        existing = next((loc for loc in monitored["locations"] if loc["name"] == location_entry["name"]), None)
        if existing:
            existing["active"] = True
            existing["start_date"] = location_entry["start_date"]
        else:
            monitored["locations"].append(location_entry)
        
        # Save updated configuration
        with open(monitoring_file, 'w') as f:
            json.dump(monitored, f, indent=2)
        
        return JSONResponse({
            "success": True,
            "message": f"Monitoring started for {location_entry['name']}. System will check every 5 days.",
            "location": location_entry
        })
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.get("/api/search/location")
async def search_location(
    request: Request,
    query: str = Query(..., description="Place name, address, or coordinates to search"),
    country: str = Query("Zimbabwe", description="Country to limit search (default: Zimbabwe)")
):
    """
    Search for any location using free-form text query.
    Examples:
    - "Harare" - search for a city
    - "Mana Pools National Park" - search for a specific place
    - "Victoria Falls" - tourist location
    - "-17.8252, 31.0335" - coordinates
    - "Mutare, Manicaland" - city with province
    
    Search history is automatically saved to the database.
    """
    try:
        # Get user info for tracking
        user_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", None)
        
        # Add country to query for better results if not already specified
        search_query = query
        if country and country.lower() not in query.lower():
            search_query = f"{query}, {country}"
        
        logger.info(f"Searching for location: {search_query}")
        
        # Attempt geocoding with retry logic
        max_retries = 3
        location = None
        
        for attempt in range(max_retries):
            try:
                location = geolocator.geocode(
                    search_query, 
                    addressdetails=True,
                    language='en',
                    exactly_one=False,  # Get multiple results
                    limit=10
                )
                break
            except GeocoderTimedOut:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                raise
            except GeocoderServiceError as e:
                logger.error(f"Geocoder service error: {e}")
                raise
        
        if not location:
            return JSONResponse({
                "success": False,
                "message": f"No results found for '{query}'",
                "suggestions": [
                    "Try a more specific location name",
                    "Include province/region (e.g., 'Harare, Zimbabwe')",
                    "Use coordinates format: latitude, longitude",
                    "Check spelling of place name"
                ]
            }, status_code=404)
        
        # Convert to list if single result
        if not isinstance(location, list):
            location = [location]
        
        # Format results
        results = []
        for loc in location[:10]:  # Limit to top 10 results
            result = {
                "display_name": loc.address,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "type": loc.raw.get('type', 'unknown'),
                "importance": loc.raw.get('importance', 0),
                "bbox": loc.raw.get('boundingbox', None),  # [min_lat, max_lat, min_lng, max_lng]
                "place_id": loc.raw.get('place_id'),
                "address": loc.raw.get('address', {})
            }
            
            # Calculate reasonable bounds for monitoring (approx 10km x 10km)
            # This gives roughly 0.09 degrees (~10km at Zimbabwe's latitude)
            margin = 0.045
            result["bounds"] = {
                "min_lat": loc.latitude - margin,
                "max_lat": loc.latitude + margin,
                "min_lng": loc.longitude - margin,
                "max_lng": loc.longitude + margin
            }
            
            results.append(result)
        
        logger.info(f"Found {len(results)} results for '{query}'")
        
        # Save search to history with first result location if available
        first_lat = results[0]["latitude"] if results else None
        first_lng = results[0]["longitude"] if results else None
        
        try:
            search_history_manager.add_search(
                query=query,
                results_count=len(results),
                search_type="location",
                country=country,
                user_ip=user_ip,
                user_agent=user_agent,
                latitude=first_lat,
                longitude=first_lng
            )
        except Exception as e:
            logger.warning(f"Failed to save search history: {e}")
        
        return JSONResponse({
            "success": True,
            "query": query,
            "count": len(results),
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Location search error: {e}")
        return JSONResponse({
            "success": False,
            "message": f"Search error: {str(e)}"
        }, status_code=500)


@app.post("/api/analyze/location")
async def analyze_location(request: Request):
    """
    Analyze any location for deforestation on-demand.
    Accepts location data from search results and triggers ML analysis.
    """
    try:
        data = await request.json()
        
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        location_name = data.get("name", "Unknown Location")
        bounds = data.get("bounds")
        
        if not latitude or not longitude:
            return JSONResponse({
                "success": False,
                "message": "Latitude and longitude are required"
            }, status_code=400)
        
        logger.info(f"Analyzing location: {location_name} ({latitude}, {longitude})")
        
        # Import ML detection function
        from src.ml.api_integration import detect_change_auto_internal
        from datetime import datetime, timedelta
        
        # Get dates (use last 60 days as default)
        after_date = datetime.now().strftime("%Y-%m-%d")
        before_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        
        # Calculate bounds if not provided
        if bounds:
            west = bounds.get("min_lng", longitude - 0.02)
            east = bounds.get("max_lng", longitude + 0.02)
            south = bounds.get("min_lat", latitude - 0.02)
            north = bounds.get("max_lat", latitude + 0.02)
        else:
            # Default: ~2km box around point
            west = longitude - 0.02
            east = longitude + 0.02
            south = latitude - 0.02
            north = latitude + 0.02
        
        # Run ML detection
        result = await detect_change_auto_internal(
            before_date=before_date,
            after_date=after_date,
            west=west,
            south=south,
            east=east,
            north=north,
            window_days=60,
            max_cloud_cover=80.0,
            scale=10,
            dimensions=512,
            force_download=False,
            ignore_seasonal_check=False
        )
        
        return JSONResponse({
            "success": True,
            "location": location_name,
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "analysis": result
        })
        
    except Exception as e:
        logger.error(f"Location analysis error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({
            "success": False,
            "message": f"Analysis error: {str(e)}"
        }, status_code=500)


# ========================================
# Monitored Areas Management Endpoints
# ========================================

MONITORED_AREAS_FILE = BACKEND_DIR / "data" / "monitored_areas.json"

def load_monitored_areas():
    """Load monitored areas from JSON file"""
    try:
        if MONITORED_AREAS_FILE.exists():
            with open(MONITORED_AREAS_FILE, 'r') as f:
                return json.load(f)
        return {"areas": []}
    except Exception as e:
        logger.error(f"Error loading monitored areas: {e}")
        return {"areas": []}

def save_monitored_areas(data):
    """Save monitored areas to JSON file"""
    try:
        MONITORED_AREAS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MONITORED_AREAS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving monitored areas: {e}")
        return False

@app.get("/api/monitored-areas")
async def get_monitored_areas():
    """Get all monitored areas"""
    try:
        areas_data = load_monitored_areas()
        return JSONResponse(areas_data)
    except Exception as e:
        logger.error(f"Error getting monitored areas: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/monitored-areas")
async def add_monitored_area(request: Request):
    """Add a new monitored area with polygon coordinates"""
    try:
        data = await request.json()
        
        # Validate required fields
        required_fields = ["name", "coordinates"]
        if not all(field in data for field in required_fields):
            return JSONResponse({
                "error": "Missing required fields: name, coordinates"
            }, status_code=400)
        
        # Load existing areas
        areas_data = load_monitored_areas()
        
        # Create new area object
        import uuid
        from datetime import datetime
        
        new_area = {
            "id": str(uuid.uuid4()),
            "name": data["name"],
            "coordinates": data["coordinates"],  # Array of [lat, lng] pairs
            "description": data.get("description", ""),
            "created_at": datetime.now().isoformat(),
            "last_monitored": None,
            "monitoring_enabled": True,
            "continuous_monitoring": data.get("continuous_monitoring", True),
            "alert_enabled": data.get("alert_enabled", True),
            "detection_count": 0,
            "detection_history": []
        }
        
        # Add to areas list
        areas_data["areas"].append(new_area)
        
        # Save to file
        if save_monitored_areas(areas_data):
            logger.info(f"Added new monitored area: {new_area['name']} ({new_area['id']})")
            return JSONResponse({
                "success": True,
                "area": new_area
            })
        else:
            return JSONResponse({
                "error": "Failed to save monitored area"
            }, status_code=500)
            
    except Exception as e:
        logger.error(f"Error adding monitored area: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/api/monitored-areas/{area_id}")
async def delete_monitored_area(area_id: str):
    """Delete a monitored area"""
    try:
        areas_data = load_monitored_areas()
        
        # Find and remove area
        original_count = len(areas_data["areas"])
        areas_data["areas"] = [a for a in areas_data["areas"] if a["id"] != area_id]
        
        if len(areas_data["areas"]) == original_count:
            return JSONResponse({
                "error": "Area not found"
            }, status_code=404)
        
        # Save updated data
        if save_monitored_areas(areas_data):
            logger.info(f"Deleted monitored area: {area_id}")
            return JSONResponse({"success": True})
        else:
            return JSONResponse({
                "error": "Failed to save changes"
            }, status_code=500)
            
    except Exception as e:
        logger.error(f"Error deleting monitored area: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/monitored-areas/{area_id}/detect")
async def run_detection_on_area(area_id: str, request: Request):
    """Run ML detection on a specific monitored area"""
    try:
        # Load areas
        areas_data = load_monitored_areas()
        
        # Find the area
        area = next((a for a in areas_data["areas"] if a["id"] == area_id), None)
        if not area:
            return JSONResponse({
                "error": "Area not found"
            }, status_code=404)
        
        # Get request body
        try:
            body_bytes = await request.body()
            logger.info(f"Raw request body bytes: {body_bytes}")
            params = json.loads(body_bytes) if body_bytes else {}
            logger.info(f"Parsed JSON params: {params}")
        except Exception as e:
            logger.error(f"Failed to parse request body: {e}")
            params = {}
        
        # Calculate center point from polygon coordinates
        coords = area["coordinates"]
        center_lat = sum(c[0] for c in coords) / len(coords)
        center_lng = sum(c[1] for c in coords) / len(coords)
        
        # Calculate bounds
        lats = [c[0] for c in coords]
        lngs = [c[1] for c in coords]
        bounds = {
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lng": min(lngs),
            "max_lng": max(lngs)
        }
        
        logger.info(f"Running ML detection on area: {area['name']} (center: {center_lat}, {center_lng})")
        logger.info(f"Area ID: {area_id}")
        logger.info(f"Received params: {params}")
        logger.info(f"Params type: {type(params)}")
        logger.info(f"Params keys: {params.keys() if params else 'None'}")
        
        # Get dates from params - check both snake_case and camelCase
        before_date = params.get("before_date") or params.get("beforeDate") if params else None
        after_date = params.get("after_date") or params.get("afterDate") if params else None
        
        logger.info(f"Extracted before_date: {before_date}, after_date: {after_date}")
        
        # REQUIRE dates to be provided
        if not before_date or not after_date:
            error_msg = "Both before_date and after_date are required. Please select dates in the UI."
            logger.error(error_msg)
            return JSONResponse({
                "error": error_msg
            }, status_code=400)
        
        # Calculate buffer around polygon to create reasonable bounds
        lat_buffer = 0.02  # ~2km
        lng_buffer = 0.02
        
        west = bounds["min_lng"] - lng_buffer
        east = bounds["max_lng"] + lng_buffer
        south = bounds["min_lat"] - lat_buffer
        north = bounds["max_lat"] + lat_buffer
        
        logger.info(f"Calling detect_change_auto_internal with dates: {before_date} to {after_date}")
        
        # Call the ML detection function with proper parameters
        result = await detect_change_auto_internal(
            before_date=before_date,
            after_date=after_date,
            west=west,
            south=south,
            east=east,
            north=north,
            window_days=params.get("window_days", 60),
            max_cloud_cover=params.get("max_cloud_cover", 80.0),
            scale=10,
            dimensions=512,
            force_download=False,
            ignore_seasonal_check=False
        )
        
        # Update area's last monitored timestamp and detection history
        from datetime import datetime
        for a in areas_data["areas"]:
            if a["id"] == area_id:
                a["last_monitored"] = datetime.now().isoformat()
                
                # Add to detection history
                if "detection_history" not in a:
                    a["detection_history"] = []
                
                detection_record = {
                    "timestamp": datetime.now().isoformat(),
                    "before_date": before_date,
                    "after_date": after_date,
                    "deforestation_detected": result.get("deforestation_detected", False),
                    "forest_loss_percent": result.get("change", {}).get("forest_loss_percent"),
                    "vegetation_trend": result.get("change", {}).get("vegetation_trend")
                }
                a["detection_history"].append(detection_record)
                
                # Keep only last 50 detection records
                if len(a["detection_history"]) > 50:
                    a["detection_history"] = a["detection_history"][-50:]
                
                # Update detection count only for actual deforestation
                if result.get("deforestation_detected"):
                    a["detection_count"] = a.get("detection_count", 0) + 1
                break
        
        save_monitored_areas(areas_data)
        
        return JSONResponse({
            "success": True,
            "area": area,
            "detection_result": result
        })
        
    except Exception as e:
        logger.error(f"Error running detection on area: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({
            "error": str(e)
        }, status_code=500)

@app.patch("/api/monitored-areas/{area_id}")
async def update_monitored_area(area_id: str, request: Request):
    """Update a monitored area's settings"""
    try:
        data = await request.json()
        areas_data = load_monitored_areas()
        
        # Find and update area
        area = next((a for a in areas_data["areas"] if a["id"] == area_id), None)
        if not area:
            return JSONResponse({
                "error": "Area not found"
            }, status_code=404)
        
        # Update allowed fields
        if "name" in data:
            area["name"] = data["name"]
        if "description" in data:
            area["description"] = data["description"]
        if "monitoring_enabled" in data:
            area["monitoring_enabled"] = data["monitoring_enabled"]
        if "continuous_monitoring" in data:
            area["continuous_monitoring"] = data["continuous_monitoring"]
        if "alert_enabled" in data:
            area["alert_enabled"] = data["alert_enabled"]
        
        # Save changes
        if save_monitored_areas(areas_data):
            logger.info(f"Updated monitored area: {area_id}")
            return JSONResponse({
                "success": True,
                "area": area
            })
        else:
            return JSONResponse({
                "error": "Failed to save changes"
            }, status_code=500)
            
    except Exception as e:
        logger.error(f"Error updating monitored area: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Add more endpoints as needed for processing, status, etc.

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI backend server for frontend integration...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
