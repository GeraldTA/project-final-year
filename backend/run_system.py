#!/usr/bin/env python3
"""
Simple runner script for the deforestation detection system.
This script handles Python path setup and provides easy access to main functionality.
"""

import os
import sys
from pathlib import Path

# Add project directories to Python path
project_root = Path(__file__).parent
src_dir = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_dir))

# Now import and run the main pipeline
if __name__ == "__main__":
    try:
        from src.main import main
        main()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please ensure all dependencies are installed:")
        print("pip install numpy pandas matplotlib scikit-learn rasterio geopandas PyYAML requests scikit-image scipy")
        sys.exit(1)
    except Exception as e:
        print(f"Error running system: {e}")
        sys.exit(1)
