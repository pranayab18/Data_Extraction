import pandas as pd
from pathlib import Path
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def safe_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in " ._-()" else "_" for c in s)

def extract_excel(file_path: str, output_dir: str = "output") -> dict:
    """
    Extracts all sheets from an Excel file and saves them as CSVs.
    """
    file_path = Path(file_path)
    basename = file_path.stem
    safe_base = safe_filename(basename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    run_dir = Path(output_dir) / safe_base / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Extracting Excel: {file_path} to {run_dir}")
    
    generated_files = []
    
    try:
        # Read all sheets
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names
        
        for sheet in sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=sheet)
                if df.empty:
                    continue
                
                safe_sheet = safe_filename(sheet)
                csv_name = f"{safe_base}_{safe_sheet}.csv"
                csv_path = run_dir / csv_name
                
                df.to_csv(csv_path, index=False)
                generated_files.append(str(csv_path))
            except Exception as e:
                logger.error(f"Failed to extract sheet '{sheet}' from {file_path}: {e}")
                
    except Exception as e:
        logger.error(f"Failed to open Excel file {file_path}: {e}")
        return {}

    summary = {
        "original_file": str(file_path),
        "run_dir": str(run_dir),
        "timestamp": timestamp,
        "extracted_files": generated_files
    }
    
    summary_path = run_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
        
    return summary
