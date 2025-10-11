"""
Logging utilities for the deforestation detection system.

This module provides centralized logging configuration and utilities
for consistent logging across all components of the system.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import sys
from datetime import datetime


def setup_logger(
    name: str = "deforestation_detection",
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    Set up logger with file and console handlers.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, no file logging.
        max_file_size_mb: Maximum log file size in MB before rotation
        backup_count: Number of backup files to keep
        console_output: Whether to output to console
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Set logging level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,  # Convert MB to bytes
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get logger instance with optional name suffix.
    
    Args:
        name: Optional name suffix for the logger
        
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"deforestation_detection.{name}")
    else:
        return logging.getLogger("deforestation_detection")


class LoggerMixin:
    """Mixin class to add logging capability to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)


def log_function_call(func):
    """
    Decorator to log function calls with parameters and execution time.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        # Log function start
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.debug(f"{func.__name__} completed successfully in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {str(e)}")
            raise
    
    return wrapper


def log_download_progress(total_files: int, current_file: int, filename: str):
    """
    Log download progress.
    
    Args:
        total_files: Total number of files to download
        current_file: Current file number (1-based)
        filename: Name of current file being downloaded
    """
    logger = get_logger("downloader")
    progress = (current_file / total_files) * 100
    
    logger.info(f"Downloading file {current_file}/{total_files} ({progress:.1f}%): {filename}")


def log_processing_step(step_name: str, details: str = None):
    """
    Log processing step with optional details.
    
    Args:
        step_name: Name of the processing step
        details: Optional additional details
    """
    logger = get_logger("processor")
    
    if details:
        logger.info(f"Processing step: {step_name} - {details}")
    else:
        logger.info(f"Processing step: {step_name}")


def log_error_with_context(error: Exception, context: dict = None):
    """
    Log error with additional context information.
    
    Args:
        error: Exception that occurred
        context: Dictionary with additional context information
    """
    logger = get_logger("error")
    
    error_msg = f"Error occurred: {type(error).__name__}: {str(error)}"
    
    if context:
        context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
        error_msg += f" | Context: {context_str}"
    
    logger.error(error_msg, exc_info=True)


def log_system_info():
    """Log system information for debugging purposes."""
    import platform
    import psutil
    
    logger = get_logger("system")
    
    logger.info("=== System Information ===")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Python version: {platform.python_version()}")
    logger.info(f"CPU cores: {psutil.cpu_count()}")
    logger.info(f"Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    logger.info(f"Disk space: {psutil.disk_usage('/').total / (1024**3):.1f} GB")
    logger.info("=== End System Information ===")


# Initialize default logger when module is imported
def initialize_logging(config=None):
    """
    Initialize logging system with configuration.
    
    Args:
        config: Configuration object. If None, uses default settings.
    """
    if config:
        log_level = config.get('logging.level', 'INFO')
        log_file = config.get('logging.file', 'deforestation_detection.log')
        max_file_size = config.get('logging.max_file_size_mb', 10)
        backup_count = config.get('logging.backup_count', 5)
    else:
        log_level = 'INFO'
        log_file = 'deforestation_detection.log'
        max_file_size = 10
        backup_count = 5
    
    setup_logger(
        level=log_level,
        log_file=log_file,
        max_file_size_mb=max_file_size,
        backup_count=backup_count
    )
