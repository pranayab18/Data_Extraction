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
    "google/gemini-1.5-flash",
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
        "scheme_name": "Extract the scheme name as mentioned by the brand, usually from the email subject line.",
        "scheme_description": "Capture any important conditions or notes mentioned in the brand email related to the scheme.",
        "scheme_period": "Identify whether the scheme is a \"Duration\" or an \"Event\". Note: Out of ~7000 claim IDs per 3 months, fewer than 10 are event-based.",
        "duration": "Extract the scheme validity period in the format \"Start Date to End Date\".",
        "discount_type": "Identify the type of discount mentioned in the email: Percentage of NLC, Percentage of MRP, Absolute value",
        "max_cap": "Extract any maximum support amount or cap specified by the brand.",
        "vendor_name": "Identify the vendor name referenced in the mail, from vendor site details if applicable.",
        "price_drop_date": "For PDC claims, extract the exact price drop date mentioned in the email.",
        "start_date": "Extract the scheme start date.",
        "end_date": "Extract the scheme end date.",
        "fsn_file_config_file": "Prepare and attach an FSN file based on the FSNs/models provided in the email. Return \"Yes\" if FSN data/file is present/needed, otherwise \"No\".",
        "min_actual_discount_or_agreed_claim": "If any commercial cap or limit is mentioned by the brand, select \"Yes\". Otherwise, select \"No\".",
        "remove_gst": "If the brand mentions prices inclusive of GST -> select \"Yes\". If prices are exclusive of GST -> select \"No\".",
        "over_and_above": "Select only if the support is additional for the same claim period and must override duplicity checks. Return \"Yes\" or \"No\".",
        "scheme_document": "Attach the brand-provided document (letter, PDF, email attachment). Return \"Yes\" if present.",
        "discount_slab_type": "For Buyside-Periodic claims, capture slab details exactly as mentioned in the brand email.",
        "best_bet": "For Buyside-Periodic claims, identify and extract the BEST_BET information as per the mail.",
        "brand_support_absolute": "For OFC claims only - extract the absolute brand support amount from the email.",
        "gst_rate": "For One-Off claims, extract the GST rate mentioned in the mail and enter in percentage.",
        "scheme_type": """Determine the 'Scheme Type' from the document based on these rules:
To determine the Scheme Type, review the email content for specific business keywords and context.
Classify the scheme as BUY_SIDE when the message includes terms such as Buyside, Sellin, Sellin Incentive, Price Protection, PP, Price Drop, or any One-Off support related to the buy side.
Classify it as SELL_SIDE when the email refers to Coupon, VPC, PUC, Pricing Support, Sellout Support, CP, Product Exchange, Prexo, Prexo Bumpup, Upgrade, Super Coin, Lifestyle support, or Bank Offers.
If the communication indicates a one-time or standalone support that does not fall clearly under periodic buy-side or sell-side structures, categorize it under ONE_OFF.
The Scheme Type should always reflect the overall commercial nature of the support described in the brand’s mail.
Return ONLY one of: BUY_SIDE, SELL_SIDE, ONE_OFF.""",
        "sub_type": """Determine the 'Sub Type' from the document based on these rules:
Once the Scheme Type is decided, identify the Scheme Sub Type using more specific keywords from the email.
For BUY_SIDE, classify the sub type as PERIODIC_CLAIM when the mail refers to Buyside, Sellin, or Sellin Incentive; choose PDC when Price Protection, PP, or Price Drop is mentioned; and use ONE_OFF when the support is explicitly described as a one-off for either buyside or sell side.
For SELL_SIDE, assign COUPON when the email contains Coupon or VPC references; choose PUC_FDC when CP, Pricing Support, or Sellout Support is mentioned, or when the support is generic without a clear category; use PREXO for Exchange, Prexo, Bumpup, Upgrade, or BUP-related schemes; select SUPER_COIN for super coin-based support; assign Bank Offers for any bank-led offer schemes; and select LIFESTYLE for lifestyle-specific support, except in cases where brands provide CN-PU.
The Sub Type should accurately reflect the closest matching intent or terminology in the email.
Return one of: PERIODIC_CLAIM, PDC, ONE_OFF, COUPON, PUC_FDC, PREXO, SUPER_COIN, BANK_OFFER, LIFESTYLE."""
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
