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
        self.key_usage_count = {key: 0 for key in self.api_keys}
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds minimum between requests
        self.global_backoff_until = 0    # Time until which we should back off all requests
        
        # Track successful requests
        self.successful_keys = set()
        self.success_count = 0
        
        # Request limiter settings
        self.requests_per_minute = 10     # Target requests per minute
        self.request_window = 60.0        # Window size in seconds
        self.request_timestamps = []       # Store timestamps of recent requests
        
        # Browser fingerprinting
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        ]
        
        self.accept_languages = [
            "en-US,en;q=0.9",
            "en-GB,en;q=0.9",
            "en-CA,en;q=0.9,fr-CA;q=0.8",
            "en-AU,en;q=0.9",
        ]
        
        logger.info(f"Enhanced fallback proxy initialized with {len(self.api_keys)} API keys")
        
    def get_next_key(self) -> str:
        """Get the next available API key using a smart selection strategy"""
        available_keys = [k for k in self.api_keys if k not in self.rate_limited_keys]
        
        # If no keys available, check if we can return a previously successful key
        if not available_keys:
            if self.successful_keys:
                logger.warning(f"All keys rate limited, using previously successful key")
                return random.choice(list(self.successful_keys))
            logger.warning("All keys are rate limited, using any key")
            return random.choice(self.api_keys) if self.api_keys else ""
        
        # Prioritize keys that have worked successfully before
        successful_available = [k for k in available_keys if k in self.successful_keys]
        if successful_available and random.random() < 0.7:  # 70% chance to use successful key
            return random.choice(successful_available)
            
        # Otherwise use least-recently-used strategy
        usage_sorted = sorted([(k, self.key_usage_count[k]) for k in available_keys], 
                             key=lambda x: x[1])
        
        # Get the least used key
        least_used_key = usage_sorted[0][0]
        self.key_usage_count[least_used_key] += 1
        
        return least_used_key
        
    def _enforce_rate_limit(self) -> float:
        """
        Enforce self-imposed rate limits to avoid triggering API rate limits
        Returns the sleep time needed to stay within rate limits
        """
        now = time.time()
        
        # Respect global backoff if set (for 429 responses)
        if now < self.global_backoff_until:
            sleep_time = self.global_backoff_until - now
            logger.info(f"In global backoff period, sleeping {sleep_time:.2f}s")
            return sleep_time
            
        # Clean up old request timestamps
        self.request_timestamps = [t for t in self.request_timestamps if now - t <= self.request_window]
        
        # If we're under our rate limit, no need to sleep
        if len(self.request_timestamps) < self.requests_per_minute:
            return 0
            
        # Calculate time to sleep to stay under rate limit
        oldest_timestamp = min(self.request_timestamps)
        time_passed = now - oldest_timestamp
        target_time = self.request_window
        
        if time_passed < target_time:
            sleep_time = target_time - time_passed + 0.1  # Add a small buffer
            logger.info(f"Rate limiting: {len(self.request_timestamps)} requests in window, sleeping {sleep_time:.2f}s")
            return sleep_time
            
        return 0
            
    def mark_rate_limited(self, key: str) -> None:
        """Mark a key as rate limited and apply global backoff"""
        if key and key not in self.rate_limited_keys:
            self.rate_limited_keys.add(key)
            logger.warning(f"API key marked as rate limited")
            logger.info(f"Currently {len(self.rate_limited_keys)}/{len(self.api_keys)} keys are rate limited")
            
            # Set global backoff if many keys are rate limited
            rate_limited_ratio = len(self.rate_limited_keys) / len(self.api_keys)
            if rate_limited_ratio > 0.25:  # If more than 25% of keys are rate limited
                backoff_time = 60 * rate_limited_ratio  # Scale backoff with ratio (15s to 60s)
                self.global_backoff_until = time.time() + backoff_time
                logger.warning(f"Setting global backoff for {backoff_time:.1f}s due to high rate limiting")
            
            # Auto-clear rate limited keys after some time
            def clear_rate_limited_key():
                time.sleep(180)  # Wait 3 minutes
                if key in self.rate_limited_keys:
                    self.rate_limited_keys.remove(key)
                    logger.info(f"Cleared rate limit for a key, now {len(self.rate_limited_keys)}/{len(self.api_keys)} keys are rate limited")
            
            # Start a thread to clear the rate limit after a delay
            import threading
            threading.Thread(target=clear_rate_limited_key, daemon=True).start()
            
    def get_randomized_headers(self) -> Dict[str, str]:
        """Get randomized browser-like request headers"""
        user_agent = random.choice(self.user_agents)
        accept_language = random.choice(self.accept_languages)
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "Referer": random.choice([
                "https://ai.google.dev/",
                "https://developers.google.com/",
                "https://developers.generativeai.google/",
                "https://colab.research.google.com/"
            ]),
            "Connection": "keep-alive",
        }
        
        return headers
    
    def optimize_request_payload(self, prompt: str) -> Dict[str, Any]:
        """Optimize request payload to reduce detection and token usage"""
        # Create safety settings with varied thresholds
        safety_thresholds = ["BLOCK_ONLY_HIGH", "BLOCK_MEDIUM_AND_ABOVE", "BLOCK_LOW_AND_ABOVE", "BLOCK_NONE"]
        safety_settings = []
        
        # Add small variations to safety settings
        for category in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", 
                        "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]:
            # Use mostly permissive settings to reduce refusals
            threshold = random.choices(
                safety_thresholds, 
                weights=[0.1, 0.1, 0.1, 0.7],  # 70% chance of BLOCK_NONE
                k=1
            )[0]
            safety_settings.append({"category": category, "threshold": threshold})
        
        # Slight variation in generation parameters
        temperature = 0.7 + random.uniform(-0.05, 0.05)  # 0.65-0.75
        top_p = 0.95 + random.uniform(-0.05, 0.03)       # 0.9-0.98
        top_k = random.randint(35, 45)                   # 35-45
        
        return {
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
                "temperature": temperature,
                "maxOutputTokens": 4096,
                "topP": top_p, 
                "topK": top_k
            },
            "safetySettings": safety_settings
        }
    
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
            
        # Create optimized request data with slight variations
        request_data = self.optimize_request_payload(prompt)
        
        # Apply comprehensive rate limiting strategy
        # 1. Check global backoff and rate limits
        sleep_time = self._enforce_rate_limit()
        if sleep_time > 0:
            time.sleep(sleep_time)
            
        # 2. Enforce minimum gap between consecutive requests
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            logger.debug(f"Enforcing minimum request interval: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        # Try up to MAX_RETRIES times
        for attempt in range(MAX_RETRIES):
            # Get API key with smart selection
            api_key = self.get_next_key()
            if not api_key:
                return {
                    "text": "Error: No API keys available",
                    "model_used": model,
                    "status": "error"
                }
                
            # Build URL (using standard format - the custom format caused 404 errors)
            url = f"{GEMINI_URL}/{model}:generateContent"
            
            # Get randomized browser-like headers
            headers = self.get_randomized_headers()
            headers["x-goog-api-key"] = api_key
            
            # Update last request time
            self.last_request_time = time.time()
            
            try:
                # Record this request's timestamp for rate limiting
                self.request_timestamps.append(time.time())
                
                # Make the request with exponential backoff and jitter
                response = requests.post(
                    url=url,
                    json=request_data,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )
                
                # Check for rate limiting
                if response.status_code == 429:
                    self.mark_rate_limited(api_key)
                    
                    # Apply exponential backoff with jitter
                    if attempt < MAX_RETRIES - 1:
                        # Calculate backoff time: base^attempt * (1 + jitter)
                        # Use larger backoff factor on later attempts
                        factor = BACKOFF_FACTOR * (1 + attempt * 0.5)  # Increases with each attempt
                        jitter = random.uniform(0, 0.3)  # 0-30% randomness
                        backoff = factor ** (attempt + 1) * (1 + jitter)
                        
                        # Cap backoff at 30 seconds
                        backoff = min(backoff, 30.0)
                        
                        logger.info(f"Rate limited (429): Backing off {backoff:.2f}s before retry")
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
                            
                            # Record successful key usage
                            self.successful_keys.add(api_key)
                            self.success_count += 1
                            
                            logger.info(f"Successfully generated content with {model}")
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
    print("Testing enhanced fallback proxy...")
    
    # Try a simple request first
    print("\nTest 1: Basic request")
    result = generate_content("Write a haiku about programming.")
    print(f"Status: {result['status']}")
    print(f"Model: {result['model_used']}")
    print(f"Text: {result['text'][:100]}..." if len(result.get('text', '')) > 100 else f"Text: {result.get('text', '')}")
    
    if result['status'] == 'success':
        # If successful, try a second request to test rate limiting
        print("\nTest 2: Follow-up request to test rate limiting")
        time.sleep(3)  # Short delay
        result2 = generate_content("Explain quantum computing in one sentence.")
        print(f"Status: {result2['status']}")
        print(f"Model: {result2['model_used']}")
        print(f"Text: {result2['text'][:100]}..." if len(result2.get('text', '')) > 100 else f"Text: {result2.get('text', '')}")
    
    # Print statistics
    proxy = get_proxy()
    print(f"\nStatistics:")
    print(f"- API Keys total: {len(proxy.api_keys)}")
    print(f"- Rate limited keys: {len(proxy.rate_limited_keys)}")
    print(f"- Successful keys: {len(proxy.successful_keys)}")
    print(f"- Success count: {proxy.success_count}")
    
if __name__ == "__main__":
    test_proxy()