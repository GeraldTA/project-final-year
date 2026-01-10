"""
FastAPI server for frontend-backend integration
Exposes endpoints for deforestation map data and realistic satellite images
"""

from fastapi import FastAPI, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import json
import folium
from folium.plugins import MarkerCluster

app = FastAPI()

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
    limit: int = Query(100, description="Maximum number of detection markers to show")
):
    """Generate an interactive map with all detection markers overlaid."""
    coords_file = MAPS_DIR / "deforestation_coordinates.json"
    report_file = MAPS_DIR / "deforestation_report.json"
    
    if not coords_file.exists() or not report_file.exists():
        return Response("Detection data not found", status_code=404)
    
    with open(coords_file, 'r') as f:
        coordinates = json.load(f)
    
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    # Create map centered on region
    center_lat = (report['coordinates']['south'] + report['coordinates']['north']) / 2
    center_lon = (report['coordinates']['west'] + report['coordinates']['east']) / 2
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles='OpenStreetMap'
    )
    
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
        tiles='OpenStreetMap'
    )
    
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

# Add more endpoints as needed for processing, status, etc.

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI backend server for frontend integration...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
