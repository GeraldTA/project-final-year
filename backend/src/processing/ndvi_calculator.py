"""
NDVI (Normalized Difference Vegetation Index) calculator for Sentinel-2 imagery.

This module provides functions to calculate NDVI from Sentinel-2 satellite
images and analyze vegetation health and changes over time.
"""

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
import logging
from datetime import datetime
import sys

# Add utils to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.insert(0, str(src_dir))

from utils.logger import LoggerMixin, log_function_call
from utils.config import get_config


class NDVICalculator(LoggerMixin):
    """
    NDVI calculator for Sentinel-2 imagery.
    
    This class handles NDVI calculation, vegetation health assessment,
    and temporal analysis of vegetation changes.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize NDVI calculator.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = get_config(config_path)
        self.output_dir = self.config.get_data_dir('processed_images')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # NDVI thresholds from config
        self.healthy_threshold = self.config.get('processing.ndvi.threshold_healthy', 0.4)
        self.stressed_threshold = self.config.get('processing.ndvi.threshold_stressed', 0.2)
        
        self.logger.info("NDVI calculator initialized")
    
    @log_function_call
    def calculate_ndvi(
        self,
        red_band_path: str,
        nir_band_path: str,
        output_path: Optional[str] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Calculate NDVI from Red and NIR bands.
        
        NDVI = (NIR - Red) / (NIR + Red)
        
        Args:
            red_band_path: Path to Red band (B04) GeoTIFF file
            nir_band_path: Path to NIR band (B08) GeoTIFF file
            output_path: Optional path to save NDVI as GeoTIFF
            
        Returns:
            Tuple of (NDVI array, metadata dict)
        """
        try:
            # Read Red band (B04)
            with rasterio.open(red_band_path) as red_src:
                red_data = red_src.read(1).astype(np.float32)
                red_profile = red_src.profile
                red_transform = red_src.transform
                red_crs = red_src.crs
            
            # Read NIR band (B08)
            with rasterio.open(nir_band_path) as nir_src:
                nir_data = nir_src.read(1).astype(np.float32)
                nir_profile = nir_src.profile
                nir_transform = nir_src.transform
                nir_crs = nir_src.crs
            
            # Check if bands have the same dimensions and CRS
            if red_data.shape != nir_data.shape:
                self.logger.warning("Red and NIR bands have different shapes, resampling NIR to match Red")
                nir_data = self._resample_band(nir_data, nir_transform, red_data.shape, red_transform)
            
            if red_crs != nir_crs:
                self.logger.warning("Red and NIR bands have different CRS")
            
            # Convert to reflectance (Sentinel-2 L2A values are already in reflectance * 10000)
            red_reflectance = red_data / 10000.0
            nir_reflectance = nir_data / 10000.0
            
            # Calculate NDVI with masking for invalid values
            # Avoid division by zero
            denominator = nir_reflectance + red_reflectance
            valid_mask = (denominator != 0) & (red_reflectance >= 0) & (nir_reflectance >= 0)
            
            ndvi = np.full_like(red_reflectance, np.nan)
            ndvi[valid_mask] = (nir_reflectance[valid_mask] - red_reflectance[valid_mask]) / denominator[valid_mask]
            
            # Clip NDVI to valid range [-1, 1]
            ndvi = np.clip(ndvi, -1, 1)
            
            # Calculate statistics
            valid_ndvi = ndvi[~np.isnan(ndvi)]
            stats = {
                'mean': float(np.mean(valid_ndvi)) if len(valid_ndvi) > 0 else np.nan,
                'std': float(np.std(valid_ndvi)) if len(valid_ndvi) > 0 else np.nan,
                'min': float(np.min(valid_ndvi)) if len(valid_ndvi) > 0 else np.nan,
                'max': float(np.max(valid_ndvi)) if len(valid_ndvi) > 0 else np.nan,
                'percentile_25': float(np.percentile(valid_ndvi, 25)) if len(valid_ndvi) > 0 else np.nan,
                'percentile_75': float(np.percentile(valid_ndvi, 75)) if len(valid_ndvi) > 0 else np.nan,
                'valid_pixels': len(valid_ndvi),
                'total_pixels': ndvi.size,
                'nodata_percentage': (1 - len(valid_ndvi) / ndvi.size) * 100
            }
            
            # Vegetation health analysis
            health_stats = self._analyze_vegetation_health(valid_ndvi)
            stats.update(health_stats)
            
            # Save NDVI if output path specified
            if output_path:
                self._save_ndvi_geotiff(ndvi, red_profile, output_path)
            
            self.logger.info(f"NDVI calculated successfully. Mean NDVI: {stats['mean']:.3f}")
            return ndvi, stats
            
        except Exception as e:
            self.logger.error(f"Failed to calculate NDVI: {e}")
            raise
    
    def _resample_band(
        self,
        data: np.ndarray,
        transform: Any,
        target_shape: Tuple[int, int],
        target_transform: Any
    ) -> np.ndarray:
        """Resample band data to match target shape and transform."""
        # Create temporary arrays for resampling
        resampled = np.empty(target_shape, dtype=data.dtype)
        
        reproject(
            source=data,
            destination=resampled,
            src_transform=transform,
            dst_transform=target_transform,
            resampling=Resampling.bilinear
        )
        
        return resampled
    
    def _analyze_vegetation_health(self, ndvi_values: np.ndarray) -> Dict[str, Any]:
        """Analyze vegetation health based on NDVI values."""
        if len(ndvi_values) == 0:
            return {
                'healthy_vegetation_percentage': 0.0,
                'stressed_vegetation_percentage': 0.0,
                'bare_soil_percentage': 0.0,
                'water_bodies_percentage': 0.0
            }
        
        total_pixels = len(ndvi_values)
        
        # Classify vegetation health
        healthy_mask = ndvi_values >= self.healthy_threshold
        stressed_mask = (ndvi_values >= self.stressed_threshold) & (ndvi_values < self.healthy_threshold)
        bare_soil_mask = (ndvi_values >= 0) & (ndvi_values < self.stressed_threshold)
        water_mask = ndvi_values < 0
        
        return {
            'healthy_vegetation_percentage': (np.sum(healthy_mask) / total_pixels) * 100,
            'stressed_vegetation_percentage': (np.sum(stressed_mask) / total_pixels) * 100,
            'bare_soil_percentage': (np.sum(bare_soil_mask) / total_pixels) * 100,
            'water_bodies_percentage': (np.sum(water_mask) / total_pixels) * 100
        }
    
    def _save_ndvi_geotiff(
        self,
        ndvi: np.ndarray,
        source_profile: Dict[str, Any],
        output_path: str
    ) -> None:
        """Save NDVI array as GeoTIFF file."""
        # Update profile for NDVI output
        profile = source_profile.copy()
        profile.update({
            'dtype': 'float32',
            'count': 1,
            'compress': 'lzw',
            'nodata': np.nan
        })
        
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(ndvi.astype(np.float32), 1)
        
        self.logger.info(f"NDVI saved to: {output_path}")
    
    @log_function_call
    def calculate_ndvi_from_sentinel_image(
        self,
        image_dir: str,
        output_name: Optional[str] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Calculate NDVI from a Sentinel-2 SAFE directory.
        
        Args:
            image_dir: Path to Sentinel-2 SAFE directory
            output_name: Optional name for output file
            
        Returns:
            Tuple of (NDVI array, metadata dict)
        """
        image_path = Path(image_dir)
        
        # Find band files in the SAFE directory structure
        img_data_dir = image_path / "GRANULE"
        granule_dirs = list(img_data_dir.glob("*"))
        
        if not granule_dirs:
            raise FileNotFoundError(f"No granule directories found in {img_data_dir}")
        
        granule_dir = granule_dirs[0]  # Take first granule
        img_dir = granule_dir / "IMG_DATA" / "R10m"  # 10m resolution bands
        
        # Find Red (B04) and NIR (B08) band files
        red_files = list(img_dir.glob("*B04_10m.jp2"))
        nir_files = list(img_dir.glob("*B08_10m.jp2"))
        
        if not red_files:
            raise FileNotFoundError(f"Red band (B04) not found in {img_dir}")
        if not nir_files:
            raise FileNotFoundError(f"NIR band (B08) not found in {img_dir}")
        
        red_band_path = str(red_files[0])
        nir_band_path = str(nir_files[0])
        
        # Generate output path
        if output_name is None:
            output_name = f"NDVI_{image_path.name}.tif"
        
        output_path = self.output_dir / output_name
        
        # Calculate NDVI
        return self.calculate_ndvi(red_band_path, nir_band_path, str(output_path))
    
    @log_function_call
    def create_ndvi_visualization(
        self,
        ndvi: np.ndarray,
        output_path: str,
        title: Optional[str] = None,
        colormap: str = 'RdYlGn'
    ) -> None:
        """
        Create NDVI visualization with proper color mapping.
        
        Args:
            ndvi: NDVI array
            output_path: Path to save visualization
            title: Optional title for the plot
            colormap: Matplotlib colormap name
        """
        plt.figure(figsize=(12, 8))
        
        # Create masked array to handle NaN values
        masked_ndvi = np.ma.masked_invalid(ndvi)
        
        # Create the plot
        im = plt.imshow(masked_ndvi, cmap=colormap, vmin=-1, vmax=1)
        
        # Add colorbar
        cbar = plt.colorbar(im, shrink=0.8)
        cbar.set_label('NDVI', rotation=270, labelpad=20)
        
        # Add title
        if title:
            plt.title(title, fontsize=14, fontweight='bold')
        else:
            plt.title('Normalized Difference Vegetation Index (NDVI)', fontsize=14, fontweight='bold')
        
        # Remove axes
        plt.axis('off')
        
        # Add NDVI interpretation legend
        legend_text = (
            "NDVI Interpretation:\n"
            "< 0: Water bodies\n"
            f"0 - {self.stressed_threshold}: Bare soil/rocks\n"
            f"{self.stressed_threshold} - {self.healthy_threshold}: Stressed vegetation\n"
            f"> {self.healthy_threshold}: Healthy vegetation"
        )
        
        plt.text(0.02, 0.98, legend_text, transform=plt.gca().transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Save the plot
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"NDVI visualization saved to: {output_path}")
    
    @log_function_call
    def batch_calculate_ndvi(
        self,
        image_directories: List[str],
        create_visualizations: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Calculate NDVI for multiple Sentinel-2 images.
        
        Args:
            image_directories: List of paths to Sentinel-2 SAFE directories
            create_visualizations: Whether to create visualization plots
            
        Returns:
            List of dictionaries containing NDVI statistics for each image
        """
        results = []
        
        for i, image_dir in enumerate(image_directories, 1):
            try:
                self.logger.info(f"Processing image {i}/{len(image_directories)}: {Path(image_dir).name}")
                
                # Calculate NDVI
                ndvi, stats = self.calculate_ndvi_from_sentinel_image(image_dir)
                
                # Add metadata
                stats['image_directory'] = image_dir
                stats['image_name'] = Path(image_dir).name
                stats['processing_date'] = datetime.now().isoformat()
                
                # Create visualization if requested
                if create_visualizations:
                    viz_path = self.output_dir / f"NDVI_viz_{Path(image_dir).name}.png"
                    self.create_ndvi_visualization(
                        ndvi,
                        str(viz_path),
                        title=f"NDVI - {Path(image_dir).name}"
                    )
                    stats['visualization_path'] = str(viz_path)
                
                results.append(stats)
                
            except Exception as e:
                self.logger.error(f"Failed to process image {image_dir}: {e}")
                # Add error entry to results
                results.append({
                    'image_directory': image_dir,
                    'image_name': Path(image_dir).name,
                    'error': str(e),
                    'processing_date': datetime.now().isoformat()
                })
        
        self.logger.info(f"Batch NDVI calculation completed. Processed {len(results)} images")
        return results
    
    @log_function_call
    def compare_ndvi_time_series(
        self,
        ndvi_data_list: List[Tuple[np.ndarray, datetime, str]],
        output_path: str
    ) -> Dict[str, Any]:
        """
        Compare NDVI values across a time series of images.
        
        Args:
            ndvi_data_list: List of tuples (ndvi_array, date, label)
            output_path: Path to save comparison plot
            
        Returns:
            Dictionary with time series statistics
        """
        if len(ndvi_data_list) < 2:
            raise ValueError("At least 2 NDVI datasets required for comparison")
        
        # Calculate mean NDVI for each time point
        time_series_data = []
        
        for ndvi, date, label in ndvi_data_list:
            valid_ndvi = ndvi[~np.isnan(ndvi)]
            if len(valid_ndvi) > 0:
                mean_ndvi = np.mean(valid_ndvi)
                time_series_data.append({
                    'date': date,
                    'mean_ndvi': mean_ndvi,
                    'label': label,
                    'std_ndvi': np.std(valid_ndvi),
                    'valid_pixels': len(valid_ndvi)
                })
        
        # Sort by date
        time_series_data.sort(key=lambda x: x['date'])
        
        # Create time series plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot 1: Mean NDVI over time
        dates = [item['date'] for item in time_series_data]
        mean_values = [item['mean_ndvi'] for item in time_series_data]
        std_values = [item['std_ndvi'] for item in time_series_data]
        
        ax1.plot(dates, mean_values, 'o-', linewidth=2, markersize=8)
        ax1.fill_between(dates, 
                        [m - s for m, s in zip(mean_values, std_values)],
                        [m + s for m, s in zip(mean_values, std_values)],
                        alpha=0.3)
        
        ax1.set_ylabel('Mean NDVI')
        ax1.set_title('NDVI Time Series Analysis')
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=self.healthy_threshold, color='g', linestyle='--', 
                   label=f'Healthy threshold ({self.healthy_threshold})')
        ax1.axhline(y=self.stressed_threshold, color='orange', linestyle='--',
                   label=f'Stressed threshold ({self.stressed_threshold})')
        ax1.legend()
        
        # Plot 2: NDVI change rate
        if len(mean_values) > 1:
            change_rates = []
            change_dates = []
            
            for i in range(1, len(mean_values)):
                days_diff = (dates[i] - dates[i-1]).days
                if days_diff > 0:
                    rate = (mean_values[i] - mean_values[i-1]) / days_diff * 30  # Change per month
                    change_rates.append(rate)
                    change_dates.append(dates[i])
            
            ax2.bar(change_dates, change_rates, alpha=0.7)
            ax2.set_ylabel('NDVI Change Rate (per month)')
            ax2.set_xlabel('Date')
            ax2.grid(True, alpha=0.3)
            ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        # Calculate overall statistics
        overall_stats = {
            'time_series_data': time_series_data,
            'overall_trend': 'improving' if mean_values[-1] > mean_values[0] else 'declining',
            'total_change': mean_values[-1] - mean_values[0],
            'max_ndvi': max(mean_values),
            'min_ndvi': min(mean_values),
            'ndvi_volatility': np.std(mean_values),
            'number_of_observations': len(time_series_data)
        }
        
        self.logger.info(f"Time series analysis completed. Overall trend: {overall_stats['overall_trend']}")
        return overall_stats
