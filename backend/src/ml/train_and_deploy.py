"""
Complete ML Training and Deployment Guide

This script demonstrates the complete workflow from data preparation
to model training and deployment for deforestation detection.

STEPS COVERED:
1. Data preparation and loading
2. Model initialization
3. Training with validation
4. Model evaluation
5. Saving and deployment
"""

import sys
from pathlib import Path
import logging
import torch
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ml.model import create_model
from src.ml.preprocessing import create_preprocessor, DeforestationDataset
from src.ml.training import train_model
from src.ml.inference import create_detector
from src.ml.postprocessing import create_post_processor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def step_1_prepare_data():
    """
    STEP 1-3: Data Preparation
    
    In a real scenario, you would:
    1. Download BigEarthNet dataset
    2. Extract Sentinel-2 images for Zimbabwe region
    3. Label images as Forest/Deforested
    4. Organize into training dataset
    
    For this example, we'll create a placeholder.
    """
    logger.info("="*80)
    logger.info("STEP 1-3: DATA PREPARATION")
    logger.info("="*80)
    
    # In real implementation:
    # - Load BigEarthNet labels
    # - Map to binary classes (Forest/Non-Forest)
    # - Create image dataset from GEE downloads
    
    logger.info("""
    To prepare your dataset:
    
    1. Download Sentinel-2 images:
       - Use Google Earth Engine (GEE)
       - Download for Zimbabwe forest regions
       - Time period: Last 2-3 years
       - Bands: B2, B3, B4, B8 (RGB + NIR)
    
    2. Label the data:
       - Manual labeling or use existing labeled dataset
       - Classes: 0 = Forest, 1 = Deforested
       - Recommended: At least 1000 samples per class
    
    3. Organize structure:
       data/
         ├── images/
         │   ├── forest/
         │   └── deforested/
         └── labels.json
    """)
    
    # Placeholder dataset (replace with real data)
    # image_paths = ["data/images/sample1.tif", "data/images/sample2.tif", ...]
    # labels = [0, 1, ...]  # 0=Forest, 1=Deforested
    
    return None  # Return actual dataset in real implementation


def step_2_create_model():
    """
    STEP 4: Create ResNet-50 Model
    """
    logger.info("="*80)
    logger.info("STEP 4: MODEL CREATION")
    logger.info("="*80)
    
    # Create model with ResNet-50 backbone
    model = create_model(
        num_classes=2,  # Forest vs Deforested
        input_channels=4,  # RGB + NIR
        freeze_backbone=True  # Transfer learning
    )
    
    logger.info(f"Model created successfully!")
    logger.info(f"Total parameters: {model.get_num_total_params():,}")
    logger.info(f"Trainable parameters: {model.get_num_trainable_params():,}")
    logger.info(f"Percentage trainable: {model.get_num_trainable_params() / model.get_num_total_params() * 100:.1f}%")
    
    return model


def step_3_train_model(model, dataset):
    """
    STEP 5: Train the Model
    """
    logger.info("="*80)
    logger.info("STEP 5: MODEL TRAINING")
    logger.info("="*80)
    
    if dataset is None:
        logger.warning("No dataset provided. Skipping training.")
        logger.info("""
        To train the model with your data:
        
        from src.ml.training import train_model
        
        trained_model, history = train_model(
            model=model,
            dataset=your_dataset,
            epochs=20,
            batch_size=32,
            learning_rate=0.001,
            save_dir='models/checkpoints'
        )
        """)
        return model, None
    
    # Train model
    trained_model, history = train_model(
        model=model,
        dataset=dataset,
        epochs=20,
        batch_size=32,
        learning_rate=0.001,
        save_dir='models/checkpoints'
    )
    
    return trained_model, history


