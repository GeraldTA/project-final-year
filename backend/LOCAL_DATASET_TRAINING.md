# Local Labeled Dataset Training Pipeline

## Overview

This guide explains how to train the deforestation detection model using a **locally stored labeled dataset** instead of fetching data from Hugging Face during training. This eliminates repeated remote downloads and allows training with custom datasets.

## Architecture

```
backend/data/
├── labels.json              # Master manifest file (auto-generated or manual)
└── raw/
    ├── forest/              # Class 0: Healthy forest
    │   ├── image_001.tif
    │   ├── image_002.tif
    │   └── ...
    └── deforested/          # Class 1: Deforested areas
        ├── image_001.tif
        ├── image_002.tif
        └── ...
```

## Step 1: Organize Training Data

Place your Sentinel-2 GeoTIFF images in the correct directory structure:

```bash
# Create class directories
mkdir -p backend/data/raw/forest
mkdir -p backend/data/raw/deforested

# Copy your GeoTIFF images
cp /path/to/forest/images/*.tif backend/data/raw/forest/
cp /path/to/deforested/images/*.tif backend/data/raw/deforested/
```

**Image Requirements:**
- Format: GeoTIFF (.tif or .tiff)
- Bands: 10-band Sentinel-2 or 4-band (B2, B3, B4, B8)
- Size: Any (will be resized to 224x224 during preprocessing)
- Cloud coverage: Ideally <10% (but pipeline handles clouds)

## Step 2: Generate Labels Manifest

### Option A: Auto-Generate from Directory Structure

```bash
cd backend
python scripts/create_labels_manifest.py \
  --data-dir backend/data/raw \
  --output backend/data/labels.json \
  --train-ratio 0.7 \
  --val-ratio 0.15 \
  --test-ratio 0.15
```

This will:
1. Scan `forest/` and `deforested/` directories
2. Automatically assign labels (0 and 1)
3. Randomly split into train/val/test (70/15/15)
4. Create `backend/data/labels.json`

### Option B: Manual Labels File

Create `backend/data/labels.json` manually:

```json
{
  "base_dir": ".",
  "description": "Training labels for deforestation detection",
  "samples": [
    {
      "image_path": "data/raw/forest/image_001.tif",
      "label": 0,
      "split": "train",
      "region": "Zimbabwe",
      "date": "2023-01-15"
    },
    {
      "image_path": "data/raw/deforested/image_001.tif",
      "label": 1,
      "split": "train",
      "region": "Zimbabwe",
      "date": "2023-01-15"
    },
    {
      "image_path": "data/raw/forest/image_002.tif",
      "label": 0,
      "split": "val",
      "region": "Zimbabwe",
      "date": "2023-02-20"
    }
  ]
}
```

**Labels:**
- `0` = Forest (no deforestation)
- `1` = Deforested area

**Split:**
- `train` - Used for training (typically 70%)
- `val` - Used for validation during training (typically 15%)
- `test` - Used for final evaluation (typically 15%)

## Step 3: Train the Model

### Quick Start

```bash
cd backend
python -c "from src.ml.train_from_local import train_local; train_local()"
```

### Full Training with Options

```bash
python src/ml/train_from_local.py \
  --labels backend/data/labels.json \
  --model-dir backend/models \
  --epochs 30 \
  --batch-size 32 \
  --learning-rate 0.001 \
  --device cuda
```

**Arguments:**
- `--labels`: Path to labels.json manifest
- `--model-dir`: Where to save model checkpoints
- `--epochs`: Number of training epochs (default: 30)
- `--batch-size`: Batch size (default: 32; reduce if GPU memory is limited)
- `--learning-rate`: Optimizer learning rate (default: 0.001)
- `--device`: Training device (`cuda` for GPU, `cpu` for CPU; auto-detected by default)

### From Python Code

```python
from src.ml.train_from_local import train_local

# Train with default settings
results = train_local()

# Or customize
results = train_local(
    labels_file='backend/data/labels.json',
    model_save_dir='backend/models',
    num_epochs=50,
    batch_size=16,
    learning_rate=0.0005,
    device='cuda'
)

print(f"Test accuracy: {results['test_metrics']['accuracy']:.2%}")
```

