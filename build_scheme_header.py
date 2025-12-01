"""
build_scheme_header_from_extraction.py

Reads extracted text+tables from output/<pdf_id>/<timestamp>/,
creates a combined mail_body, calls LLM (via OpenRouter) to extract all
Retailer Hub scheme header fields, and outputs scheme_header.csv.

Usage:
1. pip install python-dotenv pandas requests
2. Create .env file with:
       OPENROUTER_API_KEY=your_openrouter_key_here
       OPENROUTER_SITE_URL=https://localhost        # optional
       OPENROUTER_APP_NAME=RetailerHub-Scheme-Extractor  # optional
3. Run: python build_scheme_header_from_extraction.py
"""

import os
import json
import hashlib
from typing import Dict, Any, List

import pandas as pd
import requests
from dotenv import load_dotenv

# =============================
# Load .env
# =============================
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY missing in .env file")

OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "https://localhost")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "RetailerHub-Scheme-Extractor")

# choose any OpenRouter-supported chat model you like
OPENROUTER_MODEL = "qwen/qwen3-next-80b-a3b-instruct"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# =============================
# Folder Configuration
# =============================
OUTPUT_ROOT = "output"
FINAL_OUT_DIR = "out"
os.makedirs(FINAL_OUT_DIR, exist_ok=True)

SCHEME_HEADER_CSV = os.path.join(FINAL_OUT_DIR, "scheme_header.csv")


