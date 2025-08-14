"""
Unified Log Manager

This module provides a centralized logging management solution for the entire Prometheus project.
All logger configuration and retrieval should be done through this module.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from prometheus.configuration.config import settings


class ColoredFormatter(logging.Formatter):
    """Colored log formatter"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Purple
        'RESET': '\033[0m'        # Reset color
    }
    
    # Colored level names
    COLORED_LEVELNAMES = {
        'DEBUG': f'{COLORS["DEBUG"]}DEBUG{COLORS["RESET"]}',
        'INFO': f'{COLORS["INFO"]}INFO{COLORS["RESET"]}',
        'WARNING': f'{COLORS["WARNING"]}WARNING{COLORS["RESET"]}',
        'ERROR': f'{COLORS["ERROR"]}ERROR{COLORS["RESET"]}',
        'CRITICAL': f'{COLORS["CRITICAL"]}CRITICAL{COLORS["RESET"]}',
    }
    
    def __init__(self, fmt=None, datefmt=None, use_colors=True):
        """
        Initialize colored formatter
        
        Args:
            fmt: Log format string
            datefmt: Date format string
            use_colors: Whether to use colors
        """
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and self._supports_color()
    
    def _supports_color(self) -> bool:
        """Check if terminal supports colors"""
        # Check if running in a color-supporting terminal
        return (
            hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
            sys.platform != 'win32'  # Windows may need special handling
        ) or 'FORCE_COLOR' in os.environ
    
    def format(self, record):
        """Format log record"""
        if self.use_colors and record.levelname in self.COLORED_LEVELNAMES:
            # Save original level name
            original_levelname = record.levelname
            # Use colored level name
            record.levelname = self.COLORED_LEVELNAMES[record.levelname]
            
            # Format message
            formatted = super().format(record)
            
            # Restore original level name
            record.levelname = original_levelname
            
            return formatted
        else:
            return super().format(record)


class LoggerManager:
    """Logger manager class, responsible for creating and configuring all loggers"""
    
    _instance: Optional['LoggerManager'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'LoggerManager':
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize logger manager"""
        if not self._initialized:
            self._setup_root_logger()
            self._initialized = True
    
    def _setup_root_logger(self):
        """Setup root logger"""
        # Get root logger
        self.root_logger = logging.getLogger("prometheus")
        
        # Clear existing handlers to avoid duplication
        self.root_logger.handlers.clear()
        
        # Set log level
        log_level = getattr(settings, 'LOGGING_LEVEL', 'INFO')
        self.root_logger.setLevel(getattr(logging, log_level))
        
        # Create colored formatter for console output
        self.colored_formatter = ColoredFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # Create plain formatter for file output
        self.file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # Create console handler (using colored formatter)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self.colored_formatter)
        self.root_logger.addHandler(console_handler)
        
        # Prevent log propagation to parent logger
        self.root_logger.propagate = False
        
        # Log configuration information
        self._log_configuration()
    
    def _log_configuration(self):
        """Log configuration information"""
        config_attrs = [
            'LOGGING_LEVEL', 'ADVANCED_MODEL', 'BASE_MODEL', 'NEO4J_BATCH_SIZE',
            'WORKING_DIRECTORY', 'KNOWLEDGE_GRAPH_MAX_AST_DEPTH', 
            'KNOWLEDGE_GRAPH_CHUNK_SIZE', 'KNOWLEDGE_GRAPH_CHUNK_OVERLAP',
            'MAX_TOKEN_PER_NEO4J_RESULT', 'TEMPERATURE', 'MAX_INPUT_TOKENS', 
            'MAX_OUTPUT_TOKENS'
        ]
        
        for attr in config_attrs:
            value = getattr(settings, attr, 'Not Set')
            self.root_logger.info(f"{attr}={value}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get logger with specified name
        
        Args:
            name: Logger name, recommended to use full module path
            
        Returns:
            Configured logger instance
        """
        # Ensure logger name starts with prometheus
        if not name.startswith("prometheus"):
            name = f"prometheus.{name}"
        
        logger = logging.getLogger(name)
        
        # If it's a child logger, inherit root logger configuration
        if name != "prometheus":
            logger.parent = self.root_logger
            logger.propagate = True
        
        return logger
    
    def create_file_handler(self, log_file_path: Path, logger_name: str = "prometheus") -> logging.FileHandler:
        """
        Create file handler for specified logger
        
        Args:
            log_file_path: Log file path
            logger_name: Logger name
            
        Returns:
            Configured file handler
        """
        # Ensure log directory exists
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file handler (using plain formatter, without colors)
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(self.file_formatter)
        
        # Get logger and add handler
        logger = self.get_logger(logger_name)
        logger.addHandler(file_handler)
        
        return file_handler
    
    def create_timestamped_file_handler(self, log_dir: Path, prefix: str = "prometheus", 
                                      logger_name: str = "prometheus") -> logging.FileHandler:
        """
        Create file handler with timestamp
        
        Args:
            log_dir: Log directory
            prefix: Log file prefix
            logger_name: Logger name
            
        Returns:
            Configured file handler
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{prefix}_{timestamp}.log"
        return self.create_file_handler(log_file, logger_name)
    
    def remove_file_handler(self, handler: logging.FileHandler, logger_name: str = "prometheus"):
        """
        Remove file handler
        
        Args:
            handler: Handler to remove
            logger_name: Logger name
        """
        logger = self.get_logger(logger_name)
        logger.removeHandler(handler)
        handler.close()
    
    def enable_colors(self):
        """Enable colored log output"""
        self.colored_formatter.use_colors = True and self.colored_formatter._supports_color()
        
    def disable_colors(self):
        """Disable colored log output"""
        self.colored_formatter.use_colors = False
        
    def is_colors_enabled(self) -> bool:
        """Check if colored output is enabled"""
        return self.colored_formatter.use_colors


# Create global logger manager instance
logger_manager = LoggerManager()


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get logger
    
    Args:
        name: Logger name, recommended to use __name__ or module path
        
    Returns:
        Configured logger instance
        
    Examples:
        >>> logger = get_logger(__name__)
        >>> logger = get_logger("prometheus.tools.web_search")
    """
    return logger_manager.get_logger(name)


def create_file_handler(log_file_path: Path, logger_name: str = "prometheus") -> logging.FileHandler:
    """
    Convenience function to create file handler
    
    Args:
        log_file_path: Log file path
        logger_name: Logger name
        
    Returns:
        Configured file handler
    """
    return logger_manager.create_file_handler(log_file_path, logger_name)


def create_timestamped_file_handler(log_dir: Path, prefix: str = "prometheus", 
                                  logger_name: str = "prometheus") -> logging.FileHandler:
    """
    Convenience function to create timestamped file handler
    
    Args:
        log_dir: Log directory
        prefix: Log file prefix  
        logger_name: Logger name
        
    Returns:
        Configured file handler
    """
    return logger_manager.create_timestamped_file_handler(log_dir, prefix, logger_name)

