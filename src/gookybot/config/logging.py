import logging
import colorlog
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configures the root logger for the entire application."""
    
    log = logging.getLogger()
    log.setLevel(logging.INFO)

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

    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "gooky.log")

    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=5*1024*1024,
        backupCount=5, 
        encoding='utf-8'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    log.addHandler(file_handler)
