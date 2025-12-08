"""
Extraction Script
Retrieves fields from documents using selected models and saves directly to JSON.
"""
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from openrouter_client import OpenRouterClient
import experiment_config as config
import validators

def clean_extracted_value(value: str, field_name: str) -> Any:
    """
    Clean and normalize the extracted value.
    Returns None if the value indicates 'not found' or 'not specified'.
    """
    if not value:
        return None
        
    v_lower = value.lower().strip()
    
    # Common "not found" patterns
    not_found_patterns = [
        "not specified",
        "not found",
        "no information",
        "does not contain",
        "no value",
        "not mentioned",
        "no specific",
        "unable to extract",
        "does not provide",
        "no date",
        "no scheme",
        "no discount",
        "no cap"
    ]
    
    # exact match "no" or "none"
    if v_lower in ["no", "none", "n/a", "null"]:
        pass

    # Check for verbose "not found" sentences
    if len(v_lower) > 50 and any(p in v_lower for p in ["document does not", "not find", "no mention"]):
        return None
        
    for pattern in not_found_patterns:
        if pattern == v_lower:
            return None
        if len(value) < 100 and pattern in v_lower and "yes" not in v_lower: 
             return None

    # Specific cleaning for Scheme Type and Sub Type
    if field_name == "scheme_type":
        allowed = ["BUY_SIDE", "SELL_SIDE", "ONE_OFF"]
        for a in allowed:
            if a in value.upper():
                return a
        return None 
        
    if field_name == "sub_type":
        allowed = ["PERIODIC_CLAIM", "PDC", "ONE_OFF", "COUPON", "PUC_FDC", "PREXO", "SUPER_COIN", "BANK_OFFER", "LIFESTYLE"]
        for a in allowed:
            if a in value.upper().replace("/", "_").replace("-", "_"): 
                 return a
        if "PUC/FDC" in value.upper():
            return "PUC/FDC"
            
        return None
        
    return value

def load_documents(input_folder: str) -> List[Dict[str, str]]:
    """
    Load all text documents from the input folder recursively.
    """
    documents = []
    input_path = Path(input_folder)
    
    if not input_path.exists():
        print(f"[ERROR] Input folder not found: {input_folder}")
        return documents
    
    print(f"Searching for .txt files in {input_path}...")
    for file_path in input_path.rglob("*.txt"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                documents.append({
                    'filename': file_path.name,
                    'filepath': str(file_path),
                    'content': content
                })
                print(f"Loaded: {file_path.name} ({len(content)} chars)")
        except Exception as e:
            print(f"[ERROR] Error loading {file_path.name}: {e}")
    
    return documents

def save_json_output(output_dir: str, model: str, data: List[Dict[str, Any]]) -> None:
    """
    Save the extracted data for a model to a JSON file.
    """
    # Sanitize model name for filename (handle special chars like :)
    safe_model_name = model.replace('/', '_').replace('-', '_').replace(':', '_')
    output_file = os.path.join(output_dir, f"{safe_model_name}.json")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] {output_file}")
    except Exception as e:
        print(f"[ERROR] Failed to save {output_file}: {e}")

def run_extraction(
    documents: List[Dict[str, str]],
    client: OpenRouterClient,
    output_dir: str,
    models: List[str]
) -> None:
    """
    Run the extraction pipeline and save to JSON.
    """
    total_operations = len(documents) * len(models)
    
    print(f"\n{'='*80}")
    print(f"EXTRACTION PIPELINE STARTED")
    print(f"{'='*80}")
    print(f"Documents: {len(documents)}")
    print(f"Models: {len(models)}")
    print(f"Fields: {len(config.FIELDS_TO_EXTRACT)}")
    print(f"Total operations: {total_operations:,}")
    print(f"{'='*80}\n")
    
    operation_count = 0
    
    # Structure: model -> list of documents with fields
    results_by_model = {model: [] for model in models}
    
    # Initialize result structure for each model/doc
    for model in models:
        for document in documents:
            results_by_model[model].append({
                "document": document['filename'],
                "fields": {}
            })

    for doc_idx, document in enumerate(documents, 1):
        print(f"\n{'-'*80}")
        print(f"Document {doc_idx}/{len(documents)}: {document['filename']}")
        print(f"{'-'*80}")
        
        for model in models:
            print(f"\nUsing Model: {model}")
            
            # Find the result object for this document
            doc_result = next(r for r in results_by_model[model] if r["document"] == document['filename'])
            
            # Generate consolidated prompt
            prompt = config.get_consolidated_extraction_prompt(document['content'])
            operation_count += 1
            print(f"[{operation_count}/{(len(documents)*len(models))}] Extracting all fields...", end="", flush=True)

            try:
                # Call API
                response = client.create_completion(
                    model=model,
                    prompt=prompt,
                    temperature=0.0,
                    max_tokens=1500, # Increased for JSON output
                    top_p=1.0,
                    response_format={"type": "json_object"} if "gpt" in model else None # Hint for GPT models
                )

                if response['success']:
                    raw_content = response['response'].strip()
                    # Clean markdown code blocks if present
                    if raw_content.startswith("```json"):
                        raw_content = raw_content.replace("```json", "").replace("```", "")
                    elif raw_content.startswith("```"):
                         raw_content = raw_content.replace("```", "")
                    
                    try:
                        extracted_data = json.loads(raw_content)
                        print(f" [OK] Done (Received JSON)", end="")
                    except json.JSONDecodeError:
                        print(f" [FAIL] Invalid JSON received")
                        extracted_data = {}
                        # Could add fallback parsing here in future
                        
                    # Apply guardrails validation
                    validated_data, validation_errors = validators.validate_all_fields(extracted_data)
                    
                    if validation_errors:
                        print(f" [WARN] {len(validation_errors)} validation issues")
                        for err in validation_errors:
                            print(f"         - {err}")
                    else:
                        print(" ✓")
                        
                    # Process and assign fields
                    for field in config.FIELDS_TO_EXTRACT:
                        val = validated_data.get(field)
                        # clean values using existing logic (normalize nulls, etc)
                        if val:
                             val = clean_extracted_value(str(val), field)
                        doc_result["fields"][field] = val
                        
                else:
                    print(f" [FAIL] Failed: {response.get('error')}")
                    for field in config.FIELDS_TO_EXTRACT:
                         doc_result["fields"][field] = f"ERROR: {response.get('error')}"

            except Exception as e:
                print(f" [ERROR] Error: {e}")
                for field in config.FIELDS_TO_EXTRACT:
                     doc_result["fields"][field] = f"EXCEPTION: {str(e)}"
            
            # Save progress after each document for this model (optional, but good for safety)
            save_json_output(output_dir, model, results_by_model[model])

def main():
    print("\n" + "="*80)
    print("DATA EXTRACTION SCRIPT (JSON OUTPUT)")
    print("="*80 + "\n")
    
    # Load documents
    documents = load_documents(config.INPUT_FOLDER)
    if not documents:
        print("[ERROR] No documents found. Exiting.")
        return
    
    # Initialize Client
    try:
        client = OpenRouterClient()
        print("[OK] OpenRouter client initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize client: {e}")
        return
        
    # Output directory
    output_dir = os.path.join(os.path.dirname(__file__), "model_outputs")
    os.makedirs(output_dir, exist_ok=True)
    
    # Run Extraction
    run_extraction(
        documents=documents,
        client=client,
        output_dir=output_dir,
        models=config.MODELS
    )
    
    print("\n[DONE] Extraction completed!")
    print(f"Results saved to: {output_dir}")

if __name__ == "__main__":
    main()
