import logging
import sys
import warnings
from pathlib import Path
from datetime import datetime

def setup_logging(log_dir: str = "logs", log_level: int = logging.INFO):
    """
    Sets up logging to console and file.
    """
    # Suppress warnings FIRST before any logging setup
    warnings.filterwarnings("ignore", message=".*is image-based, camelot only works on text-based pages.*")
    warnings.filterwarnings("ignore", category=UserWarning, module="camelot")
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"extractor_{timestamp}.log"

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Suppress pdfminer warnings
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    logging.getLogger("pdfminer.pdfinterp").setLevel(logging.ERROR)

    logging.info(f"Logging initialized. Log file: {log_file}")
