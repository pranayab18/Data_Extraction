"""
Content Redaction Script with PII Masking
Removes unnecessary content from extracted email files including:
- Forwarded message markers
- Duplicate subject lines
- Email signatures and disclaimers
- Repetitive page headers
- Email metadata

PII Masking:
- Email addresses: Masks username, preserves domain (e.g., [EMAIL_1]@flipkart.com)
- Phone numbers: Fully masked (e.g., [PHONE_1])
- Person names: Masked (e.g., [PERSON_1])
- Company names: Preserved (Flipkart, Puma, Myntra)
"""

import os
import re
import json
import csv
from pathlib import Path
from datetime import datetime

class PIIMasker:
    """Handles PII masking with consistent mapping"""
    def __init__(self):
        self.email_map = {}  # Maps email -> EMAIL_N
        self.phone_map = {}  # Maps phone -> PHONE_N
        self.name_map = {}   # Maps name -> PERSON_N
        
        # Common Indian and Western first names for detection
        self.common_names = [
            'Aditya', 'Rohit', 'Siddharth', 'Anubhav', 'Pulak', 'Abhijit', 'Debarun',
            'Sonika', 'Manish', 'Mandal', 'Arora', 'Deshwal', 'Pillai', 'Banerjee',
            'Chaudhary', 'Sharma', 'Kumar', 'Singh', 'Patel', 'Gupta', 'Verma'
        ]
        
        # Company names to preserve
        self.preserve_companies = ['Flipkart', 'Puma', 'Myntra', 'PUMA']
    
    def mask_email(self, email):
        """Mask email username but preserve domain"""
        if email not in self.email_map:
            email_id = f"EMAIL_{len(self.email_map) + 1}"
            self.email_map[email] = email_id
        
        # Extract domain
        if '@' in email:
            username, domain = email.split('@', 1)
            return f"[{self.email_map[email]}]@{domain}"
        return f"[{self.email_map[email]}]"
    
    def mask_phone(self, phone):
        """Mask phone number completely"""
        if phone not in self.phone_map:
            phone_id = f"PHONE_{len(self.phone_map) + 1}"
            self.phone_map[phone] = phone_id
        return f"[{self.phone_map[phone]}]"
    
    def mask_name(self, name):
        """Mask person name"""
        if name not in self.name_map:
            person_id = f"PERSON_{len(self.name_map) + 1}"
            self.name_map[name] = person_id
        return f"[{self.name_map[name]}]"
    
    def apply_pii_masking(self, text):
        """Apply all PII masking to text"""
        # Mask emails (preserve domain)
        email_pattern = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
        def replace_email(match):
            return self.mask_email(match.group(1))
        text = re.sub(email_pattern, replace_email, text)
        
        # Mask phone numbers (10 digits)
        phone_pattern = r'\b(\d{10})\b'
        def replace_phone(match):
            return self.mask_phone(match.group(1))
        text = re.sub(phone_pattern, replace_phone, text)
        
        # Mask person names (common names)
        for name in self.common_names:
            # Match full name patterns (First Last) or standalone names
            name_pattern = rf'\b({name}(?:\s+[A-Z][a-z]+)?)\b'
            matches = re.finditer(name_pattern, text)
            for match in matches:
                full_name = match.group(1)
                # Don't mask if it's part of a company name
                if not any(company in text[max(0, match.start()-20):match.end()+20] 
                          for company in self.preserve_companies):
                    text = text.replace(full_name, self.mask_name(full_name))
        
        return text
    
    def save_mapping(self, output_path):
        """Save PII mapping to JSON file"""
        mapping = {
            'emails': self.email_map,
            'phones': self.phone_map,
            'names': self.name_map
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)

