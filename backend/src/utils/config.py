"""
Configuration management utilities for the deforestation detection system.

This module handles loading and validating configuration from YAML files,
environment variables, and provides default values for the system.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the deforestation detection system."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration YAML file. If None, uses default path.
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
        self._validate_config()
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        # Look for config file relative to this module
        current_dir = Path(__file__).parent.parent.parent
        return str(current_dir / "config" / "config.yaml")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file and environment variables."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            # Override with environment variables if they exist
            self._load_env_overrides(config)
            
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise
    
    def _load_env_overrides(self, config: Dict[str, Any]) -> None:
        """Load configuration overrides from environment variables."""
        # API credentials from environment variables
        if 'COPERNICUS_USERNAME' in os.environ:
            config['apis']['copernicus']['username'] = os.environ['COPERNICUS_USERNAME']
        
        if 'COPERNICUS_PASSWORD' in os.environ:
            config['apis']['copernicus']['password'] = os.environ['COPERNICUS_PASSWORD']
        
        if 'GEE_SERVICE_ACCOUNT_KEY' in os.environ:
            config['apis']['google_earth_engine']['service_account_key'] = os.environ['GEE_SERVICE_ACCOUNT_KEY']
        
        if 'GEE_PROJECT_ID' in os.environ:
            config['apis']['google_earth_engine']['project_id'] = os.environ['GEE_PROJECT_ID']
        
        # Email configuration
        if 'SMTP_USERNAME' in os.environ:
            config['notifications']['email']['username'] = os.environ['SMTP_USERNAME']
        
        if 'SMTP_PASSWORD' in os.environ:
            config['notifications']['email']['password'] = os.environ['SMTP_PASSWORD']
    
    def _validate_config(self) -> None:
        """Validate the loaded configuration."""
        required_sections = ['region', 'sentinel', 'apis', 'scheduler', 'storage', 'processing']
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate region bounds
        bounds = self.config['region']['bounds']
        if not all(key in bounds for key in ['west', 'south', 'east', 'north']):
            raise ValueError("Region bounds must include west, south, east, north coordinates")
        
        if bounds['west'] >= bounds['east']:
            raise ValueError("Western boundary must be less than eastern boundary")
        
        if bounds['south'] >= bounds['north']:
            raise ValueError("Southern boundary must be less than northern boundary")
        
        # Validate date format (basic check)
        import datetime
        try:
            datetime.datetime.strptime(self.config['sentinel']['start_date'], '%Y-%m-%d')
            datetime.datetime.strptime(self.config['sentinel']['end_date'], '%Y-%m-%d')
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD format")
        
        logger.info("Configuration validation passed")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'region.bounds.west')
            default: Default value if key is not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_region_bounds(self) -> Dict[str, float]:
        """Get region bounds as a dictionary."""
        return self.config['region']['bounds']
    
    def get_region_geometry(self) -> Dict[str, Any]:
        """Get region as GeoJSON-like geometry."""
        bounds = self.get_region_bounds()
        return {
            "type": "Polygon",
            "coordinates": [[
                [bounds['west'], bounds['south']],
                [bounds['east'], bounds['south']],
                [bounds['east'], bounds['north']],
                [bounds['west'], bounds['north']],
                [bounds['west'], bounds['south']]
            ]]
        }
    
    def get_data_dir(self, subdir: str = None) -> Path:
        """
        Get data directory path.
        
        Args:
            subdir: Subdirectory name (raw, processed, metadata)
            
        Returns:
            Path object for the data directory
        """
        base_dir = Path(self.config['storage']['base_dir'])
        
        if subdir:
            return base_dir / self.config['storage'][subdir]
        
        return base_dir
    
    def save(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to file.
        
        Args:
            path: Path to save configuration. If None, uses original path.
        """
        save_path = path or self.config_path
        
        try:
            with open(save_path, 'w', encoding='utf-8') as file:
                yaml.dump(self.config, file, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {save_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise


# Global configuration instance
_config = None

def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get global configuration instance.
    
    Args:
        config_path: Path to configuration file. Only used on first call.
        
    Returns:
        Configuration instance
    """
    global _config
    
    if _config is None:
        _config = Config(config_path)
    
    return _config

def reload_config(config_path: Optional[str] = None) -> Config:
    """
    Reload configuration from file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        New configuration instance
    """
    global _config
    _config = Config(config_path)
    return _config
