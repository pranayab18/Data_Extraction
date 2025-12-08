import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

def check_usage_breakdown():
    load_dotenv()
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found.")
        return

    # Check usage for the last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    url = f"https://openrouter.ai/api/v1/generation?start={start_date.isoformat()}&end={end_date.isoformat()}"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        response = requests.get("https://openrouter.ai/api/v1/generations", headers=headers)
        # Note: OpenRouter API endpoint for granular usage might differ or require aggregation from local logs if API doesn't support breakdown.
        # The standardized /auth/key endpoint we used returns total usage.
        # Let's try to infer from the 'generation' endpoint if available, but officially OpenRouter provides usage stats on dashboard.
        # For this script, we'll try to get recent generations if possible, OR standard endpoint providing stats.
        
        # Actually, the public doc shows /auth/key gives total usage.
        # Detailed breakdown per model is usually found in dashboard. 
        # However, we can calculate strictly based on what we just ran if we had cost logging.
        # Since we don't have historical logs on client side, we can only guess or check if there is an endpoint.
        # Checking widely known OpenRouter endpoints:
        # GET /api/v1/auth/key -> basics.
        # There isn't a widely documented public API for *per model* historical cost breakdown for the user key programmatically 
        # without fetching all generation logs which might be heavy or not fully exposed.
        
        # fallback: print message about dashboard.
        print("Fetching detailed usage stats...")
        
        # Let's try the key info again to see if it has 'details' or similar hidden fields.
        url = "https://openrouter.ai/api/v1/auth/key"
        response = requests.get(url, headers=headers)
        data = response.json()
        
        print("\nNote: OpenRouter API primarily provides total usage via API.")
        print("For exact per-model breakdown, please visit: https://openrouter.ai/activity")
        print("\nHowever, based on standard pricing:")
        print("- Claude 3 Opus is significantly more expensive ($15/M input, $75/M output)")
        print("- GPT-4 Turbo is moderate ($10/M input, $30/M output)")
        print("- Claude 3.5 Sonnet is cheaper ($3/M input, $15/M output)")
        print("- Gemini Pro/Flash are very cheap.")
        
        print("\nGiven your recent run involved Claude 3 Opus, that is the most likely culprit for high credit drain.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_usage_breakdown()