def step_4_save_model(model):
    """
    STEP 6: Save Model
    """
    logger.info("="*80)
    logger.info("STEP 6: MODEL SAVING")
    logger.info("="*80)
    
    model_dir = Path('models')
    model_dir.mkdir(exist_ok=True)
    
    model_path = model_dir / 'best_model.pth'
    model.save(model_path)
    
    logger.info(f"✓ Model saved to {model_path}")
    logger.info(f"  File size: {model_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    return model_path


def step_5_test_inference(model_path):
    """
    STEP 7: Test Inference
    """
    logger.info("="*80)
    logger.info("STEP 7: INFERENCE TESTING")
    logger.info("="*80)
    
    # Create detector
    detector = create_detector(
        model_path=str(model_path),
        confidence_threshold=0.7,
        ndvi_drop_threshold=-0.1
    )
    
    logger.info("✓ Detector initialized")
    logger.info(f"  Device: {detector.device}")
    logger.info(f"  Confidence threshold: {detector.confidence_threshold}")
    
    # Test with dummy data
    logger.info("\nTesting with dummy Sentinel-2 bands...")
    dummy_bands = {
        'B2': np.random.randint(0, 10000, (512, 512)),
        'B3': np.random.randint(0, 10000, (512, 512)),
        'B4': np.random.randint(0, 10000, (512, 512)),
        'B8': np.random.randint(0, 10000, (512, 512))
    }
    
    result = detector.predict_single(dummy_bands)
    
    logger.info(f"\nInference result:")
    logger.info(f"  Prediction: {result['prediction']}")
    logger.info(f"  Confidence: {result['confidence']:.2%}")
    logger.info(f"  NDVI mean: {result['ndvi_mean']:.3f}")
    
    logger.info("""
    To use the detector on real images:
    
    # Single image prediction
    result = detector.predict_from_file('path/to/sentinel2_image.tif')
    
    # Change detection between two dates
    change_result = detector.detect_change(
        before_bands=before_image_bands,
        after_bands=after_image_bands
    )
    """)
    
    return detector


def step_6_deployment_instructions():
    """
    STEPS 9-10: Backend and Frontend Integration
    """
    logger.info("="*80)
    logger.info("STEPS 9-10: DEPLOYMENT")
    logger.info("="*80)
    
    logger.info("""
    BACKEND INTEGRATION:
    
    1. The ML API endpoints are already created in:
       backend/src/ml/api_integration.py
    
    2. Add to your main API server (api_server.py):
       
       from src.ml.api_integration import ml_router, initialize_ml_system
       
       # Add router
       app.include_router(ml_router)
       
       # Initialize on startup
       @app.on_event("startup")
       async def startup():
           initialize_ml_system()
    
    3. Available endpoints:
       - POST /api/ml/run-ml-detection
       - POST /api/ml/detect-change
       - GET  /api/ml/detections/recent
       - GET  /api/ml/statistics
       - GET  /api/ml/status
       - GET  /api/ml/model/info
    
    FRONTEND INTEGRATION:
    
    The frontend will call these endpoints to:
    - Display ML detection results
    - Show before/after images
    - Visualize NDVI heatmaps
    - Generate detection reports
    
    Example frontend call:
    
    fetch('http://localhost:8001/api/ml/run-ml-detection?image_path=/path/to/image.tif')
        .then(res => res.json())
        .then(data => {
            console.log('Prediction:', data.prediction);
            console.log('Confidence:', data.confidence);
            // Display on map
        });
    """)


def main():
    """
    Complete workflow execution.
    """
    logger.info("="*80)
    logger.info("DEFORESTATION DETECTION ML PIPELINE")
    logger.info("ResNet-50 with Transfer Learning")
    logger.info("="*80)
    
    # Step 1-3: Prepare data
    dataset = step_1_prepare_data()
    
    # Step 4: Create model
    model = step_2_create_model()
    
    # Step 5: Train model
    trained_model, history = step_3_train_model(model, dataset)
    
    # Step 6: Save model
    model_path = step_4_save_model(trained_model)
    
    # Step 7: Test inference
    detector = step_5_test_inference(model_path)
    
    # Steps 9-10: Deployment instructions
    step_6_deployment_instructions()
    
    logger.info("="*80)
    logger.info("SETUP COMPLETE!")
    logger.info("="*80)
    logger.info("""
    Next steps:
    
    1. Prepare your real dataset (Sentinel-2 images + labels)
    2. Run this script with your dataset
    3. Integrate ML API into backend server
    4. Update frontend to display ML results
    5. Test end-to-end detection workflow
    
    For questions or issues, refer to the documentation in each module.
    """)


if __name__ == "__main__":
    main()
