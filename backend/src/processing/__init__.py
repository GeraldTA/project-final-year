"""
Processing module for satellite imagery analysis and change detection.

This module contains components for NDVI calculation, change detection,
and other image processing operations for deforestation monitoring.
"""

# Import modules to make them available when importing the package
import sys
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(src_dir))

from ndvi_calculator import NDVICalculator
from change_detector import ChangeDetector

__all__ = ["NDVICalculator", "ChangeDetector"]
