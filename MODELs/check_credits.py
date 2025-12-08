import os
import requests
import json
from dotenv import load_dotenv

def check_credits():
    load_dotenv()
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in environment or .env file.")
        return

    url = "https://openrouter.ai/api/v1/auth/key"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            key_data = data.get('data', {})
            
            print("\n" + "="*50)
            print("OPENROUTER KEY INFORMATION")
            print("="*50)
            print(f"Label:       {key_data.get('label', 'N/A')}")
            
            usage = key_data.get('usage', 0)
            limit = key_data.get('limit')
            
            print(f"Usage:       ${usage:.4f}")
            if limit:
                print(f"Limit:       ${limit:.4f}")
                print(f"Remaining:   ${(limit - usage):.4f}")
            else:
                print("Limit:       No limit / Unlimited")
                
            print(f"Free Tier:   {key_data.get('is_free_tier', False)}")
            print("="*50 + "\n")
            
        else:
            print(f"Error: {response.status_code}")
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text)
                
    except Exception as e:
        print(f"Exception occurred: {e}")

if __name__ == "__main__":
    check_credits()
