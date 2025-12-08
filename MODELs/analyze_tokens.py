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
    for file_path in Path(input_folder).rglob("*.txt"):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            docs.append({
                "name": file_path.name,
                "chars": len(content),
                "tokens": estimate_tokens(content)
            })
            print(f"- {file_path.name}: {len(content)} chars (~{int(estimate_tokens(content))} tokens)")

    # 2. Analyze Prompts (Input Overhead)
    print(f"\nAnalyzing Prompt Overhead per Field...")
    example_doc_content = "x" * 1000 # Dummy content
    fields = config.FIELDS_TO_EXTRACT
    avg_prompt_tokens = 0
    
    for field in fields:
        # We start with empty doc to measure prompt template size
        prompt = config.get_extraction_prompt("", field)
        t_count = estimate_tokens(prompt)
        avg_prompt_tokens += t_count
    
    avg_prompt_tokens /= len(fields)
    print(f"Average Prompt Template Overhead: ~{int(avg_prompt_tokens)} tokens/field")
    print(f"Total Fields: {len(fields)}")

    # 3. Calculate Input Multiplier
    print("\n" + "-"*80)
    print("INPUT TOKEN CONSUMPTION ESTIMATE (Per Document)")
    print("-" * 80)
    
    for doc in docs:
        # For each field, we send: Prompt Template + Document Content
        tokens_per_field = doc['tokens'] + avg_prompt_tokens
        total_input_tokens = tokens_per_field * len(fields)
        cost_opus = (total_input_tokens / 1_000_000) * 15 # $15/M
        cost_sonnet = (total_input_tokens / 1_000_000) * 3 # $3/M
        
        print(f"\nDocument: {doc['name']}")
        print(f"  Base Size:      {int(doc['tokens'])} tokens")
        print(f"  Requests Made:  {len(fields)} (1 per field)")
        print(f"  Total Input:    ~{int(total_input_tokens):,} tokens")
        print(f"  Est. Cost (Opus):   ${cost_opus:.4f}")
        print(f"  Est. Cost (Sonnet): ${cost_sonnet:.4f}")

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
