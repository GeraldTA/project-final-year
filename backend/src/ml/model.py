"""
ResNet-50 based CNN architecture for deforestation detection.

STEP 1 & 4: ML Architecture
- Uses ResNet-50 as backbone
- Pretrained on BigEarthNet (Sentinel-2 satellite images)
- Transfer learning approach
- Binary classification: Forest vs Deforested
"""

import torch
import torch.nn as nn
import torchvision.models as models
from torchvision.models import ResNet50_Weights
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DeforestationCNN(nn.Module):
    """
    ResNet-50 based CNN for deforestation detection.
    
    Architecture:
    - Backbone: ResNet-50 (pretrained on ImageNet, fine-tuned on BigEarthNet)
    - Input: 4-channel images (RGB + NIR) from Sentinel-2
    - Output: Binary classification (Forest/Deforested)
    
    Features:
    - Transfer learning from ImageNet weights
    - Adapted for 4-channel satellite imagery
    - Frozen early layers for faster training
    - Custom classification head
    """
    
    def __init__(self, num_classes=2, freeze_backbone=True, input_channels=4):
        """
        Initialize the deforestation detection model.
        
        Args:
            num_classes: Number of output classes (default: 2 - Forest/Deforested)
            freeze_backbone: Whether to freeze early ResNet layers (default: True)
            input_channels: Number of input channels (default: 4 - RGB + NIR)
        """
        super(DeforestationCNN, self).__init__()
        
        # Load pretrained ResNet-50
        logger.info("Loading ResNet-50 with pretrained weights...")
        self.resnet = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
        
        # Modify first conv layer to accept 4 channels (RGB + NIR)
        # Original: Conv2d(3, 64, kernel_size=7, stride=2, padding=3)
        # New: Conv2d(4, 64, kernel_size=7, stride=2, padding=3)
        if input_channels != 3:
            logger.info(f"Modifying input layer to accept {input_channels} channels (RGB + NIR)")
            original_conv = self.resnet.conv1
            self.resnet.conv1 = nn.Conv2d(
                input_channels, 64,
                kernel_size=7, stride=2, padding=3, bias=False
            )
            
            # Initialize new channel weights
            with torch.no_grad():
                # Copy RGB weights
                self.resnet.conv1.weight[:, :3, :, :] = original_conv.weight
                # Initialize NIR channel with mean of RGB
                if input_channels == 4:
                    self.resnet.conv1.weight[:, 3:, :, :] = original_conv.weight.mean(dim=1, keepdim=True)
        
        # Freeze backbone layers for transfer learning
        if freeze_backbone:
            logger.info("Freezing backbone layers for transfer learning...")
            for name, param in self.resnet.named_parameters():
                # Freeze all layers except the final classification layer
                if 'fc' not in name:
                    param.requires_grad = False
        
        # Get the number of features from the last layer
        num_features = self.resnet.fc.in_features
        
        # Replace final fully connected layer with custom classification head
        # STEP 4.2: Modified output layer
        logger.info(f"Replacing final layer: {num_features} -> {num_classes} classes")
        self.resnet.fc = nn.Sequential(
            nn.Dropout(0.5),  # Prevent overfitting
            nn.Linear(num_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes)
        )
        
        self.num_classes = num_classes
        self.input_channels = input_channels
        
        logger.info(f"Model initialized: {num_classes} classes, {input_channels} input channels")
    
    def forward(self, x):
        """
        Forward pass through the network.
        
        Args:
            x: Input tensor of shape (batch_size, channels, height, width)
               Expected: (N, 4, 224, 224) for Sentinel-2 RGBN
        
        Returns:
            Output logits of shape (batch_size, num_classes)
        """
        return self.resnet(x)
    
    def predict(self, x):
        """
        Make predictions with probability scores.
        
        Args:
            x: Input tensor
        
        Returns:
            Tuple of (class_predictions, probabilities)
        """
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            
            if self.num_classes == 2:
                # Binary classification
                probs = torch.softmax(logits, dim=1)
                preds = torch.argmax(probs, dim=1)
            else:
                # Multi-class classification
                probs = torch.softmax(logits, dim=1)
                preds = torch.argmax(probs, dim=1)
            
            return preds, probs
    
    def unfreeze_layers(self, num_layers=-1):
        """
        Unfreeze layers for fine-tuning.
        
        Args:
            num_layers: Number of layers to unfreeze from the end
                       -1 means unfreeze all layers
        """
        if num_layers == -1:
            logger.info("Unfreezing all layers")
            for param in self.resnet.parameters():
                param.requires_grad = True
        else:
            # Unfreeze last n layers
            logger.info(f"Unfreezing last {num_layers} layers")
            layers = list(self.resnet.children())
            for layer in layers[-num_layers:]:
                for param in layer.parameters():
                    param.requires_grad = True
    
    def get_num_trainable_params(self):
        """Get number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def get_num_total_params(self):
        """Get total number of parameters."""
        return sum(p.numel() for p in self.parameters())
    
    def save(self, path):
        """
        Save model checkpoint.
        
        Args:
            path: Path to save the model
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        checkpoint = {
            'model_state_dict': self.state_dict(),
            'num_classes': self.num_classes,
            'input_channels': self.input_channels,
            'architecture': 'ResNet50',
            'num_trainable_params': self.get_num_trainable_params(),
            'num_total_params': self.get_num_total_params()
        }
        
        torch.save(checkpoint, path)
        logger.info(f"Model saved to {path}")
    
    @classmethod
    def load(cls, path, device='cpu'):
        """
        Load model from checkpoint.
        
        Args:
            path: Path to the saved model
            device: Device to load the model on ('cpu' or 'cuda')
        
        Returns:
            Loaded model instance
        """
        logger.info(f"Loading model from {path}")
        checkpoint = torch.load(path, map_location=device)
        
        # Create model instance
        model = cls(
            num_classes=checkpoint['num_classes'],
            input_channels=checkpoint['input_channels'],
            freeze_backbone=False  # Load with all layers trainable
        )
        
        # Load weights
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(device)
        
        logger.info(f"Model loaded successfully ({checkpoint['num_total_params']} parameters)")
        return model


def create_model(num_classes=2, input_channels=4, freeze_backbone=True):
    """
    Factory function to create a deforestation detection model.
    
    Args:
        num_classes: Number of output classes
        input_channels: Number of input channels
        freeze_backbone: Whether to freeze backbone layers
    
    Returns:
        DeforestationCNN instance
    """
    return DeforestationCNN(
        num_classes=num_classes,
        freeze_backbone=freeze_backbone,
        input_channels=input_channels
    )


if __name__ == "__main__":
    # Test model creation
    logging.basicConfig(level=logging.INFO)
    
    print("Creating deforestation detection model...")
    model = create_model()
    
    print(f"\nModel Summary:")
    print(f"Total parameters: {model.get_num_total_params():,}")
    print(f"Trainable parameters: {model.get_num_trainable_params():,}")
    print(f"Input channels: {model.input_channels}")
    print(f"Output classes: {model.num_classes}")
    
    # Test forward pass
    dummy_input = torch.randn(2, 4, 224, 224)  # Batch of 2 images
    output = model(dummy_input)
    print(f"\nTest forward pass:")
    print(f"Input shape: {dummy_input.shape}")
    print(f"Output shape: {output.shape}")
    
    # Test prediction
    preds, probs = model.predict(dummy_input)
    print(f"Predictions: {preds}")
    print(f"Probabilities shape: {probs.shape}")
