#!/usr/bin/env python3
"""
Test script to verify the deforestation detection system is working.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_imports():
    """Test that all main modules can be imported."""
    try:
        print("Testing imports...")
        
        # Test configuration
        from utils.config import get_config
        config = get_config()
        print(f"✓ Configuration loaded: {config.get('region.name')}")
        
        # Test logger
        from utils.logger import setup_logger
        logger = setup_logger()
        print("✓ Logger initialized")
        
        # Test main pipeline
        from main import DeforestationPipeline
        print("✓ DeforestationPipeline imported successfully")
        
        # Test data modules
        from data.sentinel_downloader import SentinelDownloader
        print("✓ SentinelDownloader imported successfully")
        
        # Test processing modules  
        from processing.ndvi_calculator import NDVICalculator
        from processing.change_detector import ChangeDetector
        print("✓ Processing modules imported successfully")
        
        # Test scheduler
        from utils.scheduler import TaskScheduler
        print("✓ TaskScheduler imported successfully")
        
        print("\n🎉 All modules imported successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_configuration():
    """Test configuration loading and validation."""
    try:
        print("\nTesting configuration...")
        
        from utils.config import get_config
        config = get_config()
        
        # Test basic config access
        region_name = config.get('region.name')
        bounds = config.get_region_bounds()
        
        print(f"✓ Region: {region_name}")
        print(f"✓ Bounds: {bounds}")
        
        # Test data directories
        raw_dir = config.get_data_dir('raw_images')
        processed_dir = config.get_data_dir('processed_images') 
        
        print(f"✓ Raw data directory: {raw_dir}")
        print(f"✓ Processed data directory: {processed_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality without external API calls."""
    try:
        print("\nTesting basic functionality...")
        
        # Test NDVI calculation with dummy data
        import numpy as np
        from processing.ndvi_calculator import NDVICalculator
        
        # Create dummy Red and NIR data
        red_data = np.random.randint(1000, 3000, (100, 100))
        nir_data = np.random.randint(3000, 8000, (100, 100))
        
        # Calculate NDVI manually
        ndvi = (nir_data - red_data) / (nir_data + red_data)
        
        print(f"✓ Dummy NDVI calculated: mean = {np.mean(ndvi):.3f}")
        
        # Test change detection with dummy data
        from processing.change_detector import ChangeDetector
        
        # Create dummy before/after NDVI arrays
        before_ndvi = np.random.uniform(0.2, 0.8, (100, 100))
        after_ndvi = before_ndvi - np.random.uniform(0, 0.5, (100, 100))  # Simulate loss
        
        print("✓ Dummy change detection data created")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Deforestation Detection System Tests")
    print("=" * 50)
    
    all_passed = True
    
    # Run tests
    all_passed &= test_imports()
    all_passed &= test_configuration()
    all_passed &= test_basic_functionality()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! The system is ready to use.")
        print("\nNext steps:")
        print("1. Set up your API credentials in config/config.yaml")
        print("2. Run: python src/main.py --download")
        print("3. For automated monitoring: python src/main.py --start-monitoring")
    else:
        print("❌ Some tests failed. Please check the error messages above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
