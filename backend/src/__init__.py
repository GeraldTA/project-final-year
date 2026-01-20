"""
Deforestation Detection using Sentinel-2 Satellite Imagery

A comprehensive machine learning system for automated deforestation monitoring
using satellite imagery from Sentinel-2 and Google Earth Engine.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Keep package imports lightweight. Importing `src` should not pull in optional
# runtime dependencies (scheduler, external APIs, etc.).

__all__ = ["DeforestationPipeline"]


def __getattr__(name: str):
	if name == "DeforestationPipeline":
		from .main import DeforestationPipeline

		return DeforestationPipeline
	raise AttributeError(name)
