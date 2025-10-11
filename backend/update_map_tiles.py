#!/usr/bin/env python3
"""
Update realistic photo map with fresh NDVI tile URLs.
"""

import json
from gee_processor import GEESentinelProcessor

def update_realistic_map_with_fresh_tiles():
    """Generate fresh NDVI tiles and update the realistic photo processor."""
    
    print("🌍 Generating fresh NDVI tile URLs...")
    
    # Generate fresh tile URLs
    gee = GEESentinelProcessor()
    tiles = gee.create_ndvi_map_tiles()
    
    if not tiles:
        print("❌ Failed to generate tile URLs")
        return False
    
    print("✅ Generated fresh tile URLs:")
    for name, url in tiles.items():
        print(f"  {name}: {url[:80]}...")
    
    # Read the realistic photo processor
    with open('realistic_photo_processor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update the tile URLs in the content
    content = content.replace(
        'https://earthengine.googleapis.com/v1/projects/trans-scheme-463112-q8/maps/86dc11727349c1035b9aa536a933e639-3b4a90f3b82b18789451eaa32f313488/tiles/{z}/{x}/{y}',
        tiles['ndvi_before']
    )
    
    content = content.replace(
        'https://earthengine.googleapis.com/v1/projects/trans-scheme-463112-q8/maps/605496535641b81c6e0f268e3363e544-e67d28f4324f06ad6fbb662ac561d8c1/tiles/{z}/{x}/{y}',
        tiles['ndvi_after']
    )
    
    content = content.replace(
        'https://earthengine.googleapis.com/v1/projects/trans-scheme-463112-q8/maps/c727dab057309452cac130c72ea40659-d37c47ae64e89c1eb9fdf134e1583a82/tiles/{z}/{x}/{y}',
        tiles['ndvi_change']
    )
    
    # Write the updated content
    with open('realistic_photo_processor.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Updated realistic_photo_processor.py with fresh tile URLs")
    
    # Save the tile URLs for reference
    with open('fresh_tile_urls.json', 'w') as f:
        json.dump(tiles, f, indent=2)
    
    print("✅ Saved tile URLs to fresh_tile_urls.json")
    return True

if __name__ == "__main__":
    update_realistic_map_with_fresh_tiles()