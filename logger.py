import logging
import os
from typing import Optional


def setup_logger(name: str, log_dir: Optional[str] = "logs", level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure and return a logger that writes DEBUG+ logs to a file and INFO+ to console.
    
    Args:
        name: Logger name
        log_dir: Directory to store log files (defaults to "logs")
        level: Logging level (defaults to DEBUG)
        
    Returns:
        Configured logger instance
    """
    # Create log directory if it doesn't exist
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Skip if this logger already has handlers
    if logger.handlers:
        return logger
    
    # File handler (DEBUG level) - only if log_dir is provided
    if log_dir:
        file_path = os.path.join(log_dir, f"{name}.log")
        try:
            fh = logging.FileHandler(file_path, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            
            # Formatter for file handler
            file_fmt = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s", 
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            fh.setFormatter(file_fmt)
            logger.addHandler(fh)
        except Exception as e:
            # Fallback to console-only logging if file cannot be created
            print(f"Warning: Could not create log file at {file_path}: {e}")
    
    # Console handler (INFO level)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter for console
    console_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", 
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    ch.setFormatter(console_fmt)
    logger.addHandler(ch)

    return logger