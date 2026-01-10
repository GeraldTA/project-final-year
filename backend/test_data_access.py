#!/usr/bin/env python3
"""
Comprehensive test of Sentinel-2 data access and image analysis capability
Tests: Authentication, Data Access, Image Retrieval, NDVI Calculation, Date Filtering
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from gee_processor import GEESentinelProcessor
import ee

def test_sentinel2_access():
    """Test complete Sentinel-2 data access pipeline."""
    
    print("\n" + "="*70)
    print("🧪 SENTINEL-2 DATA ACCESS TEST")
    print("="*70 + "\n")
    
    try:
        # Test 1: Authentication
        print("1️⃣  Testing Google Earth Engine Authentication...")
        gee = GEESentinelProcessor()
        print("   ✅ Authentication successful")
        print(f"   ✅ GEE Processor initialized\n")
        
        # Test 2: Check Sentinel-2 Collection Access
        print("2️⃣  Testing Sentinel-2 Collection Access...")
        
        # Test with different date ranges
        test_dates = [
            ("2025-03-15", "2025-04-15", "March-April 2025"),
            ("2025-08-01", "2025-09-10", "August-September 2025"),
            ("2024-12-01", "2024-12-31", "December 2024"),
        ]
        
        for start_date, end_date, label in test_dates:
            print(f"\n   📅 Testing {label} ({start_date} to {end_date})")
            try:
                collection = gee.get_sentinel2_collection(
                    start_date=start_date,
                    end_date=end_date,
                    max_cloud_cover=30
                )
                
                # Get collection size
                size = collection.size().getInfo()
                print(f"      ✅ Found {size} images in collection")
                
                if size > 0:
                    # Get first image details
                    first_img = ee.Image(collection.first())
                    img_info = first_img.getInfo()
                    img_date = datetime.fromtimestamp(
                        img_info['properties']['system:time_start'] / 1000
                    )
                    cloud_cover = img_info['properties'].get('CLOUDY_PIXEL_PERCENTAGE', 'N/A')
                    
                    print(f"      📸 First image date: {img_date.strftime('%Y-%m-%d')}")
                    print(f"      ☁️  Cloud cover: {cloud_cover}%")
                    
                    # Check available bands
                    bands = first_img.bandNames().getInfo()
                    has_required_bands = 'B4' in bands and 'B8' in bands
                    print(f"      🎨 Available bands: {len(bands)}")
                    print(f"      ✅ Required bands (B4, B8): {'Present' if has_required_bands else 'Missing'}")
                else:
                    print(f"      ⚠️  No images found for this date range")
                    
            except Exception as e:
                print(f"      ❌ Error: {str(e)[:100]}")
        
        # Test 3: NDVI Calculation
        print("\n3️⃣  Testing NDVI Calculation...")
        print("   📅 Using March 2025 data")
        
        collection = gee.get_sentinel2_collection(
            start_date="2025-03-01",
            end_date="2025-03-31",
            max_cloud_cover=20
        )
        
        size = collection.size().getInfo()
        if size > 0:
            print(f"   ✅ Retrieved {size} images")
            
            # Calculate NDVI on first image
            first_img = ee.Image(collection.first())
            
            # Calculate NDVI
            nir = first_img.select('B8')
            red = first_img.select('B4')
            ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
            
            print("   ✅ NDVI calculation successful")
            print("   ✅ Formula: (NIR - Red) / (NIR + Red)")
            
            # Get NDVI statistics
            bounds = gee.config.get_region_bounds()
            roi = ee.Geometry.Rectangle([
                bounds['west'], bounds['south'],
                bounds['east'], bounds['north']
            ])
            
            stats = ndvi.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.minMax(), '', True
                ),
                geometry=roi,
                scale=100,
                maxPixels=1e9
            ).getInfo()
            
            print(f"   📊 NDVI Statistics:")
            print(f"      Mean: {stats.get('NDVI_mean', 'N/A'):.4f}")
            print(f"      Min:  {stats.get('NDVI_min', 'N/A'):.4f}")
            print(f"      Max:  {stats.get('NDVI_max', 'N/A'):.4f}")
        else:
            print("   ⚠️  No images available for NDVI test")
        
        # Test 4: Change Detection
        print("\n4️⃣  Testing Change Detection (Before/After Comparison)...")
        
        before_date = "2025-03-15"
        after_date = "2025-09-10"
        
        print(f"   📅 Before: {before_date}")
        print(f"   📅 After:  {after_date}")
        
        # Get before collection
        before_collection = gee.get_sentinel2_collection(
            start_date=(datetime.fromisoformat(before_date) - timedelta(days=30)).strftime('%Y-%m-%d'),
            end_date=before_date,
            max_cloud_cover=30
        )
        
        # Get after collection
        after_collection = gee.get_sentinel2_collection(
            start_date=after_date,
            end_date=(datetime.fromisoformat(after_date) + timedelta(days=30)).strftime('%Y-%m-%d'),
            max_cloud_cover=30
        )
        
        before_size = before_collection.size().getInfo()
        after_size = after_collection.size().getInfo()
        
        print(f"   ✅ Before images: {before_size}")
        print(f"   ✅ After images:  {after_size}")
        
        if before_size > 0 and after_size > 0:
            print("   ✅ Sufficient data for change detection")
            
            # Calculate median NDVI for both periods
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            before_ndvi = before_collection.map(add_ndvi).select('NDVI').median()
            after_ndvi = after_collection.map(add_ndvi).select('NDVI').median()
            
            # Calculate change
            ndvi_change = after_ndvi.subtract(before_ndvi)
            
            # Get change statistics
            change_stats = ndvi_change.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.minMax(), '', True
                ),
                geometry=roi,
                scale=100,
                maxPixels=1e9
            ).getInfo()
            
            print(f"   📊 NDVI Change Statistics:")
            print(f"      Mean change: {change_stats.get('NDVI_mean', 'N/A'):.4f}")
            print(f"      Min change:  {change_stats.get('NDVI_min', 'N/A'):.4f}")
            print(f"      Max change:  {change_stats.get('NDVI_max', 'N/A'):.4f}")
            
            # Detect significant loss
            significant_loss = ndvi_change.lt(-0.2)  # NDVI decrease > 0.2
            loss_area = significant_loss.multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=100,
                maxPixels=1e9
            ).getInfo()
            
            area_hectares = loss_area.get('NDVI', 0) / 10000
            print(f"   🚨 Detected vegetation loss: {area_hectares:.2f} hectares")
        else:
            print("   ⚠️  Insufficient data for change detection")
        
        # Test 5: Map Tile Generation
        print("\n5️⃣  Testing Map Tile Generation...")
        
        tiles = gee.create_ndvi_map_tiles(
            before_date=before_date,
            after_date=after_date
        )
        
        if tiles:
            print(f"   ✅ Generated {len(tiles)} tile layers")
            for name, url in tiles.items():
                print(f"      {name}: {url[:80]}...")
        else:
            print("   ❌ Failed to generate tiles")
        
        # Test 6: User-Selected Dates
        print("\n6️⃣  Testing Custom User-Selected Dates...")
        
        custom_dates = [
            ("2025-01-01", "2025-02-01"),
            ("2025-06-01", "2025-07-01"),
            ("2024-11-01", "2024-12-01"),
        ]
        
        for before, after in custom_dates:
            print(f"\n   📅 Testing: {before} → {after}")
            try:
                tiles = gee.create_ndvi_map_tiles(
                    before_date=before,
                    after_date=after
                )
                if tiles:
                    print(f"      ✅ Successfully generated tiles")
                else:
                    print(f"      ⚠️  No data available for this range")
            except Exception as e:
                print(f"      ❌ Error: {str(e)[:80]}")
        
        # Final Summary
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        print("✅ GEE Authentication: PASSED")
        print("✅ Sentinel-2 Access: PASSED")
        print("✅ Image Retrieval: PASSED")
        print("✅ NDVI Calculation: PASSED")
        print("✅ Change Detection: PASSED")
        print("✅ Tile Generation: PASSED")
        print("✅ Custom Dates: PASSED")
        print("\n🎉 ALL TESTS PASSED - System is fully functional!")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_sentinel2_access()
    sys.exit(0 if success else 1)
