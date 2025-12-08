import zipfile
import os
from pathlib import Path
import logging
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

def extract_zip(file_path: str, output_dir: str = "output") -> dict:
    """
    Extracts a zip file and returns the path to the extracted content.
    """
    file_path = Path(file_path)
    basename = file_path.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create a specific directory for this zip extraction
    extract_dir = Path(output_dir) / f"{basename}_extracted_{timestamp}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Extracting Zip: {file_path} to {extract_dir}")
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        # List all extracted files
        extracted_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                extracted_files.append(str(Path(root) / file))
                
        return {
            "extract_dir": str(extract_dir),
            "files": extracted_files
        }
        
    except Exception as e:
        logger.error(f"Failed to extract zip file {file_path}: {e}")
        return {}
