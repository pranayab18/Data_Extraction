import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RunExtraction")

# Configuration
BASE_DIR = Path(__file__).parent.resolve()
INPUT_DIR = BASE_DIR / "Input_Folder"
OUTPUT_DIR = BASE_DIR / "Redacted_Files"
DATA_EXTRACTION_DIR = BASE_DIR / "data_extraction"

# Ensure data_extraction is in python path
if str(DATA_EXTRACTION_DIR) not in sys.path:
    sys.path.append(str(DATA_EXTRACTION_DIR))

try:
    from src.main import process_file
except ImportError as e:
    logger.error(f"Failed to import data_extraction modules: {e}")
    logger.error("Please ensure the 'data_extraction' repository is cloned correctly in the 'data' folder.")
    sys.exit(1)

def main():
    logger.info("Starting Data Extraction Process")
    
    # Validate Input Directory
    if not INPUT_DIR.exists():
        logger.error(f"Input directory not found: {INPUT_DIR}")
        logger.info("Creating Input_Folder...")
        try:
            INPUT_DIR.mkdir(exist_ok=True)
            logger.info("Please place your files in 'Input_Folder' and run the script again.")
        except Exception as e:
            logger.error(f"Failed to create Input_Folder: {e}")
        return

    # Create Output Directory
    if not OUTPUT_DIR.exists():
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output directory: {OUTPUT_DIR}")
        except Exception as e:
            logger.error(f"Failed to create output directory: {e}")
            return

    # Process Files
    files_found = False
    for item in INPUT_DIR.rglob("*"):
        if item.is_file():
            files_found = True
            try:
                logger.info(f"Processing file: {item.name}")
                process_file(item, str(OUTPUT_DIR))
            except Exception as e:
                logger.error(f"Error processing file {item.name}: {e}")
                # Continue processing other files even if one fails
                continue
    
    if not files_found:
        logger.warning(f"No files found in {INPUT_DIR}")
    else:
        logger.info("Extraction process completed.")

if __name__ == "__main__":
    main()
