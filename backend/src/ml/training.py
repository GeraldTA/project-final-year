"""
Model Training Pipeline

STEP 5: Training Process
- Dataset splitting (70% train, 15% val, 15% test)
- Binary Cross Entropy loss
- Adam optimizer
- Training with validation
- Metrics: Accuracy, Precision, Recall, F1-Score
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
import numpy as np
from pathlib import Path
import logging
from typing import Dict, Tuple, Optional
import json
from datetime import datetime
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Trainer for deforestation detection model.
    
    STEP 5: Complete training process with validation and metrics.
    """
    
    def __init__(
        self,
        model: nn.Module,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        learning_rate: float = 0.001,
        batch_size: int = 32,
        num_epochs: int = 20
    ):
        """
        Initialize the trainer.
        
        Args:
            model: The DeforestationCNN model
            device: Device to train on ('cuda' or 'cpu')
            learning_rate: Learning rate for optimizer
            batch_size: Batch size for training
            num_epochs: Number of training epochs
        """
        self.model = model.to(device)
        self.device = device
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.num_epochs = num_epochs
        
        # Loss function: Binary Cross Entropy
        self.criterion = nn.CrossEntropyLoss()
        
        # Optimizer: Adam
        self.optimizer = optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=1e-5  # L2 regularization
        )
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=3,
            verbose=True
        )
        
        # Training history
        self.history = {
            'train_loss': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': [],
            'val_precision': [],
            'val_recall': [],
            'val_f1': []
        }
        
        logger.info(f"Trainer initialized on {device}")
        logger.info(f"Learning rate: {learning_rate}, Batch size: {batch_size}, Epochs: {num_epochs}")
    
    def split_dataset(
        self,
        dataset,
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15
    ) -> Tuple[DataLoader, DataLoader, DataLoader]:
        """
        Split dataset into train, validation, and test sets.
        
        STEP 5: Dataset Splitting (70% train, 15% val, 15% test)
        
        Args:
            dataset: The complete dataset
            train_ratio: Ratio of training data
            val_ratio: Ratio of validation data
            test_ratio: Ratio of test data
        
        Returns:
            Tuple of (train_loader, val_loader, test_loader)
        """
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
            "Ratios must sum to 1.0"
        
        total_size = len(dataset)
        train_size = int(train_ratio * total_size)
        val_size = int(val_ratio * total_size)
        test_size = total_size - train_size - val_size
        
        train_dataset, val_dataset, test_dataset = random_split(
            dataset,
            [train_size, val_size, test_size],
            generator=torch.Generator().manual_seed(42)
        )
        
        # Create data loaders
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=4,
            pin_memory=True if self.device == 'cuda' else False
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=4,
            pin_memory=True if self.device == 'cuda' else False
        )
        
        test_loader = DataLoader(
            test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=4,
            pin_memory=True if self.device == 'cuda' else False
        )
        
        logger.info(f"Dataset split: Train={train_size}, Val={val_size}, Test={test_size}")
        
        return train_loader, val_loader, test_loader
    
    def train_epoch(self, train_loader) -> Tuple[float, float]:
        """
        Train for one epoch.
        
        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.train()
        running_loss = 0.0
        all_preds = []
        all_labels = []
        
        for batch_idx, batch in enumerate(train_loader):
            images = batch['image'].to(self.device)
            labels = batch['label'].to(self.device)
            
            # Zero gradients
            self.optimizer.zero_grad()
            
            # Forward pass
            outputs = self.model(images)
            loss = self.criterion(outputs, labels)
            
            # Backward pass
            loss.backward()
            self.optimizer.step()
            
            # Track metrics
            running_loss += loss.item()
            _, preds = torch.max(outputs, 1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            
            if batch_idx % 10 == 0:
                logger.debug(f"Batch {batch_idx}/{len(train_loader)}, Loss: {loss.item():.4f}")
        
        avg_loss = running_loss / len(train_loader)
        accuracy = accuracy_score(all_labels, all_preds)
        
        return avg_loss, accuracy
    
    def validate(self, val_loader) -> Dict[str, float]:
        """
        Validate the model.
        
        STEP 5: Evaluation Metrics (Accuracy, Precision, Recall, F1-Score)
        
        Returns:
            Dictionary of validation metrics
        """
        self.model.eval()
        running_loss = 0.0
        all_preds = []
        all_labels = []
        all_probs = []
        
        with torch.no_grad():
            for batch in val_loader:
                images = batch['image'].to(self.device)
                labels = batch['label'].to(self.device)
                
                # Forward pass
                outputs = self.model(images)
                loss = self.criterion(outputs, labels)
                
                # Track metrics
                running_loss += loss.item()
                probs = torch.softmax(outputs, dim=1)
                _, preds = torch.max(outputs, 1)
                
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
                all_probs.extend(probs.cpu().numpy())
        
        # Calculate metrics
        avg_loss = running_loss / len(val_loader)
        accuracy = accuracy_score(all_labels, all_preds)
        precision = precision_score(all_labels, all_preds, average='binary', zero_division=0)
        recall = recall_score(all_labels, all_preds, average='binary', zero_division=0)
        f1 = f1_score(all_labels, all_preds, average='binary', zero_division=0)
        
        # Confusion matrix
        cm = confusion_matrix(all_labels, all_preds)
        
        metrics = {
            'loss': avg_loss,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'confusion_matrix': cm.tolist()
        }
        
        return metrics
    
    def train(
        self,
        train_loader,
        val_loader,
        save_dir: str = 'models/checkpoints',
        early_stopping_patience: int = 5
    ) -> Dict:
        """
        Complete training process.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            save_dir: Directory to save checkpoints
            early_stopping_patience: Epochs to wait before early stopping
        
        Returns:
            Training history dictionary
        """
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        best_val_loss = float('inf')
        patience_counter = 0
        best_epoch = 0
        
        logger.info(f"Starting training for {self.num_epochs} epochs...")
        logger.info(f"Device: {self.device}")
        
        for epoch in range(self.num_epochs):
            epoch_start = datetime.now()
            
            # Train
            train_loss, train_acc = self.train_epoch(train_loader)
            
            # Validate
            val_metrics = self.validate(val_loader)
            
            # Update learning rate
            self.scheduler.step(val_metrics['loss'])
            
            # Save history
            self.history['train_loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_loss'].append(val_metrics['loss'])
            self.history['val_acc'].append(val_metrics['accuracy'])
            self.history['val_precision'].append(val_metrics['precision'])
            self.history['val_recall'].append(val_metrics['recall'])
            self.history['val_f1'].append(val_metrics['f1_score'])
            
            epoch_time = (datetime.now() - epoch_start).total_seconds()
            
            # Log progress
            logger.info(
                f"Epoch [{epoch+1}/{self.num_epochs}] "
                f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f} | "
                f"Val Loss: {val_metrics['loss']:.4f}, Val Acc: {val_metrics['accuracy']:.4f}, "
                f"F1: {val_metrics['f1_score']:.4f} | "
                f"Time: {epoch_time:.1f}s"
            )
            
            # Save best model
            if val_metrics['loss'] < best_val_loss:
                best_val_loss = val_metrics['loss']
                best_epoch = epoch + 1
                patience_counter = 0
                
                # Save checkpoint
                checkpoint_path = save_dir / 'best_model.pth'
                self.model.save(checkpoint_path)
                logger.info(f"✓ Best model saved to {checkpoint_path}")
            else:
                patience_counter += 1
            
            # Early stopping
            if patience_counter >= early_stopping_patience:
                logger.info(f"Early stopping triggered after {epoch+1} epochs")
                logger.info(f"Best model was at epoch {best_epoch}")
                break
            
            # Save checkpoint every 5 epochs
            if (epoch + 1) % 5 == 0:
                checkpoint_path = save_dir / f'checkpoint_epoch_{epoch+1}.pth'
                self.model.save(checkpoint_path)
        
        # Save final model and history
        final_path = save_dir / 'final_model.pth'
        self.model.save(final_path)
        
        history_path = save_dir / 'training_history.json'
        with open(history_path, 'w') as f:
            json.dump(self.history, f, indent=2)
        
        logger.info(f"Training completed. Best validation loss: {best_val_loss:.4f} at epoch {best_epoch}")
        logger.info(f"Final model saved to {final_path}")
        logger.info(f"Training history saved to {history_path}")
        
        return self.history
    
    def plot_training_history(self, save_path: Optional[str] = None):
        """
        Plot training history.
        
        Args:
            save_path: Path to save the plot (optional)
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Loss
        axes[0, 0].plot(self.history['train_loss'], label='Train Loss')
        axes[0, 0].plot(self.history['val_loss'], label='Val Loss')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].set_title('Training and Validation Loss')
        axes[0, 0].legend()
        axes[0, 0].grid(True)
        
        # Accuracy
        axes[0, 1].plot(self.history['train_acc'], label='Train Acc')
        axes[0, 1].plot(self.history['val_acc'], label='Val Acc')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Accuracy')
        axes[0, 1].set_title('Training and Validation Accuracy')
        axes[0, 1].legend()
        axes[0, 1].grid(True)
        
        # Precision, Recall, F1
        axes[1, 0].plot(self.history['val_precision'], label='Precision')
        axes[1, 0].plot(self.history['val_recall'], label='Recall')
        axes[1, 0].plot(self.history['val_f1'], label='F1-Score')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Score')
        axes[1, 0].set_title('Validation Metrics')
        axes[1, 0].legend()
        axes[1, 0].grid(True)
        
        # Confusion Matrix (last epoch)
        if 'val_confusion_matrix' in self.history and self.history['val_confusion_matrix']:
            last_cm = np.array(self.history['val_confusion_matrix'][-1])
            im = axes[1, 1].imshow(last_cm, cmap='Blues')
            axes[1, 1].set_title('Confusion Matrix (Last Epoch)')
            axes[1, 1].set_xlabel('Predicted')
            axes[1, 1].set_ylabel('Actual')
            axes[1, 1].set_xticks([0, 1])
            axes[1, 1].set_yticks([0, 1])
            axes[1, 1].set_xticklabels(['Forest', 'Deforested'])
            axes[1, 1].set_yticklabels(['Forest', 'Deforested'])
            
            # Add text annotations
            for i in range(2):
                for j in range(2):
                    text = axes[1, 1].text(j, i, int(last_cm[i, j]),
                                          ha="center", va="center", color="black")
            
            plt.colorbar(im, ax=axes[1, 1])
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Training plots saved to {save_path}")
        
        plt.show()


