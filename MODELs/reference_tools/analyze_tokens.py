import os
import json
import glob
from pathlib import Path
import experiment_config as config

def estimate_tokens(text):
    """
    Rough estimate of tokens (1 token ~= 4 chars for English text).
    Accurate enough for cost magnitude analysis.
    """
    if not text:
        return 0
    return len(text) / 4

def analyze_token_usage():
    print("="*80)
    print("TOKEN USAGE ANALYSIS")
    print("="*80)
    
    # 1. Analyze Documents (Input Source)
    input_folder = config.INPUT_FOLDER
    docs = []
    print(f"\nScanning documents in {input_folder}...")
    
    # Import preprocessing function
    from run_extraction import preprocess_document
    
    for file_path in Path(input_folder).rglob("*.txt"):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            preprocessed = preprocess_document(content)
            docs.append({
                "name": file_path.name,
                "chars": len(content),
                "preprocessed_chars": len(preprocessed),
                "tokens": estimate_tokens(content),
                "preprocessed_tokens": estimate_tokens(preprocessed)
            })
            print(f"- {file_path.name}: {len(content)} chars (~{int(estimate_tokens(content))} tokens) -> {len(preprocessed)} chars (~{int(estimate_tokens(preprocessed))} tokens after preprocessing)")

    # 2. Analyze Prompts (Input Overhead) - Using consolidated prompt
    print(f"\nAnalyzing Consolidated Prompt Overhead...")
    example_doc_content = "x" * 1000 # Dummy content
    fields = config.FIELDS_TO_EXTRACT
    
    # Get consolidated prompt size
    consolidated_prompt = config.get_consolidated_extraction_prompt(example_doc_content)
    prompt_tokens = estimate_tokens(consolidated_prompt)
    print(f"Consolidated Prompt Template: ~{int(prompt_tokens)} tokens")
    print(f"Total Fields Extracted: {len(fields)}")
    print(f"Note: Using single API call per document")

    # 3. Calculate Input Tokens (Consolidated Approach)
    print("\n" + "-"*80)
    print("INPUT TOKEN CONSUMPTION (Per Document - Consolidated)")
    print("-" * 80)
    
    for doc in docs:
        # Single call: Document + Consolidated Prompt (using preprocessed tokens)
        total_input_tokens = doc['preprocessed_tokens'] + prompt_tokens
        total_input_tokens_original = doc['tokens'] + prompt_tokens
        cost_mini = (total_input_tokens / 1_000_000) * 0.15  # GPT-4o-mini
        cost_sonnet = (total_input_tokens / 1_000_000) * 3  # Claude 3.5 Sonnet
        
        print(f"\nDocument: {doc['name']}")
        print(f"  Original Size:  {int(doc['tokens'])} tokens")
        print(f"  After Preprocessing: {int(doc['preprocessed_tokens'])} tokens ({int((1 - doc['preprocessed_tokens']/doc['tokens'])*100)}% reduction)")
        print(f"  Prompt Size:    {int(prompt_tokens)} tokens")
        print(f"  Total Input:    ~{int(total_input_tokens):,} tokens (was {int(total_input_tokens_original):,})")
        print(f"  Requests Made:  1 (consolidated)")
        print(f"  Est. Cost (GPT-4o-mini): ${cost_mini:.4f}")
        print(f"  Est. Cost (Claude 3.5):  ${cost_sonnet:.4f}")

    # 4. Analyze Output Tokens (Actuals from JSON)
    print("\n" + "-"*80)
    print("OUTPUT TOKEN CONSUMPTION (Actuals from Logs)")
    print("-" * 80)
    
    output_dir = os.path.join(os.path.dirname(__file__), "model_outputs")
    json_files = glob.glob(os.path.join(output_dir, "*.json"))
    
    for jf in json_files:
        model_name = os.path.basename(jf).replace(".json", "")
        with open(jf, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        total_output_chars = 0
        doc_count = 0
        for entry in data:
            doc_count += 1
            fields_data = entry.get('fields', {})
            for k, v in fields_data.items():
                if v and isinstance(v, str) and not v.startswith("ERROR"):
                   total_output_chars += len(v)
        
        avg_out_tokens = estimate_tokens("a" * total_output_chars)
        print(f"Model: {model_name}")
        print(f"  Processed Docs: {doc_count}")
        print(f"  Total Output:   ~{int(avg_out_tokens)} tokens")
        if doc_count > 0:
            print(f"  Avg Output/Doc: ~{int(avg_out_tokens/doc_count)} tokens")

if __name__ == "__main__":
    analyze_token_usage()