# =============================
# LLM Prompt
# =============================
SCHEME_SYSTEM_PROMPT = """You help prepare Flipkart Retailer Hub scheme headers from brand emails.
You will be given:
- email_subject
- email_body (plain text + pasted tables from CSVs)
Your job:
- Read the email carefully.
- Identify one or more schemes/claims described in the mail.
- For each scheme, output a JSON object with all Retailer Hub header fields filled as accurately as possible.
IMPORTANT:
- Your response MUST be ONLY a valid JSON object. No commentary, no markdown, no extra text.
- If you are unsure of a numeric value, use null.
- If you are unsure of a Yes/No flag, pick the safest default based on rules below.
=====================================
OUTPUT JSON FORMAT (STRICT)
=====================================
{
  "schemes": [
    {
      "scheme_type": "BUY_SIDE | SELL_SIDE | ONE_OFF | OTHER",
      "scheme_sub_type": "PERIODIC_CLAIM | PDC | PUC_FDC | COUPON | SUPER_COIN | PREXO | BANK_OFFER | LIFESTYLE | ONE_OFF | OTHER",
      "scheme_name": "string",
      "scheme_description": "string",
      "description": "string",
      "scheme_period": "EVENT | DURATION",
      "duration_start_date": "YYYY-MM-DD or null",
      "duration_end_date": "YYYY-MM-DD or null",
      "discount_type": "Percentage of MRP | Percentage of NLC | Absolute | Other",
      "global_cap_amount": null or number,
      "min_actual_or_agreed": "Yes | No",
      "remove_gst_from_final_claim": "Yes | No",
      "over_and_above": "Yes | No",
      "discount_slab_type": "Flat | Quantity_Slab | Value_Slab | Other",
      "best_bet": "Yes | No",
      "brand_support_absolute": null or number,
      "gst_rate": null or number,
      "price_drop_date": "YYYY-MM-DD or null",
      "starting_at": "YYYY-MM-DD or null",
      "ending_at": "YYYY-MM-DD or null",
      "vendors": [
        {
          "vendor_name": "string",
          "location": "string or null",
          "amount": number or null
        }
      ]
    }
  ]
}

If the email clearly talks about multiple distinct claims (e.g. one for June'25 and one for May'25), return multiple entries in the "schemes" array.
=====================================
1. SCHEME TYPE & SUB-TYPE CLASSIFICATION
=====================================

Use BOTH subject and body (including tables). Case-insensitive.

1.1 BUY_SIDE – PERIODIC_CLAIM (scheme_type="BUY_SIDE", scheme_sub_type="PERIODIC_CLAIM")

Trigger if the mail is about long-term / periodic / business-plan / funding-on-inwards type schemes.

Look for any of these keywords/phrases:
- "jbp", "joint business plan"
- "tot", "terms of trade"
- "sell in", "sell-in", "sellin"
- "buy side", "buyside"
- "periodic", "quarter", "q1", "q2", "q3", "q4"
- "annual", "fy", "yearly support"
- "marketing support", "gmv support", "nrv", "nrv-linked"
- "inwards", "net inwards", "inventory support"
- "business plan", "commercial alignment", "funding for fy"
If these dominate the email → classify as:
- scheme_type = "BUY_SIDE"
- scheme_sub_type = "PERIODIC_CLAIM"

1.2 BUY_SIDE – PDC (Price Drop Claim) (scheme_type="BUY_SIDE", scheme_sub_type="PDC")

Trigger if the mail is about buy price reduction / price protection.

Keywords/phrases:
- "price drop", "price protection", "pp", "pdc"
- "cost reduction", "nlc change", "cost change"
- "sellin price drop", "invoice cost correction"
- "backward margin", "revision in buy price"

1.3 SELL_SIDE – PUC_FDC (scheme_type="SELL_SIDE", scheme_sub_type="PUC_FDC")

Trigger if the mail is about sellout/CP/FDC/other sell-side pricing support.

Keywords:
- "sellout", "sell out", "sell-side"
- "puc", "cp", "fdc"
- "pricing support", "rest all support"
- "discount on selling price"
- "channel support", "market support"

1.4 SELL_SIDE – COUPON (scheme_type="SELL_SIDE", scheme_sub_type="COUPON")

Keywords:
- "coupon", "vpc"
- "promo code", "offer code"
- "discount coupon"

1.5 SELL_SIDE – SUPER COIN (scheme_type="SELL_SIDE", scheme_sub_type="SUPER_COIN")

Keywords:
- "super coin", "sc funding"

1.6 SELL_SIDE – PREXO (scheme_type="SELL_SIDE", scheme_sub_type="PREXO")

Keywords:
- "exchange", "prexo", "upgrade", "bump up", "bup", "product exchange"

1.7 SELL_SIDE – BANK OFFER (scheme_type="SELL_SIDE", scheme_sub_type="BANK_OFFER")

Keywords:
- "bank offer", "card offer"
- "hdfc offer", "axis offer", "sbi offer", etc.
- "cashback (bank)", "bank cashback"

1.8 LIFESTYLE (scheme_type="SELL_SIDE", scheme_sub_type="LIFESTYLE")

If explicitly lifestyle-specific support and not clearly coupon/puc/etc.

Keywords:
- "lifestyle" AND not clearly classifiable as coupon/puc/etc.

1.9 ONE_OFF CLAIMS (scheme_type="ONE_OFF", scheme_sub_type="ONE_OFF")

Use when email clearly says it is a one-off / single lump-sum claim.

Keywords:
- "one-off", "one off", "one off claim", "one-off sales support"
- "one time support", "one time claim"
- "lump sum", "lumpsum"

If none of the above patterns match, set:
- scheme_type = "OTHER"
- scheme_sub_type = "OTHER"

If multiple categories appear, choose the **most specific scheme** based on the main money-approved lines.  
Example: “we are approving an amount of Rs X as a one-off sales support…” → ONE_OFF dominates.

=====================================
2. SCHEME NAME, DESCRIPTION, PERIOD & DATES
=====================================

2.1 scheme_name
- Usually same as email subject, cleaned.
- If subject is very generic, you can slightly enrich (e.g. append month/year if clearly mentioned).

2.2 scheme_description
- Short 1–2 line summary of what the scheme is (type of support + period + purpose).

2.3 description
- Slightly longer free-text including important conditions:
  - any key exclusions
  - CI mismatches
  - constraints (“up to 30% promo”, “only HDFC/SBI CC EMI”, etc.)

2.4 scheme_period
- If email clearly refers to a named event (e.g., "Big Billion Days", "TBBD", "Republic Day sale", "EOSS", "End of Season Sale"), set:
  - scheme_period = "EVENT"
- Otherwise:
  - scheme_period = "DURATION"

2.5 duration_start_date & duration_end_date
- Use explicit dates or months from the mail.
- If it says "for June'25" and no specific dates, approximate:
  - duration_start_date = first day of that month (e.g., "2025-06-01")
  - duration_end_date = last day of that month (e.g., "2025-06-30")
- If the mail contains a clear date range, use that.
- If you cannot infer dates, set both to null.

2.6 starting_at, ending_at
- Copy from duration_start_date and duration_end_date respectively.

=====================================
3. DISCOUNT / FINANCIAL FIELDS
=====================================

3.1 discount_type
Pick ONE OF:
- "Percentage of MRP"
- "Percentage of NLC"
- "Absolute"
- "Other"

Rules:
- If the email explicitly says "% of MRP", "on MRP", "MRP-linked":
  → "Percentage of MRP"
- If it says "% of NLC", "on NLC", "net landed cost":
  → "Percentage of NLC"
- If the claim is clearly a fixed rupee support (e.g., "we are approving an amount of Rs 19,611,874") and not defined as a %:
  → "Absolute"
- Otherwise:
  → "Other"

3.2 global_cap_amount
- Look for any max cap language:
  - "max support Rs X", "cap of Rs X", "up to Rs X", "maximum Rs X"
- If found, set global_cap_amount = X (number only).
- If multiple caps exist, choose the one that applies to the entire scheme. If ambiguous, choose null.
- If no cap mentioned, set global_cap_amount = null.

3.3 min_actual_or_agreed
- If global_cap_amount is NOT null (a cap exists), set:
  → "Yes"
- Else:
  → "No"

3.4 brand_support_absolute
- For ONE_OFF schemes (one-off claims, lump-sum support):
  - Extract the main absolute support amount approved in the mail (e.g., "We are approving an amount of Rs 19611874").
  - Set brand_support_absolute to that number.
- For non-ONE_OFF schemes:
  - Usually null unless the mail explicitly describes an absolute brand support amount (not per-unit).
- If multiple one-off amounts for different months (e.g., June'25 and May'25), treat as separate schemes with their own brand_support_absolute.

=====================================
4. VENDOR / SPLIT DETAILS
=====================================

4.1 vendors array
- Parse any supplier/vendor split tables or lists.
- For each row, create an element:
  {
    "vendor_name": "...",
    "location": "..." or null,
    "amount": number or null
  }

Example text:
"Ganesh Enterprises, Bangalore 5295206" ⇒
  vendor_name = "Ganesh Enterprises"
  location = "Bangalore"
  amount = 5295206

If GLOBAL_MARKETING_DEL or similar entries are present without clear location or amount, you can set:
  location = null
  amount = null (or amount if visible).

=====================================
5. PDC-SPECIFIC FIELD
=====================================

5.1 price_drop_date
- Only relevant for PDC (Price Drop Claim).
- If mail gives a clear effective date of price drop (e.g., "effective from 15th June 2025"):
  → price_drop_date = that date in "YYYY-MM-DD".
- If mail gives a range for PDC, you may set the start of that range as price_drop_date.
- If no clear date:
  → price_drop_date = null.

For non-PDC schemes, set price_drop_date = null.

=====================================
6. GST & TAX FLAGS
=====================================

6.1 remove_gst_from_final_claim
- If the mail says the support/amount is "inclusive of GST", "inclusive of tax", "incl. GST":
  → "Yes"
  (Meaning: we need to remove GST from the final claim amount.)
- If it says "exclusive of GST", "plus GST", "extra GST", "exclusive of tax":
  → "No"
- If nothing is mentioned:
  → "No" (default)

6.2 gst_rate
- Mainly for ONE_OFF or lump-sum claims where GST is discussed.
- If mail says "plus GST @ 18%" or similar:
  → gst_rate = 18
- If it mentions GST but no %:
  → gst_rate = null
- If no GST mention:
  → gst_rate = null

=====================================
7. OVER & ABOVE FLAG
=====================================

over_and_above:
- If email indicates this support is *additional* to some existing/ongoing scheme during the same period:
  - phrases like "over & above", "over and above", "additional support", "extra support"
  → "Yes"
- Otherwise:
  → "No"

=====================================
8. DISCOUNT_SLAB_TYPE & BEST_BET
=====================================

8.1 discount_slab_type
- For BUY_SIDE–PERIODIC_CLAIM, look for any slab structure:
  - Quantity slabs: "0–100 units", "101–200 units" → "Quantity_Slab"
  - Value slabs: "0–10L NSV", "10–20L NSV" → "Value_Slab"
- If one clear slab type is present, use that.
- If nothing slab-based is described:
  → "Flat"
- If the slab nature is unusual:
  → "Other"

8.2 best_bet
- Only typically used for BUY_SIDE–PERIODIC_CLAIM.
- If email explicitly calls out something like "best bet", "BB", or you can see it is a flagged best-bet scheme:
  → "Yes"
- Otherwise:
  → "No"

=====================================
9. SCHEME DOCUMENT
=====================================

You will not populate "Scheme Document" field directly (that is handled by caller),
but your scheme_name, scheme_description, and description must refer to the scheme in a way that is consistent with the email subject and body.

=====================================
10. GENERAL RULES
=====================================

- Always return valid JSON per the schema at the top.
- Do not invent details that are strongly contradicted by the email.
- If you truly cannot determine a numeric field, use null (not 0).
- For Yes/No flags, follow the rules above; when completely ambiguous, default:
  - min_actual_or_agreed: "No"
  - remove_gst_from_final_claim: "No"
  - over_and_above: "No"
  - best_bet: "No"
- For dates, if you know the month and year but not the exact start/end day, use the first and last day of that month.

"""


