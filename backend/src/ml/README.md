# 🧠 Machine Learning Module for Deforestation Detection

Complete implementation of ResNet-50 based CNN with transfer learning for automated deforestation detection from Sentinel-2 satellite imagery.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Complete Workflow](#complete-workflow)
- [API Integration](#api-integration)
- [Module Reference](#module-reference)

## 🎯 Overview

This ML module implements a **12-step comprehensive pipeline** for deforestation detection:

### ✅ Implemented Steps

1. **ML Architecture**: ResNet-50 with BigEarthNet transfer learning
2. **Data Pipeline**: Sentinel-2 preprocessing (cloud masking, NDVI, normalization)
3. **Label Management**: Binary classification (Forest/Deforested)
4. **Model Setup**: Transfer learning with frozen backbone
5. **Training Process**: 70/15/15 split, Adam optimizer, BCE loss
6. **Model Persistence**: Save/load trained models
7. **Inference**: Real-time prediction on new images
8. **Post-Processing**: Geo-referenced polygon generation
9. **Backend Integration**: FastAPI endpoints
10. **Frontend Integration**: Ready for UI display
11. **Results & Reporting**: Automated report generation
12. **Testing & Validation**: Comprehensive metrics

## 🏗️ Architecture

```
ResNet-50 Backbone (Pretrained on ImageNet)
    ↓
Transfer Learning (Fine-tuned on BigEarthNet)
    ↓
Custom Classification Head
    ↓
Binary Output: Forest (0) vs Deforested (1)
```

### Model Specifications

- **Input**: 4-channel images (224×224)
  - B2 (Blue)
  - B3 (Green)
  - B4 (Red)
  - B8 (NIR)
- **Backbone**: ResNet-50 (pretrained)
- **Output**: 2 classes (Forest/Deforested)
- **Parameters**: ~23M total, ~2M trainable (with frozen backbone)

## 📦 Installation

### 1. Install PyTorch

```bash
# CPU version
pip install torch torchvision torchaudio

# GPU version (CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Required packages:
- torch >= 2.0.0
- torchvision >= 0.15.0
- rasterio >= 1.3.0
- geopandas >= 0.10.0
- scikit-learn >= 1.0.0
- scikit-image >= 0.19.0

## 🚀 Quick Start

### 1. Test Model Creation

```python
from src.ml.model import create_model

# Create model
model = create_model(
    num_classes=2,
    input_channels=4,
    freeze_backbone=True
)

print(f"Model created with {model.get_num_total_params():,} parameters")
```

### 2. Test Preprocessing

```python
from src.ml.preprocessing import create_preprocessor
import numpy as np

# Create preprocessor
preprocessor = create_preprocessor()

# Prepare dummy Sentinel-2 bands
bands = {
    'B2': np.random.randint(0, 10000, (512, 512)),
    'B3': np.random.randint(0, 10000, (512, 512)),
    'B4': np.random.randint(0, 10000, (512, 512)),
    'B8': np.random.randint(0, 10000, (512, 512))
}

# Preprocess
image, ndvi = preprocessor.preprocess_image(bands)
print(f"Preprocessed image shape: {image.shape}")
print(f"NDVI shape: {ndvi.shape}")
```

### 3. Run Complete Workflow

```bash
cd backend
python src/ml/train_and_deploy.py
```

This will guide you through all 12 steps.

## 📖 Complete Workflow

### STEP 1-3: Data Preparation

```python
from src.ml.preprocessing import Sentinel2Preprocessor, DeforestationDataset

# 1. Prepare your dataset
# - Download Sentinel-2 images for Zimbabwe
# - Label as Forest (0) or Deforested (1)
# - Organize into image_paths and labels lists

preprocessor = Sentinel2Preprocessor(
    target_size=(224, 224),
    normalize=True,
    compute_ndvi=True
)

dataset = DeforestationDataset(
    image_paths=image_paths,
    labels=labels,
    preprocessor=preprocessor
)
```

### STEP 4-6: Model Training

```python
from src.ml.model import create_model
from src.ml.training import train_model

# Create model
model = create_model(
    num_classes=2,
    input_channels=4,
    freeze_backbone=True
)

# Train
trained_model, history = train_model(
    model=model,
    dataset=dataset,
    epochs=20,
    batch_size=32,
    learning_rate=0.001,
    save_dir='models/checkpoints'
)

# Model automatically saved to models/checkpoints/best_model.pth
```

### STEP 7: Inference

```python
from src.ml.inference import create_detector

# Load trained model
detector = create_detector(
    model_path='models/best_model.pth',
    confidence_threshold=0.7,
    ndvi_drop_threshold=-0.1
)

# Single image prediction
result = detector.predict_from_file('path/to/sentinel2_image.tif')
print(f"Prediction: {result['prediction']}")
print(f"Confidence: {result['confidence']:.2%}")

# Change detection between two dates
change_result = detector.detect_change(
    before_bands=before_bands,
    after_bands=after_bands
)

if change_result['deforestation_detected']:
    print(f"⚠️ Deforestation detected!")
    print(f"NDVI change: {change_result['change']['ndvi_change']:.3f}")
```

### STEP 8: Post-Processing

```python
from src.ml.postprocessing import create_post_processor

post_processor = create_post_processor(
    min_area_hectares=0.5,
    simplify_tolerance=0.0001
)

# Convert predictions to polygons
polygons = post_processor.predictions_to_polygons(
    predictions=predictions_array,
    confidence_map=confidence_array,
    transform=raster_transform
)

# Create GeoDataFrame
gdf = post_processor.create_detection_geodataframe(
    polygon_data=polygons,
    crs='EPSG:4326'
)

# Generate report
report = post_processor.generate_detection_report(
    gdf=gdf,
    output_path='reports/detection_report.json'
)

# Save in multiple formats
post_processor.save_detections(
    gdf=gdf,
    output_dir='detections',
    formats=['geojson', 'shapefile', 'kml']
)
```

## 🔌 API Integration

### 1. Add to Backend Server

Edit `backend/api_server.py`:

```python
from src.ml.api_integration import ml_router, initialize_ml_system

# Add router
app.include_router(ml_router)

# Initialize on startup
@app.on_event("startup")
async def startup():
    initialize_ml_system()
```

### 2. Available Endpoints

#### Run ML Detection
```http
POST /api/ml/run-ml-detection?image_path=/path/to/image.tif
```

Response:
```json
{
  "status": "success",
  "prediction": "Deforested",
  "confidence": 0.89,
  "coordinates": {
    "latitude": -20.1667,
    "longitude": 28.5833
  },
  "ndvi_mean": 0.24,
  "ndvi_std": 0.08,
  "detection_date": "2026-01-16T12:00:00",
  "image_path": "/path/to/image.tif"
}
```

#### Detect Change
```http
POST /api/ml/detect-change
  ?before_image=/path/to/before.tif
  &after_image=/path/to/after.tif
  &before_date=2025-01-01
  &after_date=2026-01-01
```

#### Get Recent Detections
```http
GET /api/ml/detections/recent?limit=50
```

#### Get Statistics
```http
GET /api/ml/statistics
```

#### Model Info
```http
GET /api/ml/model/info
```

#### System Status
```http
GET /api/ml/status
```

### 3. Frontend Integration

```typescript
// Fetch ML detection
async function runMLDetection(imagePath: string) {
  const response = await fetch(
    `http://localhost:8001/api/ml/run-ml-detection?image_path=${imagePath}`
  );
  const data = await response.json();
  
  // Display results
  console.log('Prediction:', data.prediction);
  console.log('Confidence:', data.confidence);
  
  // Update map with detection coordinates
  displayOnMap(data.coordinates, data.prediction);
}

// Get detection statistics
async function getMLStats() {
  const response = await fetch('http://localhost:8001/api/ml/statistics');
  const stats = await response.json();
  
  // Display in dashboard
  updateDashboard({
    totalDetections: stats.total_detections,
    deforestationRate: stats.deforestation_rate,
    avgConfidence: stats.average_confidence
  });
}
```

## 📚 Module Reference

### `model.py` - ResNet-50 Architecture
- `DeforestationCNN`: Main model class
- `create_model()`: Factory function
- Methods: `forward()`, `predict()`, `save()`, `load()`

### `preprocessing.py` - Data Pipeline
- `Sentinel2Preprocessor`: Image preprocessing
- `DeforestationDataset`: PyTorch dataset
- Methods: `preprocess_image()`, `calculate_ndvi()`, `apply_cloud_mask()`

### `training.py` - Model Training
- `ModelTrainer`: Training orchestrator
- `train_model()`: Complete training workflow
- Metrics: Accuracy, Precision, Recall, F1-Score

### `inference.py` - Real-Time Detection
- `DeforestationDetector`: Inference engine
- `DetectionPipeline`: End-to-end pipeline
- Methods: `predict_single()`, `detect_change()`, `batch_detect()`

### `postprocessing.py` - Result Processing
- `DetectionPostProcessor`: Result processor
- Methods: `predictions_to_polygons()`, `generate_detection_report()`, `save_detections()`

### `api_integration.py` - Backend API
- `ml_router`: FastAPI router
- `initialize_ml_system()`: Startup initialization
- All API endpoints

## 🎓 Training Your Model

### 1. Prepare Dataset

```
data/
├── train/
│   ├── forest/
│   │   ├── image_001.tif
│   │   └── ...
│   └── deforested/
│       ├── image_001.tif
│       └── ...
└── labels.json
```

### 2. Train

```python
python src/ml/train_and_deploy.py
```

Or programmatically:

```python
from src.ml.model import create_model
from src.ml.training import train_model

model = create_model()
trained_model, history = train_model(
    model=model,
    dataset=your_dataset,
    epochs=20
)
```

### 3. Monitor Training

Training metrics are automatically plotted and saved:
- Loss curves
- Accuracy curves
- Precision/Recall/F1
- Confusion matrix

Files saved:
- `models/checkpoints/best_model.pth`
- `models/checkpoints/training_history.json`
- `models/checkpoints/training_plots.png`
- `models/checkpoints/test_metrics.json`

## 🧪 Testing

Test each component:

```bash
# Test model
python src/ml/model.py

# Test preprocessing
python src/ml/preprocessing.py

# Test inference
python src/ml/inference.py

# Test post-processing
python src/ml/postprocessing.py
```

## 📊 Performance Metrics

Expected performance (with proper training):
- **Accuracy**: > 90%
- **Precision**: > 85%
- **Recall**: > 85%
- **F1-Score**: > 85%

## 🛠️ Troubleshooting

### Model not loading
```python
# Check model path
from pathlib import Path
model_path = Path('models/best_model.pth')
print(f"Model exists: {model_path.exists()}")
```

### CUDA out of memory
```python
# Reduce batch size
train_model(model, dataset, batch_size=16)  # Instead of 32
```

### Slow training
```python
# Freeze more layers
model.unfreeze_layers(num_layers=2)  # Only unfreeze last 2 layers
```

## 📝 License

Part of the Deforestation Detection Project

## 🤝 Contributing

For questions or contributions, refer to the main project documentation.

---

**Status**: ✅ Fully Implemented (All 12 Steps)  
**Last Updated**: 2026-01-16  
**Version**: 1.0.0
