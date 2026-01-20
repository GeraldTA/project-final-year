# 🚀 Quick Start Guide - ML Module Installation

## ⚡ Fast Installation (5 minutes)

### Step 1: Install PyTorch

Choose based on your system:

#### Windows (CPU):
```bash
pip install torch torchvision torchaudio
```

#### Windows (GPU - NVIDIA):
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Step 2: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Verify Installation
```bash
python -c "import torch; print(f'PyTorch {torch.__version__} installed')"
python -c "from src.ml.model import create_model; print('✓ ML module ready')"
```

## 🧪 Test the ML System

### Test 1: Create Model
```bash
python src/ml/model.py
```

Expected output:
```
Creating deforestation detection model...
Model created with 25,557,032 parameters
✓ Test passed
```

### Test 2: Test Preprocessing
```bash
python src/ml/preprocessing.py
```

Expected output:
```
Preprocessing results:
Image shape: (224, 224, 4)
NDVI shape: (224, 224)
✓ Test passed
```

### Test 3: Complete Workflow Guide
```bash
python src/ml/train_and_deploy.py
```

This will show you the complete 12-step workflow!

## 📦 What Got Installed

```
backend/src/ml/
├── __init__.py              # Module exports
├── model.py                 # ResNet-50 architecture (STEP 1 & 4)
├── preprocessing.py         # Data pipeline (STEP 2)
├── training.py              # Training system (STEP 5)
├── inference.py             # Real-time detection (STEP 7)
├── postprocessing.py        # Results processing (STEP 8)
├── api_integration.py       # Backend API (STEP 9)
├── train_and_deploy.py      # Complete workflow guide
└── README.md                # Full documentation
```

## 🎯 Next Steps

### Option A: Use Pre-trained Model (When Available)
```python
from src.ml.inference import create_detector

detector = create_detector('models/best_model.pth')
result = detector.predict_from_file('image.tif')
print(f"Prediction: {result['prediction']}")
```

### Option B: Train Your Own Model

1. **Prepare Dataset**:
   - Download Sentinel-2 images for Zimbabwe
   - Label as Forest (0) or Deforested (1)
   - Organize into dataset structure

2. **Train**:
   ```python
   from src.ml.training import train_model
   from src.ml.model import create_model
   
   model = create_model()
   trained_model, history = train_model(
       model=model,
       dataset=your_dataset,
       epochs=20
   )
   ```

3. **Deploy**:
   - Model saved to `models/checkpoints/best_model.pth`
   - Integrate with backend API (instructions in README.md)

## 🔧 Integration with Backend

Edit `backend/api_server.py`:

```python
# Add these lines at the top
from src.ml.api_integration import ml_router, initialize_ml_system

# Add router to app
app.include_router(ml_router)

# Initialize ML system on startup
@app.on_event("startup")
async def startup():
    initialize_ml_system()
```

Then restart your backend:
```bash
python api_server.py
```

ML endpoints will be available at:
- `http://localhost:8001/api/ml/status`
- `http://localhost:8001/api/ml/run-ml-detection`
- `http://localhost:8001/api/ml/statistics`

## ✅ Verification Checklist

- [ ] PyTorch installed
- [ ] All dependencies installed
- [ ] Model creation test passed
- [ ] Preprocessing test passed
- [ ] Read the complete workflow guide
- [ ] Ready to train or deploy!

## 🆘 Need Help?

Check the full documentation:
```bash
cat backend/src/ml/README.md
```

Or run the interactive guide:
```bash
python src/ml/train_and_deploy.py
```

## 🎉 You're All Set!

The complete ML system is now installed and ready to use. Follow the 12-step workflow in `train_and_deploy.py` to implement deforestation detection with ResNet-50!

---
**Time to complete**: ~5 minutes  
**Status**: ✅ All 12 steps implemented  
**Ready for**: Training and deployment
