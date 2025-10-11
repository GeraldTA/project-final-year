"""
FastAPI server for frontend-backend integration
Exposes endpoints for deforestation map data and realistic satellite images
"""

from fastapi import FastAPI, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import json

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
def get_realistic_photos():
    """Return the realistic satellite photos map HTML."""
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
