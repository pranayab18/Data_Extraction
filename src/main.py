import argparse
import logging
from pathlib import Path
import sys
import mimetypes

# Add src to path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent))

from src.logger import setup_logging
from src import extractor
from src import excel_handler
from src import zip_handler

logger = logging.getLogger(__name__)

def get_file_type(file_path: Path) -> str:
    """
    Determine file type based on extension.
    """
    ext = file_path.suffix.lower()
    if ext == '.pdf':
        return 'pdf'
    elif ext in ['.xlsx', '.xls']:
        return 'excel'
    elif ext in ['.zip']:
        return 'zip'
    return 'unknown'

def process_file(file_path: Path, output_dir: str = "output", recursive: bool = True):
    """
    Dispatch file to appropriate handler.
    """
    ftype = get_file_type(file_path)
    
    if ftype == 'pdf':
        logger.info(f"Processing PDF: {file_path}")
        extractor.run_for_pdf(str(file_path), output_dir=output_dir)
        
    elif ftype == 'excel':
        logger.info(f"Processing Excel: {file_path}")
        excel_handler.extract_excel(str(file_path), output_dir)
        
    elif ftype == 'zip':
        logger.info(f"Processing Zip: {file_path}")
        result = zip_handler.extract_zip(str(file_path), output_dir)
        
        if recursive and result and 'files' in result:
            logger.info(f"Recursively processing contents of {file_path}")
            for extracted_file in result['files']:
                process_file(Path(extracted_file), output_dir, recursive=False) # Avoid infinite recursion depth issues if needed, but 1 level is usually fine. Let's keep it simple for now.
                # Actually, recursive=True is probably fine unless we have zip bombs. 
                # Let's pass recursive=True to allow nested zips? 
                # For safety, maybe just process immediate children for now or stick to the flag.
                # The user asked for "pdfs, zip files, excel sheets", implying they might be mixed.
                pass

    else:
        logger.debug(f"Skipping unsupported file type: {file_path}")

def main():
    parser = argparse.ArgumentParser(description="Universal Data Extractor (PDF, Excel, Zip)")
    parser.add_argument("input", help="Input file or directory")
    parser.add_argument("--output", default="output", help="Output directory")
    
    args = parser.parse_args()
    
    setup_logging()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        logger.error(f"Input path does not exist: {input_path}")
        return

    if input_path.is_file():
        process_file(input_path, args.output)
    elif input_path.is_dir():
        for item in input_path.rglob("*"):
            if item.is_file():
                process_file(item, args.output)

if __name__ == "__main__":
    main()
