import subprocess
import sys
import os
import time
from datetime import datetime

def run_command(command, description):
    """
    Run a shell command and stream output.
    Returns True if successful, False otherwise.
    """
    print(f"\n{'='*80}")
    print(f"STEP: {description}")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    
    try:
        # Run command and stream output
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding='utf-8'
        )
        
        # Print output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                
        return_code = process.poll()
        duration = time.time() - start_time
        
        if return_code == 0:
            print(f"\n[SUCCESS] {description} completed in {duration:.2f}s")
            return True
        else:
            print(f"\n[FAILURE] {description} failed with return code {return_code}")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Failed to execute {description}: {e}")
        return False

def main():
    print(f"Pipeline started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. PDF Extraction
    # Extracts text from PDFs in Input_Folder -> Extracted_files
    if not run_command("python run_extraction.py", "1. Extract Text from PDFs"):
        sys.exit(1)
        
    # 2. Redaction & PII Masking
    # Cleans text in Extracted_files -> Redacted_and_PII_Files
    if not run_command("python run_redaction.py", "2. Redact and Mask PII"):
        sys.exit(1)
        
    # 3. Model Extraction
    # Uses LLMs to extract fields from Redacted_and_PII_Files -> MODELs/model_outputs
    # We need to change directory to MODELs for this script to work correctly with its relative imports
    print("\nSwitching to MODELs directory for final step...")
    original_cwd = os.getcwd()
    models_dir = os.path.join(original_cwd, "MODELs")
    
    try:
        os.chdir(models_dir)
        if not run_command("python run_extraction.py", "3. LLM Data Extraction"):
            sys.exit(1)
    finally:
        os.chdir(original_cwd)

    print(f"\n{'='*80}")
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
