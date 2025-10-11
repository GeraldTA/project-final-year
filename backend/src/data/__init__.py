"""
Data module for satellite imagery downloading and management.

This module contains components for downloading and managing satellite imagery
from various sources including Copernicus Data Space Ecosystem and Google Earth Engine.
"""

# Import modules to make them available when importing the package
import sys
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(src_dir))

from sentinel_downloader import SentinelDownloader
from gee_client import GEEClient

__all__ = ["SentinelDownloader", "GEEClient"]
