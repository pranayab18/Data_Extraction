"""
Experiment Configuration for Model Evaluation Pipeline
"""
import os

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================
# OpenRouter model identifiers
# OpenRouter model identifiers
MODELS = [
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-sonnet",
]

# ============================================================================
# FIELDS TO EXTRACT
# ============================================================================
FIELDS_TO_EXTRACT = [
    "scheme_name",
    "scheme_description",
    "scheme_period",
    "duration",
    "discount_type",
    "max_cap",
    "vendor_name",
    "price_drop_date",
    "start_date",
    "end_date",
    "fsn_file_config_file",
    "min_actual_discount_or_agreed_claim",
    "remove_gst",
    "over_and_above",
    "scheme_document",
    "discount_slab_type",
    "best_bet",
    "brand_support_absolute",
    "gst_rate",
    "scheme_type",
    "sub_type"
]

# ============================================================================
# PROMPT TEMPLATES
# ============================================================================
def get_consolidated_extraction_prompt(document_text: str) -> str:
    """
    Generate a single prompt to extract all fields as a JSON object.
    """
    fields_desc = ""
    prompts = {
        "scheme_name": "Extract scheme name from subject/header",
        "scheme_description": "Key conditions or notes about the scheme",
        "scheme_period": "Duration or Event (usually Duration)",
        "duration": "Validity period: Start to End date",
        "discount_type": "% of NLC, % of MRP, or Absolute value",
        "max_cap": "Maximum support amount/cap",
        "vendor_name": "Vendor name from email",
        "price_drop_date": "PDC price drop date if mentioned",
        "start_date": "Scheme start date",
        "end_date": "Scheme end date",
        "fsn_file_config_file": "Yes if FSN data needed, else No",
        "min_actual_discount_or_agreed_claim": "Yes if commercial cap mentioned, else No",
        "remove_gst": "Yes if prices inclusive of GST, No if exclusive",
        "over_and_above": "Yes if additional support for same period, else No",
        "scheme_document": "Yes if document attached",
        "discount_slab_type": "Slab details for Buyside-Periodic",
        "best_bet": "BEST_BET info for Buyside-Periodic",
        "brand_support_absolute": "Absolute support amount for OFC only",
        "gst_rate": "GST % for One-Off claims",
        "scheme_type": "BUY_SIDE (Sellin/PP/Price Drop) | SELL_SIDE (Coupon/VPC/Prexo/Bank) | ONE_OFF (standalone)",
        "sub_type": "PERIODIC_CLAIM | PDC | ONE_OFF | COUPON | PUC_FDC | PREXO | SUPER_COIN | BANK_OFFER | LIFESTYLE"
    }

    for key in FIELDS_TO_EXTRACT:
        # Build description list
        desc = prompts.get(key, f"Extract {key}")
        fields_desc += f"- \"{key}\": {desc}\n"

    return f"""You are an automated data extraction system. Your task is to extract information from the provided document into a structured JSON format.

Instructions:
1. Extract values for each field listed below based on the description.
2. If a value is "Not Specified", "Not Found", or not present in the document, return null (for JSON) or the string "No" if it is a Yes/No field (min_actual_..., remove_gst, over_and_above, scheme_document, fsn_file...).
3. Return ONLY a valid JSON object. Do not include markdown formatting (like ```json), explanations, or extra text.

Fields to Extract:
{fields_desc}

Document:
{document_text}

JSON Output:"""


# ============================================================================
# INPUT/OUTPUT PATHS
# ============================================================================
INPUT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "Redacted_and_PII_Files")
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "evaluation_results.csv")

# ============================================================================
# API CONFIGURATION
# ============================================================================
MAX_RETRIES = 3
API_TIMEOUT = 60
RATE_LIMIT_RPM = 60