def train_model(
    model,
    dataset,
    epochs: int = 20,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    save_dir: str = 'models/checkpoints'
):
    """
    Convenience function to train a model.
    
    STEP 5 & 6: Training and Model Saving
    
    Args:
        model: The model to train
        dataset: The complete dataset
        epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        save_dir: Directory to save checkpoints
    
    Returns:
        Trained model and training history
    """
    # Create trainer
    trainer = ModelTrainer(
        model=model,
        learning_rate=learning_rate,
        batch_size=batch_size,
        num_epochs=epochs
    )
    
    # Split dataset
    train_loader, val_loader, test_loader = trainer.split_dataset(dataset)
    
    # Train
    history = trainer.train(train_loader, val_loader, save_dir=save_dir)
    
    # Plot results
    plot_path = Path(save_dir) / 'training_plots.png'
    trainer.plot_training_history(save_path=str(plot_path))
    
    # Final evaluation on test set
    logger.info("\nEvaluating on test set...")
    test_metrics = trainer.validate(test_loader)
    logger.info(f"Test Results:")
    logger.info(f"  Accuracy: {test_metrics['accuracy']:.4f}")
    logger.info(f"  Precision: {test_metrics['precision']:.4f}")
    logger.info(f"  Recall: {test_metrics['recall']:.4f}")
    logger.info(f"  F1-Score: {test_metrics['f1_score']:.4f}")
    
    # Save test metrics
    test_metrics_path = Path(save_dir) / 'test_metrics.json'
    with open(test_metrics_path, 'w') as f:
        # Convert numpy arrays to lists for JSON serialization
        serializable_metrics = {
            k: v.tolist() if isinstance(v, np.ndarray) else v
            for k, v in test_metrics.items()
        }
        json.dump(serializable_metrics, f, indent=2)
    
    return model, history


if __name__ == "__main__":
    # Test training setup
    logging.basicConfig(level=logging.INFO)
    
    print("Training pipeline test...")
    print("This would normally train the model on your dataset")
    print("See train_model() function for complete training workflow")
