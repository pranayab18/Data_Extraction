"""
Validation Guardrails for Extracted Fields
Ensures data quality and catches LLM hallucinations.
"""
import re
from datetime import datetime
from typing import Any, Optional, Tuple

# Valid enum values
SCHEME_TYPES = ["BUY_SIDE", "SELL_SIDE", "ONE_OFF"]
SUB_TYPES = ["PERIODIC_CLAIM", "PDC", "ONE_OFF", "COUPON", "PUC_FDC", "PREXO", "SUPER_COIN", "BANK_OFFER", "LIFESTYLE"]
YES_NO_VALUES = ["Yes", "No", "yes", "no", "YES", "NO"]

def validate_date(value: Any, field_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate date fields. Accepts multiple formats.
    Returns: (is_valid, cleaned_value, error_message)
    """
    if value is None:
        return True, None, None
    
    if not isinstance(value, str):
        return False, None, f"{field_name}: Expected string, got {type(value).__name__}"
    
    # Try common date formats
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d %B %Y",
        "%B %d, %Y"
    ]
    
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(value.strip(), fmt)
            # Normalize to YYYY-MM-DD
            return True, parsed_date.strftime("%Y-%m-%d"), None
        except ValueError:
            continue
    
    # Check if it's a date range (for duration field)
    if " to " in value.lower():
        return True, value, None
    
    return False, None, f"{field_name}: Invalid date format '{value}'"

def validate_enum(value: Any, field_name: str, allowed_values: list) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate enum fields against allowed values.
    """
    if value is None:
        return True, None, None
    
    if not isinstance(value, str):
        return False, None, f"{field_name}: Expected string, got {type(value).__name__}"
    
    # Normalize and check
    normalized = value.upper().replace("/", "_").replace("-", "_").strip()
    
    for allowed in allowed_values:
        if normalized == allowed.upper().replace("/", "_"):
            return True, allowed, None
    
    return False, None, f"{field_name}: '{value}' not in allowed values {allowed_values}"

def validate_yes_no(value: Any, field_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate Yes/No fields.
    """
    if value is None:
        return True, "No", None  # Default to No for missing boolean fields
    
    if not isinstance(value, str):
        return False, None, f"{field_name}: Expected string, got {type(value).__name__}"
    
    normalized = value.strip().lower()
    if normalized in ["yes", "y", "true", "1"]:
        return True, "Yes", None
    elif normalized in ["no", "n", "false", "0"]:
        return True, "No", None
    
    return False, None, f"{field_name}: Expected Yes/No, got '{value}'"

def validate_numeric(value: Any, field_name: str, min_val: float = None, max_val: float = None) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate numeric fields with optional bounds.
    """
    if value is None:
        return True, None, None
    
    # Handle string representations
    if isinstance(value, str):
        # Remove common currency symbols and commas
        cleaned = value.strip().replace(",", "").replace("₹", "").replace("$", "").replace("%", "")
        try:
            value = float(cleaned)
        except ValueError:
            return False, None, f"{field_name}: Cannot parse '{value}' as number"
    
    if not isinstance(value, (int, float)):
        return False, None, f"{field_name}: Expected number, got {type(value).__name__}"
    
    if min_val is not None and value < min_val:
        return False, None, f"{field_name}: {value} below minimum {min_val}"
    
    if max_val is not None and value > max_val:
        return False, None, f"{field_name}: {value} above maximum {max_val}"
    
    return True, value, None

def validate_text_length(value: Any, field_name: str, min_len: int = None, max_len: int = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate text field length.
    """
    if value is None:
        return True, None, None
    
    if not isinstance(value, str):
        return False, None, f"{field_name}: Expected string, got {type(value).__name__}"
    
    length = len(value)
    
    if min_len is not None and length < min_len:
        return False, None, f"{field_name}: Length {length} below minimum {min_len}"
    
    if max_len is not None and length > max_len:
        return False, None, f"{field_name}: Length {length} above maximum {max_len}"
    
    return True, value, None

def validate_field(field_name: str, value: Any) -> Tuple[bool, Any, Optional[str]]:
    """
    Main validation dispatcher for each field.
    Returns: (is_valid, cleaned_value, error_message)
    """
    # Date fields
    if field_name in ["start_date", "end_date", "price_drop_date"]:
        return validate_date(value, field_name)
    
    # Duration (special date range)
    if field_name == "duration":
        return validate_text_length(value, field_name, max_len=100)
    
    # Enum fields
    if field_name == "scheme_type":
        return validate_enum(value, field_name, SCHEME_TYPES)
    
    if field_name == "sub_type":
        return validate_enum(value, field_name, SUB_TYPES)
    
    # Yes/No fields
    if field_name in ["fsn_file_config_file", "min_actual_discount_or_agreed_claim", 
                      "remove_gst", "over_and_above", "scheme_document"]:
        return validate_yes_no(value, field_name)
    
    # Numeric fields
    if field_name == "gst_rate":
        return validate_numeric(value, field_name, min_val=0, max_val=100)
    
    if field_name == "max_cap":
        return validate_numeric(value, field_name, min_val=0)
    
    # Text fields with reasonable length limits
    if field_name in ["scheme_name", "vendor_name"]:
        return validate_text_length(value, field_name, max_len=200)
    
    if field_name == "scheme_description":
        return validate_text_length(value, field_name, max_len=1000)
    
    # Default: accept as-is
    return True, value, None

def validate_all_fields(extracted_data: dict) -> Tuple[dict, list]:
    """
    Validate all extracted fields.
    Returns: (validated_data, validation_errors)
    """
    validated = {}
    errors = []
    
    for field_name, value in extracted_data.items():
        is_valid, cleaned_value, error_msg = validate_field(field_name, value)
        
        if is_valid:
            validated[field_name] = cleaned_value
        else:
            validated[field_name] = value  # Keep original on error
            errors.append(error_msg)
    
    return validated, errors
