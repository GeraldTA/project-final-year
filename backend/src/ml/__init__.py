"""
Machine Learning module for deforestation detection.

This module implements ResNet-50 based CNN with transfer learning
from BigEarthNet for accurate vegetation classification and change detection.
"""

# Keep imports lightweight so API startup doesn't require training-only deps.

__all__ = [
    "DeforestationCNN",
    "Sentinel2Preprocessor",
    "DeforestationDetector",
    "ModelTrainer",
    "BigEarthNetForestChangeDetector",
]


def __getattr__(name: str):
    if name == "DeforestationCNN":
        from .model import DeforestationCNN

        return DeforestationCNN
    if name == "Sentinel2Preprocessor":
        from .preprocessing import Sentinel2Preprocessor

        return Sentinel2Preprocessor
    if name == "DeforestationDetector":
        from .inference import DeforestationDetector

        return DeforestationDetector
    if name == "ModelTrainer":
        from .training import ModelTrainer

        return ModelTrainer
    if name == "BigEarthNetForestChangeDetector":
        from .bigearthnet_detector import BigEarthNetForestChangeDetector

        return BigEarthNetForestChangeDetector
    raise AttributeError(name)
