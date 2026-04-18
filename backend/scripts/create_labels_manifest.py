"""
Create training labels manifest from image files and directory structure.

Usage:
    python scripts/create_labels_manifest.py --data-dir backend/data/raw --output backend/data/labels.json

This script scans the data directory for GeoTIFF files and creates a labels.json
manifest file that can be used with DeforestationDataset.from_labels_file().

Directory structure expected:
    backend/data/raw/
        forest/           # Labeled as class 0
            image1.tif
            image2.tif
        deforested/       # Labeled as class 1
            image1.tif
            image2.tif
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_tiff_files(data_dir: Path) -> Dict[int, List[Path]]:
    """
    Scan data directory and group TIFF files by class label.
    
    Expected structure:
        data_dir/
            forest/           -> label 0
            deforested/       -> label 1
    """
    CLASS_DIRS = {
        'forest': 0,
        'deforested': 1,
    }
    
    class_files: Dict[int, List[Path]] = {0: [], 1: []}
    
    for class_name, class_label in CLASS_DIRS.items():
        class_dir = data_dir / class_name
        if class_dir.exists() and class_dir.is_dir():
            tiff_files = sorted(class_dir.glob('**/*.tif')) + sorted(class_dir.glob('**/*.tiff'))
            class_files[class_label].extend(tiff_files)
            logger.info(f"Found {len(tiff_files)} files in {class_name}/ (label={class_label})")
        else:
            logger.warning(f"Directory not found: {class_dir}")
    
    return class_files


def split_train_val_test(
    file_list: List[Path],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42
) -> Dict[str, List[Path]]:
    """
    Split files into train/val/test sets.
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "Ratios must sum to 1.0"
    
    np.random.seed(seed)
    shuffled = file_list.copy()
    np.random.shuffle(shuffled)
    
    n_total = len(shuffled)
    n_train = int(train_ratio * n_total)
    n_val = int(val_ratio * n_total)
    
    splits = {
        'train': shuffled[:n_train],
        'val': shuffled[n_train:n_train + n_val],
        'test': shuffled[n_train + n_val:],
    }
    
    for split_name, split_files in splits.items():
        logger.info(f"  {split_name}: {len(split_files)} files")
    
    return splits


def create_labels_manifest(
    data_dir: Path,
    output_path: Path,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> None:
    """
    Create labels.json manifest from data directory.
    """
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    
    logger.info(f"Scanning data directory: {data_dir}")
    class_files = find_tiff_files(data_dir)
    
    # Create samples list
    samples: List[Dict] = []
    
    for label, file_list in class_files.items():
        if not file_list:
            logger.warning(f"No files found for label {label}")
            continue
        
        logger.info(f"Processing label {label}: {len(file_list)} files")
        splits = split_train_val_test(
            file_list,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
        )
        
        for split_name, split_files in splits.items():
            for file_path in split_files:
                # Compute relative path from data_dir
                relative_path = file_path.relative_to(data_dir.parent)
                
                sample = {
                    "image_path": str(relative_path),
                    "label": label,
                    "split": split_name,
                    "filename": file_path.name,
                }
                samples.append(sample)
    
    if not samples:
        logger.warning("No samples created!")
        return
    
    # Create manifest
    manifest = {
        "base_dir": ".",
        "description": "Training labels for deforestation detection model. Format: 0=forest (no deforestation), 1=deforested",
        "created": str(Path.cwd()),
        "total_samples": len(samples),
        "samples": samples,
    }
    
    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    logger.info(f"Labels manifest created: {output_path}")
    logger.info(f"Total samples: {len(samples)}")
    
    # Summary by split
    splits_summary = {}
    for sample in samples:
        split = sample['split']
        splits_summary[split] = splits_summary.get(split, 0) + 1
    logger.info(f"Split summary: {splits_summary}")


def main():
    parser = argparse.ArgumentParser(
        description='Create training labels manifest from image files'
    )
    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path('backend/data/raw'),
        help='Data directory to scan for TIFF files (default: backend/data/raw)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('backend/data/labels.json'),
        help='Output labels.json path (default: backend/data/labels.json)'
    )
    parser.add_argument(
        '--train-ratio',
        type=float,
        default=0.7,
        help='Fraction of data for training (default: 0.7)'
    )
    parser.add_argument(
        '--val-ratio',
        type=float,
        default=0.15,
        help='Fraction of data for validation (default: 0.15)'
    )
    parser.add_argument(
        '--test-ratio',
        type=float,
        default=0.15,
        help='Fraction of data for testing (default: 0.15)'
    )
    
    args = parser.parse_args()
    
    create_labels_manifest(
        data_dir=args.data_dir,
        output_path=args.output,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
    )


if __name__ == '__main__':
    main()