class EmailRedactor:
    def __init__(self, pii_masker=None):
        self.pii_masker = pii_masker
        
        # Patterns to identify and remove
        self.forwarded_marker = r'^-+\s*Forwarded message\s*-+\s*$'
        self.page_header = r'^\d+/\d+/\d+,\s+\d+:\d+\s+[AP]M\s+Flipkart\.com Mail.*$'
        self.page_separator = r'^---\s*PAGE\s+\d+\s*---\s*$'
        
        # Email signature patterns
        self.signature_patterns = [
            r'^Thanks\s*&\s*Regards\s*$',
            r'^Best\s+regards,?\s*$',
            r'^Regards,?\s*$',
            r'^Thanks,?\s*$',
            r'^PUMA Sports India Pvt Ltd\.\s*$',
            r'^No\.\s*\d+.*Road\s*$',
            r'^\d{6}\s+\w+\s*$',  # Postal codes
            r'^India\s*$',
            r'^Director\s+.*$',
            r'@(puma|flipkart)\.com\s*$',
        ]
        
        # Disclaimer patterns
        self.disclaimer_patterns = [
            r'This email.*confidential',
            r'If you.*not the intended recipient',
            r'Please.*delete.*email',
            r'Confidentiality Notice',
            r'DISCLAIMER',
        ]
        
    def is_forwarded_marker(self, line):
        """Check if line is a forwarded message marker"""
        return bool(re.match(self.forwarded_marker, line.strip(), re.IGNORECASE))
    
    def is_page_header(self, line):
        """Check if line is a repetitive page header"""
        return bool(re.match(self.page_header, line.strip()))
    
    def is_page_separator(self, line):
        """Check if line is a page separator"""
        return bool(re.match(self.page_separator, line.strip()))
    
    def is_signature_line(self, line):
        """Check if line is part of email signature"""
        line_stripped = line.strip()
        for pattern in self.signature_patterns:
            if re.match(pattern, line_stripped, re.IGNORECASE):
                return True
        return False
    
    def is_disclaimer(self, line):
        """Check if line contains disclaimer text"""
        for pattern in self.disclaimer_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def extract_subject(self, line):
        """Extract subject from a line if present"""
        match = re.match(r'^Subject:\s*(.+)$', line.strip(), re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
    
    def is_fyi_line(self, line):
        """Check if line is just 'FYI'"""
        return line.strip().upper() == 'FYI'
    
    def redact_content(self, content):
        """
        Main redaction logic
        """
        lines = content.split('\n')
        redacted_lines = []
        
        subject_seen = False
        in_signature = False
        skip_next_empty_lines = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_stripped = line.strip()
            
            # Skip empty lines
            if not line_stripped:
                if skip_next_empty_lines > 0:
                    skip_next_empty_lines -= 1
                    i += 1
                    continue
                redacted_lines.append(line)
                i += 1
                continue
            
            # Remove forwarded message markers
            if self.is_forwarded_marker(line):
                skip_next_empty_lines = 2  # Skip following empty lines
                i += 1
                continue
            
            # Remove page headers (repetitive email headers on each page)
            if self.is_page_header(line):
                i += 1
                continue
            
            # Keep page separators but clean them up
            if self.is_page_separator(line):
                redacted_lines.append(line)
                i += 1
                continue
            
            # Handle subject lines - keep only the first one
            subject = self.extract_subject(line)
            if subject:
                if not subject_seen:
                    redacted_lines.append(f"Subject: {subject}")
                    subject_seen = True
                i += 1
                continue
            
            # Remove FYI lines (usually after forwarded markers)
            if self.is_fyi_line(line):
                i += 1
                continue
            
            # Remove disclaimer content
            if self.is_disclaimer(line):
                # Skip this line and potentially following disclaimer lines
                i += 1
                continue
            
            # Detect signature blocks
            if self.is_signature_line(line):
                in_signature = True
                # Skip signature lines but check if we're entering a new message
                # Look ahead to see if there's actual content coming
                j = i + 1
                found_content = False
                while j < len(lines) and j < i + 10:
                    next_line = lines[j].strip()
                    if next_line and not self.is_signature_line(lines[j]) and not next_line == 'India':
                        # Check if it's the start of a new email (has "On ... wrote:" pattern)
                        if re.match(r'^On\s+\w+,.*wrote:', next_line):
                            found_content = True
                            break
                        # Or if it's actual business content
                        if len(next_line) > 20 and not re.match(r'^\d{10}$', next_line):
                            found_content = True
                            break
                    j += 1
                
                if found_content:
                    # This is a transition, skip signature but continue
                    while i < len(lines) and (self.is_signature_line(lines[i]) or 
                                             lines[i].strip() in ['India', ''] or
                                             re.match(r'^\d{10}$', lines[i].strip())):
                        i += 1
                    continue
                else:
                    # End of document signature, skip it
                    i += 1
                    continue
            
            # Keep the line
            redacted_lines.append(line)
            i += 1
        
        # Clean up multiple consecutive empty lines
        cleaned_lines = []
        empty_count = 0
        for line in redacted_lines:
            if not line.strip():
                empty_count += 1
                if empty_count <= 2:  # Allow max 2 consecutive empty lines
                    cleaned_lines.append(line)
            else:
                empty_count = 0
                cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines)
        
        # Apply PII masking if masker is available
        if self.pii_masker:
            result = self.pii_masker.apply_pii_masking(result)
        
        return result

