"""
Train deforestation detection model using locally stored labeled dataset.

STEP 6: Train from Local Labels
- Load training data from labels.json
- Split into train/val/test using the manifest
- Train model with full validation pipeline
- Save checkpoints and final model weights

Usage:
    python -c "from src.ml.train_from_local import train_local; train_local()"
    
Or from command line:
    python src/ml/train_from_local.py --labels backend/data/labels.json --epochs 30
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict
import json
from datetime import datetime
import argparse

from src.ml.preprocessing import Sentinel2Preprocessor, DeforestationDataset
from src.ml.model import DeforestationCNN
from src.ml.training import ModelTrainer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_dataset_from_manifest(
    labels_file: str,
    split: Optional[str] = None,
) -> DeforestationDataset:
    """
    Load dataset from labels manifest file.
    
    Args:
        labels_file: Path to labels.json manifest
        split: Specific split to load ('train', 'val', 'test', or None for all)
    
    Returns:
        DeforestationDataset instance
    """
    logger.info(f"Loading dataset from: {labels_file}")
    
    preprocessor = Sentinel2Preprocessor(
        target_size=(224, 224),
        normalize=True,
        compute_ndvi=True
    )
    
    dataset = DeforestationDataset.from_labels_file(
        labels_file=labels_file,
        preprocessor=preprocessor,
        split=split,
        strict_validation=True,
    )
    
    logger.info(f"Loaded dataset: {len(dataset)} samples")
    return dataset


def create_split_loaders(
    dataset: DeforestationDataset,
    batch_size: int = 32,
    num_workers: int = 0,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Create train/val/test DataLoaders from manifest-split dataset.
    
    Args:
        dataset: DeforestationDataset with 'splits' attribute
        batch_size: Batch size for loaders
        num_workers: Number of worker processes
    
    Returns:
        Tuple of (train_loader, val_loader, test_loader)
    """
    # Create indices for each split
    train_indices = [i for i, split in enumerate(dataset.splits) if split == 'train']
    val_indices = [i for i, split in enumerate(dataset.splits) if split == 'val']
    test_indices = [i for i, split in enumerate(dataset.splits) if split == 'test']
    
    logger.info(f"Split sizes: train={len(train_indices)}, val={len(val_indices)}, test={len(test_indices)}")
    
    train_subset = Subset(dataset, train_indices)
    val_subset = Subset(dataset, val_indices)
    test_subset = Subset(dataset, test_indices)
    
    train_loader = DataLoader(
        train_subset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )
    
    val_loader = DataLoader(
        val_subset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    test_loader = DataLoader(
        test_subset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    return train_loader, val_loader, test_loader


def train_local(
    labels_file: str = 'backend/data/labels.json',
    model_save_dir: str = 'backend/models',
    learning_rate: float = 0.001,
    batch_size: int = 32,
    num_epochs: int = 30,
    device: Optional[str] = None,
) -> Dict:
    """
    Train model using local labeled dataset.
    
    Args:
        labels_file: Path to labels.json manifest
        model_save_dir: Directory to save model checkpoints
        learning_rate: Learning rate for optimizer
        batch_size: Batch size for training
        num_epochs: Number of training epochs
        device: Device to train on ('cuda' or 'cpu')
    
    Returns:
        Training results dictionary
    """
    if device is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    logger.info(f"Training device: {device}")
    
    # Create output directory
    model_dir = Path(model_save_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Load dataset and create data loaders
    dataset = load_dataset_from_manifest(labels_file)
    train_loader, val_loader, test_loader = create_split_loaders(
        dataset,
        batch_size=batch_size,
    )
    
    # Initialize model
    logger.info("Initializing model...")
    model = DeforestationCNN(num_classes=2, input_channels=4)
    
    # Initialize trainer
    trainer = ModelTrainer(
        model=model,
        device=device,
        learning_rate=learning_rate,
        batch_size=batch_size,
        num_epochs=num_epochs,
    )
    
    # Train
    logger.info("Starting training...")
    history = trainer.train(
        train_loader=train_loader,
        val_loader=val_loader,
        save_dir=str(model_dir),
    )
    
    # Evaluate on test set
    logger.info("Evaluating on test set...")
    test_metrics = trainer.evaluate(test_loader)
    
    # Save final model
    final_model_path = model_dir / 'final_model.pth'
    torch.save(model.state_dict(), final_model_path)
    logger.info(f"Final model saved: {final_model_path}")
    
    # Save training summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'device': device,
        'learning_rate': learning_rate,
        'batch_size': batch_size,
        'num_epochs': num_epochs,
        'labels_file': labels_file,
        'dataset_size': len(dataset),
        'train_size': len(train_loader.dataset),
        'val_size': len(val_loader.dataset),
        'test_size': len(test_loader.dataset),
        'history': history,
        'test_metrics': test_metrics,
    }
    
    summary_path = model_dir / f'training_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    logger.info(f"Training summary saved: {summary_path}")
    logger.info(f"Test metrics: {test_metrics}")
    
    return summary


def main():
    parser = argparse.ArgumentParser(
        description='Train deforestation detection model from local labeled dataset'
    )
    parser.add_argument(
        '--labels',
        type=str,
        default='backend/data/labels.json',
        help='Path to labels.json manifest (default: backend/data/labels.json)'
    )
    parser.add_argument(
        '--model-dir',
        type=str,
        default='backend/models',
        help='Directory to save model checkpoints (default: backend/models)'
    )
    parser.add_argument(
        '--epochs',
        type=int,
        default=30,
        help='Number of training epochs (default: 30)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for training (default: 32)'
    )
    parser.add_argument(
        '--learning-rate',
        type=float,
        default=0.001,
        help='Learning rate (default: 0.001)'
    )
    parser.add_argument(
        '--device',
        type=str,
        default=None,
        help='Device to train on: cuda or cpu (default: auto-detect)'
    )
    
    args = parser.parse_args()
    
    train_local(
        labels_file=args.labels,
        model_save_dir=args.model_dir,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        num_epochs=args.epochs,
        device=args.device,
    )


if __name__ == '__main__':
    main()
