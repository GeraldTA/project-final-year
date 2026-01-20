"""
Initialize ML System with Demo Capabilities
Creates a ready-to-use deforestation detection model
"""
import torch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ml.model import create_model
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_demo_model():
    """Create a demo model for immediate use"""
    logger.info("Creating demo deforestation detection model...")
    
    try:
        # Create model
        model = create_model(freeze_backbone=True)
        model.eval()
        
        # Save to models directory
        models_dir = Path(__file__).parent / "models"
        models_dir.mkdir(exist_ok=True)
        
        model_path = models_dir / "deforestation_model.pth"
        
        # Save model state
        torch.save({
            'model_state_dict': model.state_dict(),
            'model_config': {
                'num_classes': 2,
                'input_channels': 4,
                'freeze_backbone': True
            },
            'training_info': {
                'status': 'demo',
                'note': 'Untrained model - for demo purposes only',
                'requires_training': True
            }
        }, model_path)
        
        logger.info(f"✓ Demo model saved to {model_path}")
        logger.info("✓ Model is ready for use (requires training for production)")
        
        # Test model
        logger.info("Testing model inference...")
        dummy_input = torch.randn(1, 4, 224, 224)
        with torch.no_grad():
            output = model(dummy_input)
        logger.info(f"✓ Model test successful - output shape: {output.shape}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create demo model: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("ML SYSTEM INITIALIZATION")
    logger.info("="*60)
    
    success = initialize_demo_model()
    
    if success:
        logger.info("\n" + "="*60)
        logger.info("✓ ML SYSTEM READY")
        logger.info("="*60)
        logger.info("\nYou can now:")
        logger.info("1. Start the API server: python api_server.py")
        logger.info("2. Access ML endpoints at http://localhost:8001/api/ml/")
        logger.info("3. Check status: http://localhost:8001/api/ml/status")
        logger.info("\nNote: Model is untrained. For production use:")
        logger.info("- Prepare labeled dataset")
        logger.info("- Run training: python src/ml/train_and_deploy.py")
    else:
        logger.error("\n✗ ML system initialization failed")
        sys.exit(1)
