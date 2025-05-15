#!/usr/bin/env python3
"""
Simplified Gemini stealth proxy with essential features
A more reliable version that avoids complex type issues
"""

import os
import logging
import requests
import random
import time
import json
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fallback_proxy")

# Import API keys from existing config
try:
    from config import GEMINI_API_KEYS
    API_KEYS = GEMINI_API_KEYS
except ImportError:
    # Default fallback if config import fails
    API_KEYS = [
        os.environ.get("GOOGLE_API_KEY1", ""),
        os.environ.get("GOOGLE_API_KEY2", ""),
        os.environ.get("GOOGLE_API_KEY3", ""),
    ]
    
# Filter out empty keys
API_KEYS = [key for key in API_KEYS if key]

# Runtime configuration
GEMINI_URL = "https://generativelanguage.googleapis.com/v1"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0

class FallbackProxy:
    """Simpler implementation of the stealth proxy"""
    
    def __init__(self):
        """Initialize the proxy"""
        self.api_keys = API_KEYS.copy()
        self.rate_limited_keys = set()
        self.key_index = 0
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
        ]
        logger.info(f"Fallback proxy initialized with {len(self.api_keys)} API keys")
        
    def get_next_key(self) -> str:
        """Get the next available API key"""
        # If all keys are rate limited, use any key
        if len(self.rate_limited_keys) >= len(self.api_keys):
            logger.warning("All keys are rate limited, using any key")
            return random.choice(self.api_keys) if self.api_keys else ""
            
        # Find a key that's not rate limited
        for _ in range(len(self.api_keys)):
            self.key_index = (self.key_index + 1) % len(self.api_keys)
            key = self.api_keys[self.key_index]
            if key not in self.rate_limited_keys:
                return key
                
        # Shouldn't get here, but just in case
        return random.choice(self.api_keys) if self.api_keys else ""
        
    def mark_rate_limited(self, key: str) -> None:
        """Mark a key as rate limited"""
        if key and key not in self.rate_limited_keys:
            self.rate_limited_keys.add(key)
            logger.warning(f"API key marked as rate limited")
            logger.info(f"Currently {len(self.rate_limited_keys)}/{len(self.api_keys)} keys are rate limited")
            
            # Auto-clear rate limited keys after some time
            def clear_rate_limited_key():
                time.sleep(120)  # Wait 2 minutes
                if key in self.rate_limited_keys:
                    self.rate_limited_keys.remove(key)
                    logger.info(f"Cleared rate limit for a key, now {len(self.rate_limited_keys)}/{len(self.api_keys)} keys are rate limited")
            
            # Start a thread to clear the rate limit after a delay
            import threading
            threading.Thread(target=clear_rate_limited_key, daemon=True).start()
            
    def generate_content(self, prompt: str, model: str = "gemini-1.5-pro") -> Dict[str, Any]:
        """
        Generate content using the Gemini API
        
        Args:
            prompt: The prompt text
            model: Model name
            
        Returns:
            Response dictionary
        """
        # Ensure model has proper prefix
        if not model.startswith("models/"):
            model = f"models/{model}"
            
        # Format request data
        request_data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ],
                    "role": "user"
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096,
                "topP": 0.95,
                "topK": 40
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }
        
        # Try up to MAX_RETRIES times
        for attempt in range(MAX_RETRIES):
            # Get API key
            api_key = self.get_next_key()
            if not api_key:
                return {
                    "text": "Error: No API keys available",
                    "model_used": model,
                    "status": "error"
                }
                
            # Select random user agent
            user_agent = random.choice(self.user_agents)
            
            # Build URL and headers
            url = f"{GEMINI_URL}/{model}:generateContent"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
                "User-Agent": user_agent
            }
            
            try:
                # Make the request
                response = requests.post(
                    url=url,
                    json=request_data,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )
                
                # Check for rate limiting
                if response.status_code == 429:
                    self.mark_rate_limited(api_key)
                    if attempt < MAX_RETRIES - 1:
                        backoff = BACKOFF_FACTOR ** attempt * (1 + random.uniform(0, 0.1))
                        logger.info(f"Waiting {backoff:.2f}s before retry")
                        time.sleep(backoff)
                        continue
                    else:
                        return {
                            "text": "Error: Rate limit exceeded on all available API keys",
                            "model_used": model,
                            "status": "error"
                        }
                
                # Handle successful response
                if response.status_code == 200:
                    data = response.json()
                    if "candidates" in data and data["candidates"]:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            text = candidate["content"]["parts"][0].get("text", "")
                            return {
                                "text": text,
                                "model_used": model,
                                "status": "success"
                            }
                
                # Handle other errors
                error_msg = "Unknown error"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        if "message" in error_data["error"]:
                            error_msg = error_data["error"]["message"]
                        else:
                            error_msg = str(error_data["error"])
                except:
                    error_msg = f"API Error: Status code {response.status_code}"
                
                return {
                    "text": f"Error: {error_msg}",
                    "model_used": model,
                    "status": "error"
                }
                
            except Exception as e:
                logger.error(f"Request failed: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    backoff = BACKOFF_FACTOR ** attempt * (1 + random.uniform(0, 0.1))
                    logger.info(f"Waiting {backoff:.2f}s before retry")
                    time.sleep(backoff)
                    continue
        
        # If we reach here, all attempts failed
        return {
            "text": "Error: All API requests failed after multiple attempts",
            "model_used": model,
            "status": "error"
        }

# Create singleton instance
_proxy = None

def get_proxy():
    """Get the singleton proxy instance"""
    global _proxy
    if _proxy is None:
        _proxy = FallbackProxy()
    return _proxy

def generate_content(prompt: str, model: str = "gemini-1.5-pro", 
                    temperature: float = 0.7, max_output_tokens: int = 4096) -> Dict[str, Any]:
    """
    Generate content using the fallback proxy
    
    Args:
        prompt: The text prompt
        model: Model name
        temperature: Not used in this fallback version
        max_output_tokens: Not used in this fallback version
        
    Returns:
        Response with text, model_used, and status
    """
    proxy = get_proxy()
    return proxy.generate_content(prompt, model)

def test_proxy():
    """Test the fallback proxy"""
    print("Testing fallback proxy...")
    result = generate_content("Write a haiku about programming.")
    print(f"Status: {result['status']}")
    print(f"Model: {result['model_used']}")
    print(f"Text: {result['text']}")
    
if __name__ == "__main__":
    test_proxy()