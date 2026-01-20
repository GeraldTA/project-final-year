"""
Sentinel-2 Image Preprocessing Pipeline

STEP 2: Data Pipeline
- Cloud masking
- Image cropping to AOI
- Resize to 224x224 (ResNet input size)
- Normalization
- NDVI calculation
"""

import numpy as np
import torch
from torch.utils.data import Dataset
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, List
import json

logger = logging.getLogger(__name__)


class Sentinel2Preprocessor:
    """
    Preprocessor for Sentinel-2 satellite imagery.
    
    Handles:
    - Band selection (B2, B3, B4, B8)
    - Cloud masking
    - Image cropping
    - Resizing to 224x224
    - Normalization
    - NDVI calculation
    """
    
    # Sentinel-2 band indices
    BAND_MAPPING = {
        'B2_BLUE': 0,
        'B3_GREEN': 1,
        'B4_RED': 2,
        'B8_NIR': 3
    }
    
    # Normalization parameters (from Sentinel-2 statistics)
    # Values are approximate means and stds for each band
    NORMALIZATION_PARAMS = {
        'mean': [1353.04, 1265.71, 1269.77, 2497.57],  # B2, B3, B4, B8
        'std': [242.07, 290.94, 402.69, 516.77]
    }
    
    def __init__(self, target_size=(224, 224), normalize=True, compute_ndvi=True):
        """
        Initialize the preprocessor.
        
        Args:
            target_size: Target image size (height, width)
            normalize: Whether to normalize pixel values
            compute_ndvi: Whether to compute NDVI
        """
        self.target_size = target_size
        self.normalize = normalize
        self.compute_ndvi = compute_ndvi
        
        logger.info(f"Preprocessor initialized: size={target_size}, "
                   f"normalize={normalize}, ndvi={compute_ndvi}")
    
    def apply_cloud_mask(self, image: np.ndarray, qa_band: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Apply cloud masking to remove cloudy pixels.
        
        STEP 2.2: Cloud Masking
        
        Args:
            image: Input image array (H, W, C)
            qa_band: Quality assessment band (Sentinel-2 QA60 or similar)
        
        Returns:
            Masked image with clouds removed
        """
        if qa_band is None:
            logger.warning("No QA band provided, skipping cloud masking")
            return image
        
        # Sentinel-2 QA band bit masks
        # Bit 10: Opaque clouds
        # Bit 11: Cirrus clouds
        CLOUD_BIT = 10
        CIRRUS_BIT = 11
        
        cloud_mask = (qa_band & (1 << CLOUD_BIT)) == 0
        cirrus_mask = (qa_band & (1 << CIRRUS_BIT)) == 0
        
        # Combined mask
        clear_mask = cloud_mask & cirrus_mask
        
        # Apply mask to all bands
        masked_image = image.copy()
        for i in range(image.shape[2]):
            masked_image[:, :, i] = np.where(clear_mask, image[:, :, i], 0)
        
        cloudy_percent = (1 - clear_mask.sum() / clear_mask.size) * 100
        logger.info(f"Cloud masking applied: {cloudy_percent:.1f}% cloudy pixels removed")
        
        return masked_image
    
    def crop_to_aoi(self, image_path: str, aoi_geojson: Dict) -> np.ndarray:
        """
        Crop image to Area of Interest (Zimbabwe forest regions).
        
        STEP 2.2: Image Cropping
        
        Args:
            image_path: Path to the raster image
            aoi_geojson: GeoJSON geometry defining the area of interest
        
        Returns:
            Cropped image array
        """
        with rasterio.open(image_path) as src:
            # Crop to AOI
            out_image, out_transform = mask(src, [aoi_geojson], crop=True)
            
            # Update metadata
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform
            })
            
            logger.info(f"Image cropped to AOI: {out_image.shape}")
            return out_image
    
    def resize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Resize image to target size (224x224 for ResNet).
        
        STEP 2.2: Resize Images
        
        Args:
            image: Input image array (C, H, W) or (H, W, C)
        
        Returns:
            Resized image
        """
        from skimage.transform import resize
        
        # Ensure correct shape (H, W, C)
        if image.shape[0] in [3, 4]:  # Channels first
            image = np.transpose(image, (1, 2, 0))
        
        # Resize
        resized = resize(
            image,
            self.target_size,
            mode='reflect',
            anti_aliasing=True,
            preserve_range=True
        )
        
        logger.debug(f"Image resized: {image.shape} -> {resized.shape}")
        return resized
    
    def normalize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Normalize pixel values using Sentinel-2 statistics.
        
        STEP 2.2: Normalize Pixel Values
        Scale values between 0 and 1 using standardization
        
        Args:
            image: Input image array (H, W, C)
        
        Returns:
            Normalized image
        """
        if not self.normalize:
            # Simple 0-1 scaling
            return image / 10000.0  # Sentinel-2 values are scaled by 10000
        
        # Standardization: (x - mean) / std
        mean = np.array(self.NORMALIZATION_PARAMS['mean']).reshape(1, 1, -1)
        std = np.array(self.NORMALIZATION_PARAMS['std']).reshape(1, 1, -1)
        
        normalized = (image - mean) / std
        
        logger.debug("Image normalized using Sentinel-2 statistics")
        return normalized
    
    def calculate_ndvi(self, nir: np.ndarray, red: np.ndarray) -> np.ndarray:
        """
        Calculate NDVI (Normalized Difference Vegetation Index).
        
        STEP 2.2: NDVI Calculation
        NDVI = (NIR - Red) / (NIR + Red)
        
        Args:
            nir: Near-infrared band (B8)
            red: Red band (B4)
        
        Returns:
            NDVI array with values between -1 and 1
        """
        # Avoid division by zero
        denominator = nir + red
        denominator = np.where(denominator == 0, 0.0001, denominator)
        
        ndvi = (nir - red) / denominator
        
        # Clip to valid range
        ndvi = np.clip(ndvi, -1, 1)
        
        # Log statistics
        valid_pixels = ~np.isnan(ndvi)
        if valid_pixels.any():
            logger.info(f"NDVI calculated: mean={ndvi[valid_pixels].mean():.3f}, "
                       f"min={ndvi[valid_pixels].min():.3f}, "
                       f"max={ndvi[valid_pixels].max():.3f}")
        
        return ndvi
    
    def preprocess_image(
        self,
        bands: Dict[str, np.ndarray],
        qa_band: Optional[np.ndarray] = None,
        return_ndvi: bool = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Complete preprocessing pipeline for a single image.
        
        Args:
            bands: Dictionary of band arrays {'B2': array, 'B3': array, 'B4': array, 'B8': array}
            qa_band: Quality assessment band for cloud masking
            return_ndvi: Whether to return NDVI separately (default: self.compute_ndvi)
        
        Returns:
            Tuple of (preprocessed_image, ndvi) where:
            - preprocessed_image: (H, W, 4) array with RGBN channels
            - ndvi: (H, W) array or None
        """
        if return_ndvi is None:
            return_ndvi = self.compute_ndvi
        
        # Stack bands: B2 (Blue), B3 (Green), B4 (Red), B8 (NIR)
        required_bands = ['B2', 'B3', 'B4', 'B8']
        for band in required_bands:
            if band not in bands:
                raise ValueError(f"Missing required band: {band}")
        
        # Stack bands into single array (H, W, C)
        image = np.stack([bands[b] for b in required_bands], axis=-1)
        
        # Apply cloud mask if available
        if qa_band is not None:
            image = self.apply_cloud_mask(image, qa_band)
        
        # Resize to target size
        image = self.resize_image(image)
        
        # Calculate NDVI before normalization
        ndvi = None
        if return_ndvi:
            red = image[:, :, 2]  # B4
            nir = image[:, :, 3]  # B8
            ndvi = self.calculate_ndvi(nir, red)
        
        # Normalize
        image = self.normalize_image(image)
        
        return image, ndvi
    
    def preprocess_batch(
        self,
        batch_bands: List[Dict[str, np.ndarray]],
        qa_bands: Optional[List[np.ndarray]] = None
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Preprocess a batch of images.
        
        Args:
            batch_bands: List of band dictionaries
            qa_bands: List of QA bands (optional)
        
        Returns:
            Tuple of (image_tensor, ndvi_tensor)
        """
        if qa_bands is None:
            qa_bands = [None] * len(batch_bands)
        
        images = []
        ndvis = []
        
        for bands, qa in zip(batch_bands, qa_bands):
            img, ndvi = self.preprocess_image(bands, qa)
            images.append(img)
            if ndvi is not None:
                ndvis.append(ndvi)
        
        # Convert to tensors (N, C, H, W)
        image_tensor = torch.from_numpy(np.array(images)).float()
        image_tensor = image_tensor.permute(0, 3, 1, 2)  # (N, H, W, C) -> (N, C, H, W)
        
        ndvi_tensor = None
        if ndvis:
            ndvi_tensor = torch.from_numpy(np.array(ndvis)).float()
        
        return image_tensor, ndvi_tensor


class DeforestationDataset(Dataset):
    """
    PyTorch Dataset for deforestation detection.
    
    STEP 3: Label Management
    Loads and manages training data with labels.
    """
    
    def __init__(
        self,
        image_paths: List[str],
        labels: List[int],
        preprocessor: Sentinel2Preprocessor,
        transform=None
    ):
        """
        Initialize dataset.
        
        Args:
            image_paths: List of paths to image files
            labels: List of labels (0: Forest, 1: Deforested)
            preprocessor: Sentinel2Preprocessor instance
            transform: Optional additional transforms
        """
        self.image_paths = image_paths
        self.labels = labels
        self.preprocessor = preprocessor
        self.transform = transform
        
        assert len(image_paths) == len(labels), "Mismatch between images and labels"
        
        logger.info(f"Dataset created: {len(self)} samples")
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        """
        Get a single sample.
        
        Returns:
            Tuple of (image_tensor, label, ndvi_tensor)
        """
        # Load image bands
        # This is a simplified version - actual implementation would load from raster files
        image_path = self.image_paths[idx]
        label = self.labels[idx]
        
        # TODO: Implement actual band loading from GeoTIFF files
        # For now, return placeholder
        
        return {
            'image': torch.zeros(4, 224, 224),  # Placeholder
            'label': torch.tensor(label),
            'ndvi': torch.zeros(224, 224),
            'path': image_path
        }


# STEP 2: Output - Clean, standardized image tensors ready for CNN input
def create_preprocessor(target_size=(224, 224), normalize=True, compute_ndvi=True):
    """Factory function to create a preprocessor."""
    return Sentinel2Preprocessor(target_size, normalize, compute_ndvi)


if __name__ == "__main__":
    # Test preprocessing
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Sentinel-2 Preprocessor...")
    preprocessor = create_preprocessor()
    
    # Create dummy bands
    dummy_bands = {
        'B2': np.random.randint(0, 10000, (512, 512)),
        'B3': np.random.randint(0, 10000, (512, 512)),
        'B4': np.random.randint(0, 10000, (512, 512)),
        'B8': np.random.randint(0, 10000, (512, 512))
    }
    
    # Preprocess
    image, ndvi = preprocessor.preprocess_image(dummy_bands)
    
    print(f"\nPreprocessing results:")
    print(f"Image shape: {image.shape}")
    print(f"NDVI shape: {ndvi.shape if ndvi is not None else 'None'}")
    print(f"Image range: [{image.min():.3f}, {image.max():.3f}]")
    if ndvi is not None:
        print(f"NDVI range: [{ndvi.min():.3f}, {ndvi.max():.3f}]")
