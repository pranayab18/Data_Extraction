"""
OpenRouter API Client
Provides a unified interface for making completion requests to various LLMs via OpenRouter.
"""
import os
import time
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class OpenRouterClient:
    """Client for interacting with the OpenRouter API."""
    
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        app_name: Optional[str] = None,
        app_url: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 60
    ):
        """
        Initialize the OpenRouter client.
        
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            app_name: Application name for analytics
            app_url: Application URL for analytics
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.app_name = app_name or os.getenv("OPENROUTER_APP_NAME", "Model_Evaluation_Pipeline")
        self.app_url = app_url or os.getenv("OPENROUTER_APP_URL", "http://localhost")
        self.max_retries = max_retries
        self.timeout = timeout
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.app_url,
            "X-Title": self.app_name,
            "Content-Type": "application/json"
        })
    
    def create_completion(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 1.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a chat completion using the OpenRouter API.
        
        Args:
            model: Model identifier (e.g., "openai/gpt-4", "anthropic/claude-3-opus")
            prompt: The prompt text
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            Response dictionary containing:
                - success (bool): Whether the request succeeded
                - response (str): The generated text (if successful)
                - raw_response (dict): Full API response (if successful)
                - error (str): Error message (if failed)
                - model (str): Model used
                - parameters (dict): Parameters used
        """
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            **kwargs
        }
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    self.BASE_URL,
                    json=payload,
                    timeout=self.timeout
                )
                
                # Check for HTTP errors
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                
                # Extract the generated text
                if "choices" in data and len(data["choices"]) > 0:
                    generated_text = data["choices"][0]["message"]["content"]
                    
                    return {
                        "success": True,
                        "response": generated_text,
                        "raw_response": data,
                        "model": model,
                        "parameters": {
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "top_p": top_p
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "No choices in response",
                        "raw_response": data,
                        "model": model,
                        "parameters": {
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "top_p": top_p
                        }
                    }
                    
            except requests.exceptions.Timeout:
                error_msg = f"Request timeout (attempt {attempt + 1}/{self.max_retries})"
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return {
                    "success": False,
                    "error": error_msg,
                    "model": model,
                    "parameters": {
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "top_p": top_p
                    }
                }
                
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP error: {e.response.status_code} - {e.response.text}"
                if attempt < self.max_retries - 1 and e.response.status_code in [429, 500, 502, 503, 504]:
                    # Retry on rate limit or server errors
                    time.sleep(2 ** attempt)
                    continue
                return {
                    "success": False,
                    "error": error_msg,
                    "model": model,
                    "parameters": {
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "top_p": top_p
                    }
                }
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                return {
                    "success": False,
                    "error": error_msg,
                    "model": model,
                    "parameters": {
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "top_p": top_p
                    }
                }
        
        return {
            "success": False,
            "error": f"Max retries ({self.max_retries}) exceeded",
            "model": model,
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p
            }
        }
    
    def __del__(self):
        """Close the session when the client is destroyed."""
        if hasattr(self, 'session'):
            self.session.close()
