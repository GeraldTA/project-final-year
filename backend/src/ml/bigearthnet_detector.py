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


# Path where the fine-tuned binary model will be saved after Colab training
_LOCAL_MODEL_PATH = Path(__file__).parent.parent.parent.parent / "models" / "deforestation_model.pth"


class BigEarthNetForestChangeDetector:
    """Forest probability inference + change detection using BigEarthNet weights."""

    def __init__(
        self,
        device: Optional[str] = None,
        forest_drop_threshold: float = 0.20,
        min_forest_before: float = 0.40,
        max_forest_after: float = 0.30,
        ndvi_drop_threshold: float = 0.10,
        local_model_path: Optional[str] = None,
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.forest_drop_threshold = forest_drop_threshold
        self.min_forest_before = min_forest_before
        self.max_forest_after = max_forest_after
        self.ndvi_drop_threshold = ndvi_drop_threshold

        # Resolve local model path: explicit arg > default backend/models/ location
        resolved_local = Path(local_model_path) if local_model_path else _LOCAL_MODEL_PATH

        if resolved_local.exists():
            logger.info("Found fine-tuned model at %s — using it instead of HuggingFace", resolved_local)
            self.model, self.is_binary = self._load_finetuned_model(resolved_local)
        else:
            logger.info("No local fine-tuned model found. Loading pretrained BigEarthNet from HuggingFace...")
            self.model, self.is_binary = self._load_bigearthnet_model(), False

        self.model = self.model.to(self.device)
        self.model.eval()
        logger.info("BigEarthNet detector ready on %s (binary_mode=%s)", self.device, self.is_binary)

    def _load_finetuned_model(self, path: Path):
        """Load a fine-tuned binary (Forest/Non-Forest) model from a .pth checkpoint."""
        import torch as _torch
        checkpoint = _torch.load(str(path), map_location="cpu")
        state_dict = checkpoint.get("model_state_dict", checkpoint)
        num_classes    = checkpoint.get("num_classes", 2)
        input_channels = checkpoint.get("input_channels", 4)

        model = resnet50(weights=None)
        model.conv1 = nn.Conv2d(input_channels, 64, kernel_size=7, stride=2, padding=3, bias=False)
        model.fc = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(2048, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes)
        )
        model.load_state_dict(state_dict, strict=False)
        logger.info("Fine-tuned model loaded — %d classes, %d input channels", num_classes, input_channels)
        return model, True

    def _load_bigearthnet_model(self) -> nn.Module:
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

        num_bands = arr.shape[0]
        required  = 4 if self.is_binary else 10

        if num_bands < required:
            raise ValueError(
                f"Model requires {required} Sentinel-2 bands. "
                f"Got {num_bands} band(s) in {image_path}."
            )

        arr_out = arr[:required].astype(np.float32)

        # Convert typical Sentinel-2 scaled reflectance (0..10000) to 0..1
        if np.nanmax(arr_out) > 1.5:
            arr_out = arr_out / 10000.0
        arr_out = np.clip(arr_out, 0.0, 1.0)

        return arr_out, bbox

    def _to_tensor_224(self, bands: np.ndarray) -> torch.Tensor:
        # bands: (C, H, W)
        t = torch.from_numpy(bands).unsqueeze(0)  # (1, C, H, W)
        if t.shape[-2:] != (224, 224):
            t = F.interpolate(t, size=(224, 224), mode="bilinear", align_corners=False)
        return t.to(self.device)

    def _ndvi_mean(self, bands: np.ndarray) -> float:
        if self.is_binary:
            # 4-band order: B4(Red), B3(Green), B2(Blue), B8(NIR)
            red = bands[0]
            nir = bands[3]
        else:
            # 10-band BigEarthNet order: B02,B03,B04,B05,B06,B07,B08,B8A,B11,B12
            red = bands[2]
            nir = bands[6]
        denom = (nir + red) + 1e-6
        ndvi = (nir - red) / denom
        return float(np.nanmean(ndvi))

    def _greenness_score(self, bands: np.ndarray) -> float:
        """
        Calculate greenness using Green band intensity relative to Red/Blue.
        Higher green = more vegetation. This is a visual indicator.
        """
        if self.is_binary:
            # 4-band order: B4(Red), B3(Green), B2(Blue), B8(NIR)
            red   = bands[0]
            green = bands[1]
            blue  = bands[2]
        else:
            # 10-band BigEarthNet order: B02=Blue, B03=Green, B04=Red
            blue  = bands[0]
            green = bands[1]
            red   = bands[2]

        green_dominance = green / (red + blue + 1e-6)
        return float(np.nanmean(green_dominance))

    def predict_from_file(self, image_path: str) -> Dict:
        bands, bbox = self._read_multiband(image_path)
        ndvi_mean = self._ndvi_mean(bands)
        greenness = self._greenness_score(bands)
        x = self._to_tensor_224(bands)

        with torch.no_grad():
            logits = self.model(x)

            if self.is_binary:
                # Fine-tuned binary model: class 0 = Forest, class 1 = Non-Forest
                probs_bin   = torch.softmax(logits, dim=1)[0].detach().cpu().numpy()
                forest_prob = float(probs_bin[0])   # probability of being Forest
                class_probs = {"Forest": float(probs_bin[0]), "Non-Forest": float(probs_bin[1])}
            else:
                # BigEarthNet 19-class model
                probs = torch.sigmoid(logits)[0].detach().cpu().numpy().astype(np.float32)
                class_probs = {BIGEARTHNET_V2_CLASSES[i]: float(probs[i]) for i in range(len(BIGEARTHNET_V2_CLASSES))}
                forest_prob = float(np.max([probs[i] for i in FOREST_INDICES])) if FOREST_INDICES else float(np.max(probs))

        return BigEarthNetPrediction(
            forest_probability=forest_prob,
            ndvi_mean=ndvi_mean,
            class_probabilities=class_probs,
            timestamp=datetime.now().isoformat(),
            bbox_wgs84=bbox,
        ).__dict__ | {"greenness_score": greenness}

    def detect_change_from_files(
        self,
        before_image: str,
        after_image: str,
        before_date: str,
        after_date: str,
    ) -> Dict:
        before = self.predict_from_file(before_image)
        after = self.predict_from_file(after_image)

        # Calculate raw differences (probabilities are 0-1)
        forest_drop = float(before["forest_probability"] - after["forest_probability"])
        forest_drop_percent = forest_drop * 100.0  # Convert to percentage
        
        # Calculate forest cover percentages
        forest_cover_before_percent = before["forest_probability"] * 100.0
        forest_cover_after_percent = after["forest_probability"] * 100.0
        
        # Calculate relative forest loss (as percentage of original forest)
        if before["forest_probability"] > 0.01:  # Avoid division by zero
            forest_loss_relative = (forest_drop / before["forest_probability"]) * 100.0
        else:
            forest_loss_relative = 0.0
        
        ndvi_drop = None
        ndvi_increase = 0.0
        greenness_increase = 0.0
        
        if before.get("ndvi_mean") is not None and after.get("ndvi_mean") is not None:
            ndvi_drop = float(before["ndvi_mean"] - after["ndvi_mean"])
            ndvi_increase = float(after["ndvi_mean"] - before["ndvi_mean"])
        
        if before.get("greenness_score") is not None and after.get("greenness_score") is not None:
            greenness_increase = float(after["greenness_score"] - before["greenness_score"])

        # CRITICAL FIX: Visual RGB greenness is more reliable than ML model for Zimbabwe
        # BigEarthNet was trained on European forests, not African savannas
        visual_shows_growth = greenness_increase > 0.05  # 5% more green in RGB
        ndvi_shows_growth = ndvi_increase > 0.05  # 5% NDVI increase
        ndvi_shows_decline = ndvi_drop > 0.1  # 10% NDVI drop
        
        # Priority: Visual evidence > NDVI > ML model
        if visual_shows_growth or ndvi_shows_growth:
            # Visual/NDVI evidence shows INCREASE in vegetation - NOT deforestation
            deforestation_detected = False
            logger.info(f"Vegetation GROWTH detected (greenness: +{greenness_increase:.3f}, NDVI: +{ndvi_increase:.3f}) - overriding ML model")
        elif ndvi_shows_decline:
            # NDVI confirms vegetation loss
            deforestation_detected = (
                ndvi_drop >= self.ndvi_drop_threshold
                or forest_drop >= self.forest_drop_threshold
            )
            logger.info(f"NDVI dropped by {ndvi_drop:.3f} - potential deforestation")
        else:
            # Small changes - use ML model but be conservative
            deforestation_detected = (
                before["forest_probability"] >= self.min_forest_before
                and after["forest_probability"] <= self.max_forest_after
                and forest_drop >= self.forest_drop_threshold
            )

        return {
            "status": "success",
            "deforestation_detected": bool(deforestation_detected),
            "before": {
                "date": before_date,
                "forest_probability": before["forest_probability"],
                "forest_cover_percent": forest_cover_before_percent,
                "ndvi_mean": before.get("ndvi_mean"),
                "greenness_score": before.get("greenness_score"),
                "bbox_wgs84": before.get("bbox_wgs84"),
            },
            "after": {
                "date": after_date,
                "forest_probability": after["forest_probability"],
                "forest_cover_percent": forest_cover_after_percent,
                "ndvi_mean": after.get("ndvi_mean"),
                "greenness_score": after.get("greenness_score"),
                "bbox_wgs84": after.get("bbox_wgs84"),
            },
            "change": {
                "forest_drop": forest_drop,
                "forest_drop_percent": forest_drop_percent,
                "forest_loss_percent": forest_loss_relative,
                "ndvi_drop": ndvi_drop,
                "ndvi_increase": ndvi_increase,
                "greenness_increase": greenness_increase,
                "vegetation_trend": (
                    "growth" if (visual_shows_growth or ndvi_shows_growth) 
                    else ("decline" if ndvi_shows_decline else "stable")
                ),
                "interpretation": (
                    f"Visual/NDVI analysis shows vegetation GROWTH (greenness: +{greenness_increase:.3f}, NDVI: +{ndvi_increase:.3f}) - NOT deforestation" 
                    if (visual_shows_growth or ndvi_shows_growth)
                    else f"NDVI decreased by {ndvi_drop:.3f} - possible deforestation" if ndvi_shows_decline
                    else "Minimal vegetation change detected"
                ),
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
                "note": "Visual RGB + NDVI corrected for Zimbabwe (model trained on European landscapes)",
            },
            "timestamp": datetime.now().isoformat(),
        }