# =============================
# Step 1: Collect Emails from output/
# =============================
def load_emails_from_output(root_dir: str) -> pd.DataFrame:
    email_records: List[Dict[str, Any]] = []

    for dirpath, _, filenames in os.walk(root_dir):
        full_txt_files = [f for f in filenames if f.endswith("_full_text.txt")]
        if not full_txt_files:
            continue

        for full_txt in full_txt_files:
            base = full_txt.replace("_full_text.txt", "")
            full_txt_path = os.path.join(dirpath, full_txt)

            with open(full_txt_path, "r", encoding="utf-8", errors="ignore") as f:
                txt_content = f.read()

            # extract subject
            subject = None
            for line in txt_content.splitlines():
                line = line.strip()
                if "Mail - " in line:
                    subject = line.split("Mail - ", 1)[-1].strip()
                    break

            if not subject:
                lines = [l.strip() for l in txt_content.splitlines() if l.strip()]
                if len(lines) >= 3:
                    subject = lines[2]
                elif lines:
                    subject = lines[0]
                else:
                    subject = base

            # collect csv tables
            table_files = [f for f in filenames if f.startswith(base) and f.endswith(".csv")]
            tables_text = ""
            for csv_name in sorted(table_files):
                csv_path = os.path.join(dirpath, csv_name)
                try:
                    df = pd.read_csv(csv_path)
                    tables_text += f"\n\nTABLE FROM {csv_name}\n" + df.to_csv(index=False)
                except Exception as e:
                    print(f"[WARN] Failed reading table {csv_path}: {e}")

            # read summary.json if exists
            summary_path = os.path.join(dirpath, base + "_summary.json")
            summary_text = ""
            if os.path.exists(summary_path):
                try:
                    with open(summary_path, "r", encoding="utf-8") as sf:
                        summary_data = json.load(sf)
                    summary_text = "\n\nSUMMARY_JSON:\n" + json.dumps(summary_data, indent=2)
                except Exception as e:
                    print(f"[WARN] Failed reading summary {summary_path}: {e}")

            full_body = txt_content + tables_text + summary_text
            source_file = base + ".pdf"

            email_records.append({
                "mail_subject": subject,
                "mail_body": full_body,
                "sourceFile": source_file
            })

    return pd.DataFrame(email_records)


# =============================
# Step 2: LLM call via OpenRouter
# =============================
def call_llm(email_subject: str, email_body: str) -> Dict[str, Any]:
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SCHEME_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({
                "mail_subject": email_subject,
                "mail_body": email_body[:12000]
            })}
        ]
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_SITE_URL,
        "X-Title": OPENROUTER_APP_NAME,
    }

    try:
        resp = requests.post(
            url=OPENROUTER_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=120,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] OpenRouter request failed: {e}")
        return {"schemes": []}

    try:
        resp_json = resp.json()
        content = resp_json["choices"][0]["message"]["content"]
        data = json.loads(content)
    except Exception as e:
        print(f"[ERROR] Failed to parse LLM JSON content: {e}")
        return {"schemes": []}

    if "schemes" not in data or not isinstance(data["schemes"], list):
        data["schemes"] = []

    return data


# =============================
# Step 3: Build scheme_header DF
# =============================
def build_scheme_header(result: Dict[str, Any], source_file: str) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    for scheme in result["schemes"]:
        raw_id = f"{scheme.get('scheme_name')}|{scheme.get('duration_start_date')}|{scheme.get('duration_end_date')}"
        scheme_id = hashlib.md5(raw_id.encode()).hexdigest()[:10]

        rows.append({
            "scheme_id": scheme_id,
            "Scheme Type": scheme.get("scheme_type"),
            "Sub Type": scheme.get("scheme_sub_type"),
            "Scheme Name": scheme.get("scheme_name"),
            "Scheme description": scheme.get("scheme_description"),
            "Description": scheme.get("description"),
            "Scheme Period": scheme.get("scheme_period"),
            "Duration_start_date": scheme.get("duration_start_date"),
            "Duration_end_date": scheme.get("duration_end_date"),
            "DISCOUNT_TYPE": scheme.get("discount_type"),
            "GLOBAL_CAP_AMOUNT": scheme.get("global_cap_amount"),
            "Minimum of actual discount OR agreed claim amount": scheme.get("min_actual_or_agreed"),
            "Remove GST from final claim amount": scheme.get("remove_gst_from_final_claim"),
            "Over & Above": scheme.get("over_and_above"),
            "DISCOUNT_SLAB_TYPE": scheme.get("discount_slab_type"),
            "BEST_BET": scheme.get("best_bet"),
            "BRAND_SUPPORT_ABSOLUTE": scheme.get("brand_support_absolute"),
            "GST Rate": scheme.get("gst_rate"),
            "Scheme Document": source_file,
            "FSN File/Config File": None,
        })

    return pd.DataFrame(rows)


# =============================
# Main
# =============================
def main():
    print("\n🔍 Scanning extracted output folders…")
    emails_df = load_emails_from_output(OUTPUT_ROOT)

    if emails_df.empty:
        print("⚠ No extracted emails found.")
        return

    all_rows: List[pd.DataFrame] = []

    for idx, row in emails_df.iterrows():
        print(f"\n➡ Processing email {idx+1}/{len(emails_df)}: {row['mail_subject'][:80]}…")
        data = call_llm(row["mail_subject"], row["mail_body"])
        df = build_scheme_header(data, row["sourceFile"])

        if not df.empty:
            all_rows.append(df)
        else:
            print("  [WARN] No schemes extracted for this email.")

    if not all_rows:
        print("\n⚠ No scheme headers extracted.")
        return

    final_df = pd.concat(all_rows, ignore_index=True)
    final_df.to_csv(SCHEME_HEADER_CSV, index=False)

    print(f"\n✅ Done! scheme_header.csv created at: {SCHEME_HEADER_CSV}")


if __name__ == "__main__":
    main()
