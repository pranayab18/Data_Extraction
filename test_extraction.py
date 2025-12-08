import pandas as pd
import zipfile
from pathlib import Path
import os
import sys

# Ensure we can import src
sys.path.append(str(Path(__file__).parent))

from src import main

def create_dummy_excel(filename):
    df = pd.DataFrame({'A': [1, 2, 3], 'B': ['x', 'y', 'z']})
    df.to_excel(filename, index=False)
    print(f"Created {filename}")

def create_dummy_zip(filename, files_to_zip):
    with zipfile.ZipFile(filename, 'w') as zf:
        for f in files_to_zip:
            zf.write(f)
    print(f"Created {filename}")

def test_run():
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    
    # Create Excel
    excel_path = test_dir / "test.xlsx"
    create_dummy_excel(excel_path)
    
    # Create Zip containing the Excel
    zip_path = test_dir / "test.zip"
    create_dummy_zip(zip_path, [excel_path])
    
    # Run extraction on the Zip
    print("Running extraction on Zip...")
    main.process_file(zip_path, output_dir="test_output")
    
    # Check results
    expected_output_dir = Path("test_output")
    if expected_output_dir.exists():
        print("Output directory created.")
        # We expect a folder for the zip extraction
        # and inside it, or in the main output, the excel extraction.
        # Based on my logic:
        # Zip extracts to: output_dir / {zip_stem}_extracted_{timestamp}
        # Then recursive process calls process_file on the extracted excel
        # Excel extracts to: output_dir / {excel_stem} / {timestamp}
        
        # So we should see folders in test_output
        found = list(expected_output_dir.glob("*"))
        print(f"Found in output: {found}")
    else:
        print("Output directory NOT created.")

if __name__ == "__main__":
    test_run()
