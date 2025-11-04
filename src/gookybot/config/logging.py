import logging
import colorlog
import os
from logging.handlers import RotatingFileHandler  # <-- Import this

def setup_logging():
    """Configures the root logger for the entire application."""
    
    log = logging.getLogger()
    log.setLevel(logging.INFO) # Set the lowest level of messages to handle

    # --- 1. Console Handler (your existing code) ---
    log_format = (
        '%(log_color)s%(levelname)-8s'
        '%(reset)s | '
        '%(asctime)s | '
        '%(name)-16s | '
        '%(log_color)s%(message)s%(reset)s'
    )
    
    formatter = colorlog.ColoredFormatter(
        log_format,
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'bold_red',
        }
    )
    
    handler = colorlog.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)

    # --- 2. File Handler (the new part) ---
    
    # Create 'logs' directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "gooky.log")

    # Use a rotating handler to prevent log files from becoming huge
    # 5MB per file, 5 backup files (gooky.log.1, gooky.log.2, etc.)
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=5*1024*1024, # 5 MB
        backupCount=5, 
        encoding='utf-8'
    )
    
    # Files don't need color codes. Use a plain text formatter.
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Add the file handler to the root logger
    log.addHandler(file_handler)

    # Note: We don't log "Logger configured" here, as it's
    # called before the logger is fully set up in main.py
