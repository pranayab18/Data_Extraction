import os
import re
import json
from pathlib import Path
from datetime import datetime

# Configuration
INPUT_DIR = Path(r"c:\Users\Admin\Desktop\data\Redacted_and_PII_Files")
OUTPUT_DIR = Path(r"c:\Users\Admin\Desktop\data\RH fields")

def extract_scheme_name(text):
    """Extract scheme name from the Subject line."""
    # Look for line starting with "Subject:"
    match = re.search(r'^Subject:\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Fallback: First non-empty line that isn't a page marker
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("---") and not line.startswith("["):
            return line
    return None

def extract_scheme_description(text):
    """Extract body text excluding headers/footers and email clutter."""
    lines = text.splitlines()
    body_lines = []
    header_passed = False
    
    # Common greetings and closings to filter out
    greetings = ["hi ", "dear ", "hello ", "hey ", "greetings"]
    closings = ["thanks", "regards", "best", "cheers", "sincerely", "yours", "warm regards"]
    
    for line in lines:
        stripped_line = line.strip()
        lower_line = stripped_line.lower()
        
        # Skip empty lines
        if not stripped_line:
            continue

        # Skip page markers
        if stripped_line.startswith("--- PAGE"):
            continue
            
        # Detect start of body (heuristic)
        if not header_passed:
            if lower_line.startswith("subject:"):
                header_passed = True
                continue
            # If we hit a greeting, we are in the body
            if any(lower_line.startswith(g) for g in greetings):
                header_passed = True
                # Don't add the greeting line itself if it's just a greeting
                if len(stripped_line) < 50: 
                    continue
                body_lines.append(line)
                continue
            
            # If we see a long line that doesn't look like a header, assume body started
            if len(stripped_line) > 100 and not re.match(r'^[A-Z][a-z]+:', line):
                header_passed = True
                body_lines.append(line)
                continue
                
            # If we see "1." or similar list start, assume body started
            if re.match(r'^\d+\.', stripped_line):
                header_passed = True
                body_lines.append(line)
                continue
                
            continue
            
        # --- Body Filtering ---

        # Skip email headers in body (Forwarded messages/Replies)
        if re.match(r'^(From|Sent|To|Subject|Cc|Date):', line, re.IGNORECASE):
            continue
            
        # Skip "On ... wrote:" reply markers
        if re.search(r'On .*? wrote:', line, re.IGNORECASE):
            continue
            
        # Skip lines that look like lists of emails/names (e.g. <email>, Name <email>)
        if '<' in line and '@' in line and '>' in line:
            continue
            
        # Skip isolated greetings/closings in the body
        if any(lower_line.startswith(c) for c in closings) and len(stripped_line) < 50:
            continue
        if any(lower_line.startswith(g) for g in greetings) and len(stripped_line) < 50:
            continue
            
        # Skip lines that are just a name (e.g. "[PERSON_4]")
        if re.match(r'^\[PERSON_\d+\]$', stripped_line):
            continue
            
        # Skip lines that are just an email
        if re.match(r'^\[EMAIL_\d+\]@[\w\.-]+$', stripped_line):
            continue
            
        # Skip "Sent from my..."
        if "sent from my" in lower_line:
            continue

        body_lines.append(line)
        
    return "\n".join(body_lines).strip()

def extract_duration(text):
    """Extract date range."""
    # Pattern for "Date to Date"
    # Supports DD/MM/YYYY, DD-MM-YYYY, DD Month YYYY
    date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}'
    range_pattern = f"({date_pattern}).*?to.*?({date_pattern})"
    
    match = re.search(range_pattern, text, re.IGNORECASE)
    if match:
        return f"{match.group(1)} to {match.group(2)}", match.group(1), match.group(2)
        
    # Pattern for "Month/Month'YY" (e.g., May/June'25)
    month_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[/-]?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\']?(\d{2,4})'
    match = re.search(month_pattern, text, re.IGNORECASE)
    if match:
        m1, m2, year = match.groups()
        if len(year) == 2: year = "20" + year
        return f"{m1} {year} to {m2} {year}", f"{m1} {year}", f"{m2} {year}"
        
    return None, None, None

def extract_discount_type(text):
    """Identify discount type."""
    text_lower = text.lower()
    if "nlc" in text_lower:
        return "Percentage of NLC"
    if "mrp" in text_lower:
        return "Percentage of MRP"
    if "absolute" in text_lower:
        return "Absolute"
    return None

def extract_max_cap(text):
    """Extract max cap amount."""
    # Look for currency amounts near "cap", "limit", "max", "support", "budget"
    # Pattern: (cap|limit|max|support|budget)...(Rs\.?|INR|Cr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)
    pattern = r'(?:cap|limit|max|support|budget).*?(?:Rs\.?|INR)?\s*(\d+(?:,\d+)*(?:\.\d+)?(?:\s*Cr)?)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def extract_vendor_name(text):
    """Extract vendor name."""
    # 1. Look for "JBP ... (Flipkart & [Vendor])"
    match = re.search(r'Flipkart\s*&\s*([A-Za-z0-9\s]+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
        
    # 2. Look for "from party" or "to party"
    pattern = r'(?:from|to)\s+party.*?:?\s*([a-zA-Z0-9\s\.]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
        
    # 3. Look for domain in email addresses (excluding flipkart)
    emails = re.findall(r'[\w\.-]+@([\w\.-]+)', text)
    for domain in emails:
        if "flipkart" not in domain.lower() and "gmail" not in domain.lower():
            return domain.split('.')[0].title() # e.g. puma.com -> Puma
            
    return None

def extract_price_drop_date(text):
    """Extract price drop date."""
    # Look for date near "price drop" or "PDC"
    date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
    pattern = f"(?:price drop|pdc).*?({date_pattern})"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def extract_fsn(text):
    """Extract FSNs."""
    # FSN pattern: alphanumeric, usually starts with alphanumeric, length 10-16
    # This is a heuristic pattern
    pattern = r'\b[A-Z0-9]{10,16}\b'
    matches = re.findall(pattern, text)
    # Filter out common false positives (like phone numbers if they match)
    fsns = [m for m in matches if not m.isdigit()] 
    return fsns if fsns else None

def has_keyword(text, keywords):
    """Check if any of the keywords exist in text as whole words."""
    for kw in keywords:
        # Escape special characters in keyword just in case
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def determine_scheme_type(text):
    """Determine Scheme Type based on keywords."""
    
    buy_side_keywords = ["buyside", "sellin", "sellin incentive", "price protection", "pp", "price drop", "jbp", "margin", "tod", "marketing"]
    sell_side_keywords = ["coupon", "vpc", "puc", "pricing support", "sellout support", "cp", "product exchange", "prexo", "prexo bumpup", "upgrade", "super coin", "lifestyle support", "bank offers"]
    
    if has_keyword(text, buy_side_keywords):
        return "BUY_SIDE"
            
    if has_keyword(text, sell_side_keywords):
        return "SELL_SIDE"
            
    if has_keyword(text, ["one-off"]):
        return "ONE_OFF"
        
    return None

def determine_sub_type(scheme_type, text):
    """Determine Sub Type based on Scheme Type and keywords."""
    
    if scheme_type == "ONE_OFF":
        return "OFC"
    
    if scheme_type == "BUY_SIDE":
        if has_keyword(text, ["price protection", "pp", "price drop"]):
            return "PDC"
        if has_keyword(text, ["one-off"]):
            return "OFC"
        # Default for Buy Side
        if has_keyword(text, ["buyside", "sellin", "sellin incentive", "jbp", "margin", "tod"]):
            return "PERIODIC_CLAIM"
            
    elif scheme_type == "SELL_SIDE":
        if has_keyword(text, ["coupon", "vpc"]):
            return "COUPON"
        if has_keyword(text, ["exchange", "prexo", "bumpup", "upgrade", "bup"]):
            return "PREXO"
        if has_keyword(text, ["super coin"]):
            return "SUPER_COIN"
        if has_keyword(text, ["bank offers"]):
            return "BANK_OFFERS"
        if has_keyword(text, ["lifestyle support"]):
            return "LIFESTYLE"
        # Default/Fallback for Sell Side
        if has_keyword(text, ["cp", "pricing support", "sellout support"]):
            return "PUC_FDC"
            
    return None

def process_file(file_path):
    """Process a single file and extract fields."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        duration_full, start_date, end_date = extract_duration(text)
        scheme_type = determine_scheme_type(text)
        
        fields = {
            "Scheme Name": extract_scheme_name(text),
            "Scheme Description": extract_scheme_description(text),
            "Scheme Period": "Event" if "event" in text.lower() else "Duration", # Placeholder logic
            "Duration": duration_full,
            "DISCOUNT_TYPE": extract_discount_type(text),
            "Max Cap (₹) / GLOBAL_CAP_AMOUNT": extract_max_cap(text),
            "Vendor Name": extract_vendor_name(text),
            "Price Drop Date": extract_price_drop_date(text),
            "Starting At": start_date,
            "Ending At": end_date,
            "FSN File / Config File": extract_fsn(text),
            "Minimum of Actual Discount OR Agreed Claim Amount": "Yes" if extract_max_cap(text) else "No",
            "Remove GST from Final Claim Amount": "Yes" if "inclusive" in text.lower() else "No",
            "Over & Above": "Yes" if "over & above" in text.lower() or "additional support" in text.lower() else "No",
            "Scheme Document": file_path.name,
            "DISCOUNT_SLAB_TYPE": None, # Needs specific extraction logic if slab table exists
            "BEST_BET": None, # Needs specific extraction logic
            "BRAND_SUPPORT_ABSOLUTE": extract_max_cap(text) if "brand support" in text.lower() else None,
            "GST Rate": "18%" if re.search(r'GST.*?18%', text, re.IGNORECASE) else None, # Strict check for GST keyword
            "Scheme Type": scheme_type,
            "Scheme Sub Type": determine_sub_type(scheme_type, text)
        }
        
        return {
            "filename": file_path.name,
            "fields": fields
        }
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def main():
    if not INPUT_DIR.exists():
        print(f"Input directory not found: {INPUT_DIR}")
        return
        
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
    # Walk through all subdirectories
    for file_path in INPUT_DIR.rglob("*_full_text.txt"):
        print(f"Processing: {file_path.name}")
        result = process_file(file_path)
        if result:
            # Create individual output file path
            # Use the original filename but change extension to .json
            output_filename = file_path.stem + ".json"
            output_path = OUTPUT_DIR / output_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4)
            print(f"Saved: {output_filename}")
            
    print(f"Extraction complete. Individual JSON files saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
