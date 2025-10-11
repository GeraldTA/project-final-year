from gee_processor import GEESentinelProcessor
import ee

gee = GEESentinelProcessor()
bounds = gee.config.get_region_bounds()
roi = ee.Geometry.Rectangle([bounds['west'], bounds['south'], bounds['east'], bounds['north']])

# Get a simple collection
collection = gee.get_sentinel2_collection('2025-02-15', '2025-03-15', max_cloud_cover=30)

def add_ndvi(image):
    return image.addBands(image.normalizedDifference(['B8', 'B4']).rename('NDVI'))

ndvi_image = collection.map(add_ndvi).select('NDVI').median().clip(roi)
ndvi_vis = {'min': 0, 'max': 1, 'palette': ['red', 'orange', 'yellow', 'yellowgreen', 'green']}

map_result = ndvi_image.getMapId(ndvi_vis)
print("Full map result:", map_result)
print("Map ID:", map_result['mapid'])
print("Generated URL:", f"https://earthengine.googleapis.com/v1/{map_result['mapid']}/tiles/{{z}}/{{x}}/{{y}}")