def process_extracted_files(input_base_dir, output_base_dir, enable_pii_masking=True):
    """
    Process all extracted files and create redacted versions with PII masking
    """
    input_path = Path(input_base_dir)
    output_path = Path(output_base_dir)
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize PII masker
    pii_masker = PIIMasker() if enable_pii_masking else None
    redactor = EmailRedactor(pii_masker)
    processed_count = 0
    
    # Find all text files in extracted directory
    for txt_file in input_path.rglob('*_full_text.txt'):
        try:
            # Read original content
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Redact content
            redacted_content = redactor.redact_content(content)
            
            # Create corresponding output path
            relative_path = txt_file.relative_to(input_path)
            output_file = output_path / relative_path
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write redacted content
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(redacted_content)
            
            processed_count += 1
            print(f"[OK] Redacted: {relative_path}")
            
        except Exception as e:
            print(f"[ERROR] Error processing {txt_file}: {e}")
    
    # Process CSV files with PII masking
    for csv_file in input_path.rglob('*.csv'):
        try:
            relative_path = csv_file.relative_to(input_path)
            output_file = output_path / relative_path
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            if pii_masker:
                # Apply PII masking to CSV
                with open(csv_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                masked_content = pii_masker.apply_pii_masking(content)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(masked_content)
                print(f"[OK] Masked CSV: {relative_path}")
            else:
                # Copy CSV file without modification
                import shutil
                shutil.copy2(csv_file, output_file)
                print(f"[OK] Copied CSV: {relative_path}")
            
        except Exception as e:
            print(f"[ERROR] Error processing CSV {csv_file}: {e}")
    
    # Save PII mapping if masking was enabled
    if pii_masker:
        mapping_file = output_path / 'pii_mapping.json'
        pii_masker.save_mapping(mapping_file)
        print(f"[OK] Saved PII mapping: pii_mapping.json")
    
    return processed_count

if __name__ == "__main__":
    # Define paths
    extracted_dir = r"c:\Users\Admin\Desktop\data\Extracted_Files"
    redacted_dir = r"c:\Users\Admin\Desktop\data\Redacted_Files"
    
    print("=" * 60)
    print("EMAIL CONTENT REDACTION WITH PII MASKING")
    print("=" * 60)
    print(f"Input:  {extracted_dir}")
    print(f"Output: {redacted_dir}")
    print("=" * 60)
    
    # Process files
    count = process_extracted_files(extracted_dir, redacted_dir)
    
    print("=" * 60)
    print(f"[SUCCESS] Successfully redacted {count} files")
    print("=" * 60)
