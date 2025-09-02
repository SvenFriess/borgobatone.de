import logging
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
import os

def setup_logger(name: str = "signal_bot", log_file: str = "borgo_chatbot.log"):
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Datei-Handler mit Rotation
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, log_file),
        maxBytes=5 * 1024 * 1024,
        backupCount=5
    )
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Konsole mit Farben (Rich)
    console_handler = RichHandler(rich_tracebacks=True)
    console_handler.setLevel(logging.INFO)

    # Handler nur einmal hinzufügen
    if not logger.hasHandlers():
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger