import requests
import json

# Target coordinates
lat = -20.16392782978884
lng = 28.64070250183401

# Create bounding box (approximately 0.1 degrees around the point)
offset = 0.05
bounds = {
    'west': lng - offset,
    'south': lat - offset,
    'east': lng + offset,
    'north': lat + offset
}

# Dates for comparison (using recent available data)
params = {
    'before_date': '2020-07-15',
    'after_date': '2024-07-15',
    'west': bounds['west'],
    'south': bounds['south'],
    'east': bounds['east'],
    'north': bounds['north'],
    'window_days': 45,
    'max_cloud_cover': 70,
    'dimensions': 512
}

print('🛰️  Analyzing location: {}, {}'.format(lat, lng))
print('📅 Period: {} to {}'.format(params['before_date'], params['after_date']))
print('⏳ Downloading satellite images and running analysis...\n')

url = 'http://127.0.0.1:8001/api/ml/detect-change-auto'
r = requests.post(url, params=params, timeout=300)

if r.status_code == 200:
    result = r.json()
    
    print('='*60)
    print('🔍 DEFORESTATION ANALYSIS RESULTS')
    print('='*60)
    
    if result.get('deforestation_detected'):
        print('🚨 VERDICT: DEFORESTATION DETECTED ❌')
    else:
        print('✅ VERDICT: NO DEFORESTATION DETECTED ✓')
    
    print('\n📊 Detailed Metrics:')
    print('-'*60)
    
    before = result.get('before', {})
    after = result.get('after', {})
    change = result.get('change', {})
    
    print('Before ({}):'.format(before.get('date')))
    print('  • Forest Probability: {:.3f}'.format(before.get('forest_probability', 0)))
    print('  • NDVI (Vegetation): {:.3f}'.format(before.get('ndvi_mean', 0)))
    
    print('\nAfter ({}):'.format(after.get('date')))
    print('  • Forest Probability: {:.3f}'.format(after.get('forest_probability', 0)))
    print('  • NDVI (Vegetation): {:.3f}'.format(after.get('ndvi_mean', 0)))
    
    print('\n📉 Changes Detected:')
    print('  • Forest Drop: {:.3f}'.format(change.get('forest_drop', 0)))
    print('  • NDVI Drop: {:.3f}'.format(change.get('ndvi_drop', 0)))
    
    thresholds = change.get('thresholds', {})
    print('\n🎯 Detection Thresholds:')
    print('  • Forest drop threshold: {:.2f}'.format(thresholds.get('forest_drop_threshold', 0)))
    print('  • Min forest before: {:.2f}'.format(thresholds.get('min_forest_before', 0)))
    print('  • Max forest after: {:.2f}'.format(thresholds.get('max_forest_after', 0)))
    print('  • NDVI drop threshold: {:.2f}'.format(thresholds.get('ndvi_drop_threshold', 0)))
    
    if result.get('seasonal_warning'):
        print('\n⚠️  WARNING: {}'.format(result.get('seasonal_warning')))
    
    # Save images info
    exports = result.get('exports', {})
    if exports:
        print('\n💾 Satellite Images:')
        print('  • Before: {}'.format(exports.get('before', {}).get('path', 'N/A')))
        print('  • After: {}'.format(exports.get('after', {}).get('path', 'N/A')))
    
    print('='*60)
    
    # Final interpretation
    print('\n💡 Interpretation:')
    if result.get('deforestation_detected'):
        forest_drop = change.get('forest_drop', 0)
        ndvi_drop = change.get('ndvi_drop', 0)
        print('The analysis detected a significant forest loss of {:.1%}'.format(forest_drop))
        print('with vegetation index dropping by {:.3f}.'.format(ndvi_drop))
        print('This indicates likely deforestation or severe vegetation degradation.')
    else:
        print('No significant deforestation detected in this area.')
        print('The forest cover and vegetation indices remain relatively stable.')
else:
    print('❌ Error: {}'.format(r.status_code))
    print(r.text)
