import os
import requests
import json

def get_models():
    url = "https://openrouter.ai/api/v1/models"
    response = requests.get(url)
    
    if response.status_code == 200:
        models = response.json()['data']
        claude_models = [m['id'] for m in models if 'claude' in m['id'].lower()]
        print("Available Claude Models:")
        for m in claude_models:
            print(m)
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    get_models()