## Step 4: Monitor Training

The trainer will display:
- Epoch progress with loss and accuracy
- Validation metrics every epoch
- Best model checkpoint saved automatically

Output files saved to `backend/models/`:
- `best_model.pth` - Best checkpoint (lowest validation loss)
- `final_model.pth` - Final model after all epochs
- `training_summary_YYYYMMDD_HHMMSS.json` - Detailed metrics and history
- `checkpoint_epoch_*.pth` - Intermediate checkpoints (every 5 epochs)

## Step 5: Use Trained Model for Inference

Once training is complete, your detector automatically uses the local weights:

```python
from src.ml.bigearthnet_detector import BigEarthNetDetector

# Initialize detector (uses local models automatically)
detector = BigEarthNetDetector()

# Perform inference
result = detector.detect_deforestation_from_tif(
    image_path='path/to/sentinel2_image.tif',
    area_name='Zimbabwe_Forest_01'
)

print(f"Deforestation probability: {result['deforestation_probability']:.2%}")
print(f"Vegetation health (NDVI): {result['ndvi_mean']:.2f}")
```

## Dataset Structure Details

### DeforestationDataset Class

The `DeforestationDataset` class handles:
- Loading from labels.json manifest
- Automatic train/val/test splitting
- GeoTIFF band extraction (10-band and 4-band support)
- Preprocessing (resizing, normalization, NDVI calculation)
- Label validation

### Preprocessing Pipeline

Each image goes through:
1. **Band Extraction**: Extract B2, B3, B4, B8 from GeoTIFF
2. **Cloud Masking**: Remove cloudy pixels if QA band provided
3. **Resizing**: Resize to 224x224 (ResNet input size)
4. **Normalization**: Standardize using Sentinel-2 statistics
5. **NDVI Calculation**: Compute vegetation index from NIR and Red bands

## Troubleshooting

### Error: "No samples found in labels file"
- Check that labels.json exists and is valid JSON
- Verify image paths in labels.json point to real files
- Run `python scripts/create_labels_manifest.py` to auto-generate

### Error: "Missing file"
- Check that all image paths in labels.json are correct
- Verify .tif files exist in the specified locations
- Use absolute paths if relative paths don't work

### Error: "Invalid label"
- Labels must be 0 (forest) or 1 (deforested)
- Check labels.json for typos in label values

### GPU Out of Memory
- Reduce batch size: `--batch-size 8`
- Reduce image resolution (edit preprocessing.py)
- Train on CPU: `--device cpu`

### Slow Training
- If CPU is slow, try GPU: ensure CUDA is installed and `torch` can access it
- Check with: `python -c "import torch; print(torch.cuda.is_available())"`

## Comparison: Local vs Hugging Face Training

| Aspect | Local Dataset | Hugging Face |
|--------|---------------|--------------|
| Initial Download | Once (manual) | Every training session |
| Network Dependency | No (after setup) | Yes, during training |
| Training Speed | Fast | Depends on internet |
| Custom Data | Yes | Limited to BigEarthNet |
| Storage Required | ~90 MB (model) + your data | Just model (90 MB) |
| Colab Compatible | Yes (upload data first) | Yes (always connected) |

## Next Steps

1. **Add your dataset**: Copy Sentinel-2 images to `backend/data/raw/forest/` and `backend/data/raw/deforested/`
2. **Generate labels**: Run `create_labels_manifest.py`
3. **Start training**: Run `python src/ml/train_from_local.py`
4. **Monitor results**: Check saved metrics and checkpoints in `backend/models/`
5. **Deploy**: Use trained model for inference via BigEarthNetDetector

## References

- [DeforestationDataset](../src/ml/preprocessing.py) - Dataset class implementation
- [ModelTrainer](../src/ml/training.py) - Training pipeline
- [BigEarthNetDetector](../src/ml/bigearthnet_detector.py) - Inference class
