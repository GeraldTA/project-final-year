# Deforestation Detection using Sentinel-2 Imagery

A machine learning project that automatically downloads Sentinel-2 satellite imagery and detects deforestation patterns using NDVI calculations and change detection algorithms.

## Features

- Automated Sentinel-2 image downloading from Copernicus Data Space Ecosystem
- Google Earth Engine integration support
- Scheduled image updates every 5 days
- Cloud cover filtering and quality assessment
- NDVI calculation for vegetation analysis
- Change detection algorithms for deforestation monitoring
- Modular, reusable code architecture
- Comprehensive error handling and retry mechanisms

## Project Structure

```
deforestation-detection/
├── src/
│   ├── data/
│   │   ├── __init__.py
│   │   ├── sentinel_downloader.py     # Main download functionality
│   │   ├── gee_client.py              # Google Earth Engine client
│   │   └── data_manager.py            # Data storage and management
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── ndvi_calculator.py         # NDVI computation
│   │   ├── change_detector.py         # Change detection algorithms
│   │   └── image_processor.py         # General image processing
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py                  # Configuration management
│   │   ├── logger.py                  # Logging utilities
│   │   └── scheduler.py               # Task scheduling
│   └── main.py                        # Main pipeline orchestrator
├── data/
│   ├── raw/                           # Downloaded satellite images
│   ├── processed/                     # Processed images and results
│   └── metadata/                      # Image metadata and logs
├── notebooks/                         # Jupyter notebooks for analysis
├── tests/                             # Unit tests
├── config/
│   └── config.yaml                    # Configuration file
├── requirements.txt                   # Python dependencies
├── setup.py                          # Package setup
└── README.md                         # This file
```

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your API credentials in `config/config.yaml`
4. Run the setup: `python setup.py install`

## Usage

### Basic Usage
```python
from src.main import DeforestationPipeline

# Initialize the pipeline
pipeline = DeforestationPipeline(config_path="config/config.yaml")

# Download latest images
pipeline.download_latest_images()

# Process images and detect changes
results = pipeline.detect_changes()
```

### Automated Monitoring
```python
# Start automated monitoring (checks every 5 days)
pipeline.start_monitoring()
```

## Configuration

Edit `config/config.yaml` to set:
- Region of interest coordinates
- Date ranges
- Cloud cover thresholds
- API credentials
- Processing parameters

## Requirements

- Python 3.8+
- Google Earth Engine account (optional)
- Copernicus Data Space Ecosystem account
- Sufficient storage space for satellite imagery

## License

MIT License
