"""
Inference Engine for Real-Time Deforestation Detection

STEP 7: Inference (Real Use)
- Load trained model
- Process new Sentinel-2 images
- Make predictions
- Generate detection results with confidence scores
"""

import torch
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, mapping
import geopandas as gpd

from .model import DeforestationCNN
from .preprocessing import Sentinel2Preprocessor

logger = logging.getLogger(__name__)


class DeforestationDetector:
    """
    Real-time deforestation detection using trained CNN model.
    
    STEP 7: Complete inference pipeline
    - Loads trained model
    - Preprocesses images
    - Makes predictions
    - Outputs detection zones with confidence
    """
    
    def __init__(
        self,
        model_path: str,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        confidence_threshold: float = 0.7,
        ndvi_drop_threshold: float = -0.1
    ):
        """
        Initialize the detector.
        
        Args:
            model_path: Path to trained model checkpoint
            device: Device to run inference on
            confidence_threshold: Minimum confidence for detection (0-1)
            ndvi_drop_threshold: Minimum NDVI drop to flag deforestation
        """
        self.device = device
        self.confidence_threshold = confidence_threshold
        self.ndvi_drop_threshold = ndvi_drop_threshold
        
        # Load model
        logger.info(f"Loading model from {model_path}")
        self.model = DeforestationCNN.load(model_path, device=device)
        self.model.eval()
        
        # Initialize preprocessor
        self.preprocessor = Sentinel2Preprocessor(
            target_size=(224, 224),
            normalize=True,
            compute_ndvi=True
        )
        
        logger.info(f"Detector initialized on {device}")
        logger.info(f"Confidence threshold: {confidence_threshold}")
        logger.info(f"NDVI drop threshold: {ndvi_drop_threshold}")
    
    def preprocess_image(
        self,
        bands: Dict[str, np.ndarray],
        qa_band: Optional[np.ndarray] = None
    ) -> Tuple[torch.Tensor, np.ndarray]:
        """
        Preprocess a single image for inference.
        
        STEP 7: Image preprocessing
        
        Args:
            bands: Dictionary of band arrays
            qa_band: Optional QA band for cloud masking
        
        Returns:
            Tuple of (image_tensor, ndvi_array)
        """
        # Preprocess using the pipeline
        image, ndvi = self.preprocessor.preprocess_image(bands, qa_band)
        
        # Convert to tensor
        image_tensor = torch.from_numpy(image).float()
        image_tensor = image_tensor.permute(2, 0, 1)  # (H, W, C) -> (C, H, W)
        image_tensor = image_tensor.unsqueeze(0)  # Add batch dimension
        
        return image_tensor.to(self.device), ndvi
    
    def predict_single(
        self,
        bands: Dict[str, np.ndarray],
        qa_band: Optional[np.ndarray] = None,
        return_probabilities: bool = True
    ) -> Dict:
        """
        Make prediction on a single image.
        
        STEP 7: Model inference
        
        Args:
            bands: Dictionary of band arrays
            qa_band: Optional QA band
            return_probabilities: Whether to return class probabilities
        
        Returns:
            Dictionary with prediction results
        """
        # Preprocess
        image_tensor, ndvi = self.preprocess_image(bands, qa_band)
        
        # Predict
        with torch.no_grad():
            logits = self.model(image_tensor)
            probs = torch.softmax(logits, dim=1)
            pred_class = torch.argmax(probs, dim=1).item()
            confidence = probs[0, pred_class].item()
        
        # Prepare result
        result = {
            'prediction': 'Deforested' if pred_class == 1 else 'Forest',
            'class_id': pred_class,
            'confidence': confidence,
            'ndvi_mean': float(np.mean(ndvi)) if ndvi is not None else None,
            'ndvi_std': float(np.std(ndvi)) if ndvi is not None else None,
            'timestamp': datetime.now().isoformat()
        }
        
        if return_probabilities:
            result['probabilities'] = {
                'forest': float(probs[0, 0]),
                'deforested': float(probs[0, 1])
            }
        
        return result
    
    def detect_change(
        self,
        before_bands: Dict[str, np.ndarray],
        after_bands: Dict[str, np.ndarray],
        before_qa: Optional[np.ndarray] = None,
        after_qa: Optional[np.ndarray] = None
    ) -> Dict:
        """
        Detect deforestation change between two time periods.
        
        STEP 7: Change detection workflow
        Checks both NDVI drop and model prediction
        
        Args:
            before_bands: Bands from earlier date
            after_bands: Bands from later date
            before_qa: QA band for before image
            after_qa: QA band for after image
        
        Returns:
            Detection result dictionary
        """
        # Predict on both images
        before_result = self.predict_single(before_bands, before_qa)
        after_result = self.predict_single(after_bands, after_qa)
        
        # Calculate NDVI change
        ndvi_change = after_result['ndvi_mean'] - before_result['ndvi_mean']
        
        # Determine if deforestation occurred
        # STEP 7: If NDVI drop + deforested → flag area
        is_deforested = (
            after_result['class_id'] == 1 and  # After image shows deforestation
            before_result['class_id'] == 0 and  # Before image shows forest
            after_result['confidence'] >= self.confidence_threshold and
            ndvi_change <= self.ndvi_drop_threshold  # Significant NDVI drop
        )
        
        result = {
            'deforestation_detected': is_deforested,
            'before': {
                'prediction': before_result['prediction'],
                'confidence': before_result['confidence'],
                'ndvi': before_result['ndvi_mean']
            },
            'after': {
                'prediction': after_result['prediction'],
                'confidence': after_result['confidence'],
                'ndvi': after_result['ndvi_mean']
            },
            'change': {
                'ndvi_change': float(ndvi_change),
                'ndvi_drop_percent': float((ndvi_change / before_result['ndvi_mean']) * 100)
                    if before_result['ndvi_mean'] != 0 else 0,
                'meets_ndvi_threshold': ndvi_change <= self.ndvi_drop_threshold,
                'meets_confidence_threshold': after_result['confidence'] >= self.confidence_threshold
            },
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(
            f"Change detection: {result['deforestation_detected']} | "
            f"NDVI: {before_result['ndvi_mean']:.3f} -> {after_result['ndvi_mean']:.3f} "
            f"({ndvi_change:+.3f}) | "
            f"Confidence: {after_result['confidence']:.2%}"
        )
        
        return result
    
    def batch_detect(
        self,
        batch_bands: List[Dict[str, np.ndarray]],
        qa_bands: Optional[List[np.ndarray]] = None
    ) -> List[Dict]:
        """
        Run detection on a batch of images.
        
        Args:
            batch_bands: List of band dictionaries
            qa_bands: List of QA bands
        
        Returns:
            List of prediction results
        """
        if qa_bands is None:
            qa_bands = [None] * len(batch_bands)
        
        results = []
        for bands, qa in zip(batch_bands, qa_bands):
            result = self.predict_single(bands, qa)
            results.append(result)
        
        return results
    
    def predict_from_file(
        self,
        image_path: str,
        band_indices: Dict[str, int] = None
    ) -> Dict:
        """
        Make prediction from a GeoTIFF file.
        
        Args:
            image_path: Path to multi-band GeoTIFF
            band_indices: Mapping of band names to indices
        
        Returns:
            Prediction result
        """
        if band_indices is None:
            # Default Sentinel-2 band order
            band_indices = {'B2': 1, 'B3': 2, 'B4': 3, 'B8': 4}
        
        # Load bands from file
        with rasterio.open(image_path) as src:
            bands = {}
            for band_name, idx in band_indices.items():
                bands[band_name] = src.read(idx)
            
            # Get metadata for georeferencing
            transform = src.transform
            crs = src.crs
        
        # Make prediction
        result = self.predict_single(bands)
        result['file_path'] = image_path
        result['crs'] = str(crs)
        result['transform'] = transform.to_gdal()
        
        return result
    
    def create_detection_map(
        self,
        predictions: np.ndarray,
        confidence_map: np.ndarray,
        transform,
        crs,
        output_path: str
    ):
        """
        Create a georeferenced detection map.
        
        STEP 8: Post-processing - Convert predictions to geo-referenced polygons
        
        Args:
            predictions: Array of pixel-wise predictions
            confidence_map: Array of confidence scores
            transform: Rasterio transform
            crs: Coordinate reference system
            output_path: Path to save the detection map
        """
        # Create binary mask for deforestation
        deforestation_mask = (predictions == 1) & (confidence_map >= self.confidence_threshold)
        
        # Convert to polygons
        logger.info("Converting predictions to polygons...")
        geoms = []
        values = []
        
        for geom, value in shapes(deforestation_mask.astype(np.uint8), transform=transform):
            if value == 1:  # Deforestation detected
                geoms.append(shape(geom))
                values.append(1)
        
        if not geoms:
            logger.warning("No deforestation zones detected")
            return None
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame({
            'geometry': geoms,
            'deforestation': values,
            'detection_date': datetime.now().isoformat()
        }, crs=crs)
        
        # Calculate area in hectares
        gdf['area_hectares'] = gdf.geometry.area / 10000
        
        # Save to file
        gdf.to_file(output_path, driver='GeoJSON')
        logger.info(f"Detection map saved to {output_path}")
        logger.info(f"Total deforested area: {gdf['area_hectares'].sum():.2f} hectares")
        
        return gdf


class DetectionPipeline:
    """
    Complete end-to-end detection pipeline.
    
    STEP 7: When new Sentinel-2 image arrives
    """
    
    def __init__(self, detector: DeforestationDetector):
        """Initialize pipeline with a detector."""
        self.detector = detector
        logger.info("Detection pipeline initialized")
    
    def run_detection(
        self,
        image_path: str,
        output_dir: str = 'detections'
    ) -> Dict:
        """
        Run complete detection pipeline on a new image.
        
        STEP 7: Complete workflow
        1. Backend triggers ML pipeline
        2. Image is preprocessed, resized, normalized
        3. Image is fed into trained ResNet
        4. Model outputs: Forest/Deforested
        5. NDVI drop is checked
        6. If NDVI drop + deforested → flag area
        
        Args:
            image_path: Path to Sentinel-2 image
            output_dir: Directory to save results
        
        Returns:
            Detection results dictionary
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Running detection pipeline on {image_path}")
        
        # 1. Backend triggers ML pipeline
        # 2-3. Image preprocessing and inference
        result = self.detector.predict_from_file(image_path)
        
        # Save results
        result_path = output_dir / f"detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Detection complete: {result['prediction']} (confidence: {result['confidence']:.2%})")
        logger.info(f"Results saved to {result_path}")
        
        return result


def create_detector(
    model_path: str,
    confidence_threshold: float = 0.7,
    ndvi_drop_threshold: float = -0.1
) -> DeforestationDetector:
    """
    Factory function to create a detector.
    
    STEP 7: Load and ready the inference engine
    """
    return DeforestationDetector(
        model_path=model_path,
        confidence_threshold=confidence_threshold,
        ndvi_drop_threshold=ndvi_drop_threshold
    )


if __name__ == "__main__":
    # Test inference
    logging.basicConfig(level=logging.INFO)
    
    print("Inference engine test...")
    print("To use: detector = create_detector('path/to/model.pth')")
    print("Then: result = detector.predict_single(bands)")
