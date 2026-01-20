"""\
BigEarthNet v2.0 (reBEN) pretrained ResNet-50 (Sentinel-2) integration.

This module provides an *offline*, factory-ready detector by using publicly
available pretrained weights:

- Repo: BIFOLD-BigEarthNetv2-0/resnet50-s2-v0.2.0
- File: model.safetensors
- License: MIT (per model card)

We turn multi-label land-cover probabilities into a single "forest probability"
and detect deforestation as a significant forest-probability drop over time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import logging

import numpy as np
import torch
import torch.nn.functional as F
from safetensors.torch import load_file
from huggingface_hub import hf_hub_download
from torchvision.models import resnet50
from torch import nn

import rasterio
from rasterio.warp import transform_bounds


logger = logging.getLogger(__name__)


BIGEARTHNET_REPO_ID = "BIFOLD-BigEarthNetv2-0/resnet50-s2-v0.2.0"
BIGEARTHNET_FILENAME = "model.safetensors"


BIGEARTHNET_V2_CLASSES: List[str] = [
    "Agro-forestry areas",
    "Arable land",
    "Beaches, dunes, sands",
    "Broad-leaved forest",
    "Coastal wetlands",
    "Complex cultivation patterns",
    "Coniferous forest",
    "Industrial or commercial units",
    "Inland waters",
    "Inland wetlands",
    "Land principally occupied by agriculture, with significant areas of natural vegetation",
    "Marine waters",
    "Mixed forest",
    "Moors, heathland and sclerophyllous vegetation",
    "Natural grassland and sparsely vegetated areas",
    "Pastures",
    "Permanent crops",
    "Transitional woodland, shrub",
    "Urban fabric",
]


FOREST_CLASS_NAMES: Tuple[str, ...] = (
    "Broad-leaved forest",
    "Coniferous forest",
    "Mixed forest",
    "Transitional woodland, shrub",
)


def _forest_class_indices() -> List[int]:
    indices: List[int] = []
    for name in FOREST_CLASS_NAMES:
        try:
            indices.append(BIGEARTHNET_V2_CLASSES.index(name))
        except ValueError:
            continue
    return indices


FOREST_INDICES: List[int] = _forest_class_indices()


@dataclass
class BigEarthNetPrediction:
    forest_probability: float
    ndvi_mean: Optional[float]
    class_probabilities: Dict[str, float]
    timestamp: str
    bbox_wgs84: Optional[Dict[str, float]]


class BigEarthNetForestChangeDetector:
    """Forest probability inference + change detection using BigEarthNet weights."""

    def __init__(
        self,
        device: Optional[str] = None,
        forest_drop_threshold: float = 0.20,
        min_forest_before: float = 0.40,
        max_forest_after: float = 0.30,
        ndvi_drop_threshold: float = 0.10,
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.forest_drop_threshold = forest_drop_threshold
        self.min_forest_before = min_forest_before
        self.max_forest_after = max_forest_after
        self.ndvi_drop_threshold = ndvi_drop_threshold

        self.model = self._load_model().to(self.device)
        self.model.eval()

        logger.info("BigEarthNet detector ready on %s", self.device)

    def _load_model(self) -> nn.Module:
        logger.info("Downloading/loading BigEarthNet weights: %s", BIGEARTHNET_REPO_ID)
        weights_path = hf_hub_download(BIGEARTHNET_REPO_ID, BIGEARTHNET_FILENAME)
        state = load_file(weights_path)

        model = resnet50(weights=None)
        model.conv1 = nn.Conv2d(10, 64, kernel_size=7, stride=2, padding=3, bias=False)
        model.fc = nn.Linear(2048, len(BIGEARTHNET_V2_CLASSES))

        # Map keys: model.vision_encoder.* -> torchvision resnet keys
        mapped: Dict[str, torch.Tensor] = {}
        prefix = "model.vision_encoder."
        for k, v in state.items():
            if k.startswith(prefix):
                mapped[k[len(prefix):]] = v

        missing, unexpected = model.load_state_dict(mapped, strict=False)
        if missing or unexpected:
            # strict=False keeps us resilient across minor upstream changes.
            logger.warning("BigEarthNet weight load: missing=%d unexpected=%d", len(missing), len(unexpected))
        else:
            logger.info("BigEarthNet weights loaded cleanly")

        return model

    def _read_multiband(self, image_path: str) -> Tuple[np.ndarray, Optional[Dict[str, float]]]:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        with rasterio.open(path) as src:
            arr = src.read()  # (bands, H, W)

            bbox = None
            try:
                b = src.bounds
                if src.crs:
                    west, south, east, north = transform_bounds(src.crs, "EPSG:4326", b.left, b.bottom, b.right, b.top, densify_pts=21)
                    bbox = {"west": float(west), "south": float(south), "east": float(east), "north": float(north)}
            except Exception:
                bbox = None

        if arr.shape[0] < 10:
            raise ValueError(
                "BigEarthNet S2 model requires 10 Sentinel-2 bands in one GeoTIFF (B02,B03,B04,B05,B06,B07,B08,B8A,B11,B12). "
                f"Got {arr.shape[0]} band(s) in {image_path}."
            )

        # Take first 10 bands (expected to already be in the correct order)
        arr10 = arr[:10].astype(np.float32)

        # Convert typical Sentinel-2 scaled reflectance (0..10000) to 0..1
        if np.nanmax(arr10) > 1.5:
            arr10 = arr10 / 10000.0
        arr10 = np.clip(arr10, 0.0, 1.0)

        return arr10, bbox

    def _to_tensor_224(self, bands10: np.ndarray) -> torch.Tensor:
        # bands10: (10, H, W)
        t = torch.from_numpy(bands10).unsqueeze(0)  # (1, 10, H, W)
        if t.shape[-2:] != (224, 224):
            t = F.interpolate(t, size=(224, 224), mode="bilinear", align_corners=False)
        return t.to(self.device)

    def _ndvi_mean(self, bands10: np.ndarray) -> float:
        # Order: B02,B03,B04,B05,B06,B07,B08,B8A,B11,B12
        red = bands10[2]
        nir = bands10[6]
        denom = (nir + red) + 1e-6
        ndvi = (nir - red) / denom
        return float(np.nanmean(ndvi))

    def predict_from_file(self, image_path: str) -> Dict:
        bands10, bbox = self._read_multiband(image_path)
        ndvi_mean = self._ndvi_mean(bands10)
        x = self._to_tensor_224(bands10)

        with torch.no_grad():
            logits = self.model(x)
            probs = torch.sigmoid(logits)[0].detach().cpu().numpy().astype(np.float32)

        class_probs = {BIGEARTHNET_V2_CLASSES[i]: float(probs[i]) for i in range(len(BIGEARTHNET_V2_CLASSES))}
        forest_prob = float(np.max([probs[i] for i in FOREST_INDICES])) if FOREST_INDICES else float(np.max(probs))

        return BigEarthNetPrediction(
            forest_probability=forest_prob,
            ndvi_mean=ndvi_mean,
            class_probabilities=class_probs,
            timestamp=datetime.now().isoformat(),
            bbox_wgs84=bbox,
        ).__dict__

    def detect_change_from_files(
        self,
        before_image: str,
        after_image: str,
        before_date: str,
        after_date: str,
    ) -> Dict:
        before = self.predict_from_file(before_image)
        after = self.predict_from_file(after_image)

        forest_drop = float(before["forest_probability"] - after["forest_probability"])
        ndvi_drop = None
        if before.get("ndvi_mean") is not None and after.get("ndvi_mean") is not None:
            ndvi_drop = float(before["ndvi_mean"] - after["ndvi_mean"])

        deforestation_detected = (
            before["forest_probability"] >= self.min_forest_before
            and after["forest_probability"] <= self.max_forest_after
            and forest_drop >= self.forest_drop_threshold
            and (ndvi_drop is None or ndvi_drop >= self.ndvi_drop_threshold)
        )

        return {
            "status": "success",
            "deforestation_detected": bool(deforestation_detected),
            "before": {
                "date": before_date,
                "forest_probability": before["forest_probability"],
                "ndvi_mean": before.get("ndvi_mean"),
                "bbox_wgs84": before.get("bbox_wgs84"),
            },
            "after": {
                "date": after_date,
                "forest_probability": after["forest_probability"],
                "ndvi_mean": after.get("ndvi_mean"),
                "bbox_wgs84": after.get("bbox_wgs84"),
            },
            "change": {
                "forest_drop": forest_drop,
                "ndvi_drop": ndvi_drop,
                "thresholds": {
                    "forest_drop_threshold": self.forest_drop_threshold,
                    "min_forest_before": self.min_forest_before,
                    "max_forest_after": self.max_forest_after,
                    "ndvi_drop_threshold": self.ndvi_drop_threshold,
                },
            },
            "model": {
                "type": "bigearthnet-resnet50-s2",
                "repo_id": BIGEARTHNET_REPO_ID,
                "bands_required": ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"],
                "forest_classes": list(FOREST_CLASS_NAMES),
            },
            "timestamp": datetime.now().isoformat(),
        }
