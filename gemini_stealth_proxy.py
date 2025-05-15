#!/usr/bin/env python3
"""
gemini_stealth_proxy.py — Simplified Gemini proxy with anti-rate-limiting measures
Optimized for Replit environment constraints
"""

import time
import logging
import os
import json
import re
import random
import hashlib
import requests
from datetime import datetime, timedelta
from collections import deque
import threading
import itertools
from typing import Dict, List, Any, Optional, Tuple, Callable, Iterator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gemini_proxy")

# ---------------------------------------------------------------------------- #
# 1. CONFIGURATION                                                             #
# ---------------------------------------------------------------------------- #

# Import API keys from existing config
try:
    from config import GEMINI_API_KEYS
    _API_KEYS = GEMINI_API_KEYS
except ImportError:
    # Default fallback if config import fails
    _API_KEYS = [
        os.environ.get("GOOGLE_API_KEY1", ""),
        os.environ.get("GOOGLE_API_KEY2", ""),
        os.environ.get("GOOGLE_API_KEY3", ""),
    ]
    
# Filter out empty keys
_API_KEYS = [key for key in _API_KEYS if key]

# Runtime configuration
_MIN_INTERVAL = float(os.environ.get("PER_KEY_INTERVAL", "5.0"))  # Minimum seconds between calls to same key
_QUOTA_RESET_HOURS = float(os.environ.get("QUOTA_RESET_HOURS", "24.0"))
_MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "4096"))
_STEALTH_MODE = os.environ.get("STEALTH_MODE", "true").lower() in ("1", "true", "yes")
_REQUEST_JITTER = float(os.environ.get("JITTER", "0.3"))
_DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
_REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "30"))
_RETRY_ATTEMPTS = int(os.environ.get("RETRY_ATTEMPTS", "3"))
_RETRY_BACKOFF = float(os.environ.get("RETRY_BACKOFF", "2.0"))
_GEMINI_ROOT = "https://generativelanguage.googleapis.com"

# ---------------------------------------------------------------------------- #
# 2. REQUEST FINGERPRINT RANDOMIZATION                                         #
# ---------------------------------------------------------------------------- #

class RequestOptimizer:
    """Optimizes requests to reduce quota usage and detection"""
    
    # Common user agent strings
    USER_AGENTS = [
        # Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    ]
    
    # Accept language headers
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9",
        "en-CA,en;q=0.9,fr-CA;q=0.8",
        "en-AU,en;q=0.9",
    ]
    
    def __init__(self):
        self.browser_signatures = self._generate_browser_signatures()
        
    def _generate_browser_signatures(self):
        """Generate realistic browser signatures for request headers"""
        signatures = []
        
        # Chrome signatures
        for _ in range(3):
            version = random.randint(110, 120)
            signatures.append({
                "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.{random.randint(4000, 4999)}.{random.randint(100, 200)} Safari/537.36",
                "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Sec-Ch-Ua": f"\"Chromium\";v=\"{version}\", \" Not A;Brand\";v=\"99\"",
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": random.choice(["Windows", "macOS", "Linux"]),
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            })
        
        # Firefox signatures
        for _ in range(2):
            version = random.randint(100, 115)
            signatures.append({
                "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}.0) Gecko/20100101 Firefox/{version}.0",
                "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            })
            
        return signatures

    def get_random_signature(self):
        """Get a random browser signature"""
        return random.choice(self.browser_signatures)

    @staticmethod
    def optimize_payload(data):
        """Optimize the request payload to reduce token usage and add variations"""
        if not data:
            return data
            
        try:
            if isinstance(data, bytes):
                payload = json.loads(data.decode('utf-8'))
            else:
                payload = json.loads(data) if isinstance(data, str) else data
                
            # Process generation content requests
            if "contents" in payload:
                for content in payload["contents"]:
                    if "parts" in content:
                        for part in content["parts"]:
                            if "text" in part:
                                # Clean up whitespace to reduce tokens
                                part["text"] = re.sub(r'\s+', ' ', part["text"]).strip()
                
            # Process generation config
            if "generationConfig" in payload:
                config = payload["generationConfig"]
                # Cap max tokens
                if config.get("maxOutputTokens", 0) > _MAX_TOKENS:
                    config["maxOutputTokens"] = _MAX_TOKENS
                    
                # Add slight variations to parameters if in stealth mode
                if _STEALTH_MODE:
                    if "temperature" in config:
                        t0 = config["temperature"]
                        config["temperature"] = float(max(0.01, min(1.99, t0 + random.uniform(-0.03, 0.03))))
                    if "topP" in config:
                        p0 = config["topP"]
                        config["topP"] = float(max(0.01, min(0.99, p0 + random.uniform(-0.01, 0.01))))
            else:
                # Add default generation config if none exists
                payload["generationConfig"] = {
                    "maxOutputTokens": int(_MAX_TOKENS),
                    "temperature": float(0.7 + random.uniform(-0.05, 0.05)),
                    "topP": float(0.8 + random.uniform(-0.05, 0.05)),
                    "topK": 40,
                }
                
            if isinstance(data, bytes):
                return json.dumps(payload).encode('utf-8')
            elif isinstance(data, str):
                return json.dumps(payload)
            else:
                return payload
                
        except Exception as e:
            logger.warning(f"Failed to optimize payload: {e}")
            return data

# ---------------------------------------------------------------------------- #
# 3. API KEY ROTATION AND RATE LIMIT MANAGEMENT                                #
# ---------------------------------------------------------------------------- #

class KeyManager:
    """Manages API keys, usage tracking, and rotation"""
    
    def __init__(self, api_keys: List[str]):
        self.api_keys = list(set(api_keys))  # Remove duplicates
        self.key_usage = {key: 0 for key in self.api_keys}
        self.last_used = {key: 0 for key in self.api_keys}
        self.rate_limited = {}  # Key -> expiry timestamp
        self.quota_used = {key: 0 for key in self.api_keys}
        self.last_quota_reset = {key: time.time() for key in self.api_keys}
        self.key_lock = threading.Lock()
        self.key_cycle = itertools.cycle(self.api_keys)
        self.request_optimizer = RequestOptimizer()
        
        # Initialize quota reset thread
        self._start_quota_reset_thread()
        
        logger.info(f"Key manager initialized with {len(self.api_keys)} API keys")
        
    def _start_quota_reset_thread(self):
        """Start background thread to periodically reset quotas"""
        def reset_quotas():
            while True:
                now = time.time()
                reset_threshold = _QUOTA_RESET_HOURS * 3600  # Convert hours to seconds
                
                with self.key_lock:
                    for key in self.api_keys:
                        if now - self.last_quota_reset.get(key, 0) > reset_threshold:
                            logger.info(f"Resetting quota for API key (daily reset)")
                            self.quota_used[key] = 0
                            self.last_quota_reset[key] = now
                
                # Check and clear rate limit blacklist
                with self.key_lock:
                    expired_keys = []
                    for key, expiry in self.rate_limited.items():
                        if now > expiry:
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        logger.info(f"Removing API key from rate limit blacklist (expired)")
                        del self.rate_limited[key]
                
                # Sleep for an hour before checking again
                time.sleep(3600)
        
        thread = threading.Thread(target=reset_quotas, daemon=True)
        thread.start()
        
    def get_next_key(self) -> str:
        """Get the next available API key using round-robin strategy with rate limit awareness"""
        with self.key_lock:
            # If all keys are rate limited, find the one that will expire soonest
            available_keys = [k for k in self.api_keys if k not in self.rate_limited]
            
            if not available_keys:
                if self.rate_limited:
                    # Find key with earliest expiry
                    next_key, expiry = min(self.rate_limited.items(), key=lambda x: x[1])
                    wait_time = max(0, expiry - time.time())
                    if wait_time > 0:
                        logger.warning(f"All keys rate-limited, waiting {wait_time:.1f}s for next available key")
                        time.sleep(wait_time)
                    return next_key
                else:
                    # Shouldn't happen if we have keys, but just in case
                    logger.error("No API keys available")
                    return ""
            
            # Try to find a key that respects the minimum interval
            now = time.time()
            for _ in range(len(available_keys)):
                key = next(self.key_cycle)
                if key in available_keys:
                    # Check if the key has had enough rest time
                    last_used = self.last_used.get(key, 0)
                    time_since_last_use = now - last_used
                    
                    if time_since_last_use >= _MIN_INTERVAL:
                        # Key has rested enough
                        self.last_used[key] = now
                        self.key_usage[key] = self.key_usage.get(key, 0) + 1
                        return key
            
            # If we get here, all keys need more rest time, pick the one used longest ago
            key = min(available_keys, key=lambda k: self.last_used.get(k, 0))
            # Apply jitter to interval
            jitter = random.uniform(0, _REQUEST_JITTER)
            time_to_wait = max(0, _MIN_INTERVAL - (now - self.last_used.get(key, 0)))
            
            if time_to_wait > 0:
                logger.info(f"Waiting {time_to_wait + jitter:.2f}s before reusing API key")
                time.sleep(time_to_wait + jitter)
            
            self.last_used[key] = time.time()
            self.key_usage[key] = self.key_usage.get(key, 0) + 1
            return key
    
    def mark_rate_limited(self, key: str, seconds: int = 120):
        """Mark a key as rate limited for a period of time"""
        if not key:
            return
            
        with self.key_lock:
            expiry = time.time() + seconds
            self.rate_limited[key] = expiry
            logger.warning(f"API key marked as rate limited for {seconds}s")
            
            # Log statistics on available vs rate-limited keys
            total_keys = len(self.api_keys)
            limited_keys = len(self.rate_limited)
            logger.info(f"Currently {limited_keys}/{total_keys} keys are rate limited")

    def execute_with_retry(self, url: str, data: Any) -> Tuple[int, Dict[str, Any]]:
        """
        Execute request with automatic retries, key rotation and rate limit handling
        
        Args:
            url: The API endpoint URL
            data: The request data (dict, JSON string or bytes)
            
        Returns:
            Tuple of (status code, response data)
        """
        # Optimize the payload
        optimized_data = self.request_optimizer.optimize_payload(data)
        
        # Get bytes for request
        if isinstance(optimized_data, dict):
            request_data = json.dumps(optimized_data).encode('utf-8')
        elif isinstance(optimized_data, str):
            request_data = optimized_data.encode('utf-8')
        else:
            request_data = optimized_data
            
        # Try multiple keys with retries
        attempt = 0
        max_attempts = min(_RETRY_ATTEMPTS * 2, len(self.api_keys) * 2)  # Scale with available keys
        
        while attempt < max_attempts:
            key = self.get_next_key()
            if not key:
                return 429, {"error": "No API keys available"}
                
            # Get randomized browser signature
            headers = self.request_optimizer.get_random_signature()
            
            # Add API-specific headers
            api_headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": key,
            }
            headers.update(api_headers)
            
            # Add jitter to request timing
            if attempt > 0 and _REQUEST_JITTER > 0:
                jitter = random.uniform(0, _REQUEST_JITTER)
                time.sleep(jitter)
            
            try:
                # Execute the request
                response = requests.post(
                    url, 
                    data=request_data,
                    headers=headers,
                    timeout=_REQUEST_TIMEOUT
                )
                
                status_code = response.status_code
                
                # Handle rate limiting
                if status_code == 429:
                    # Extract retry info if available
                    retry_seconds = 120  # Default
                    try:
                        error_data = response.json()
                        if "error" in error_data and "retry_delay" in error_data["error"]:
                            retry_seconds = error_data["error"]["retry_delay"].get("seconds", retry_seconds)
                    except:
                        pass
                        
                    # Mark key as rate limited
                    self.mark_rate_limited(key, retry_seconds)
                    attempt += 1
                    continue
                    
                # Handle successful response
                if status_code == 200:
                    try:
                        response_data = response.json()
                        return status_code, response_data
                    except:
                        logger.error("Failed to parse successful response as JSON")
                        return status_code, {"error": "Failed to parse response"}
                        
                # Handle other errors
                error_msg = f"API Error: {status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = f"API Error: {error_data['error'].get('message', str(error_data['error']))}"
                except:
                    pass
                    
                logger.warning(f"{error_msg} (attempt {attempt+1}/{max_attempts})")
                
                # Apply exponential backoff
                if attempt < max_attempts - 1:
                    backoff = _RETRY_BACKOFF ** attempt * (1 + random.uniform(0, 0.1))
                    time.sleep(backoff)
                    
                attempt += 1
                    
            except Exception as e:
                logger.error(f"Request error: {str(e)} (attempt {attempt+1}/{max_attempts})")
                attempt += 1
                
                # Apply exponential backoff
                if attempt < max_attempts - 1:
                    backoff = _RETRY_BACKOFF ** attempt * (1 + random.uniform(0, 0.1))
                    time.sleep(backoff)
        
        return 429, {"error": "All API keys exhausted or rate limited"}

# ---------------------------------------------------------------------------- #
# 4. GEMINI CLIENT API                                                         #
# ---------------------------------------------------------------------------- #

class GeminiProxy:
    """
    Client API for the Gemini Proxy
    Provides a simple interface to make API calls through the proxy
    """
    
    def __init__(self, api_keys: Optional[List[str]] = None):
        """
        Initialize the Gemini proxy client
        
        Args:
            api_keys: Optional list of API keys (defaults to keys from config)
        """
        if api_keys:
            self.key_manager = KeyManager(api_keys)
        else:
            self.key_manager = KeyManager(_API_KEYS)
    
    def generate_content(self, 
                        model: str, 
                        contents: List[Dict[str, Any]], 
                        generation_config: Optional[Dict[str, Any]] = None,
                        safety_settings: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate content using the Gemini API
        
        Args:
            model: The model to use (e.g., "gemini-1.5-pro")
            contents: List of content parts (following Gemini API format)
            generation_config: Optional generation configuration
            safety_settings: Optional safety settings (list of dicts)
            
        Returns:
            API response as dictionary
        """
        # Ensure model has proper prefix
        if not model.startswith("models/"):
            model = f"models/{model}"
            
        # Build the request URL
        url = f"{_GEMINI_ROOT}/v1/{model}:generateContent"
        
        # Build request data
        data = {
            "contents": contents
        }
        
        # Add optional parameters
        if generation_config:
            data["generationConfig"] = generation_config
            
        if safety_settings:
            data["safetySettings"] = safety_settings
            
        # Execute the request through the key manager
        status_code, response = self.key_manager.execute_with_retry(url, data)
        
        if status_code != 200:
            logger.error(f"Generate content failed with status {status_code}")
            
        return response
    
    def count_tokens(self, model: str, contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Count tokens in a prompt
        
        Args:
            model: The model to use (e.g., "gemini-1.5-pro")
            contents: List of content parts (following Gemini API format)
            
        Returns:
            API response with token count information
        """
        # Ensure model has proper prefix
        if not model.startswith("models/"):
            model = f"models/{model}"
            
        # Build the request URL
        url = f"{_GEMINI_ROOT}/v1/{model}:countTokens"
        
        # Build request data
        data = {
            "contents": contents
        }
        
        # Execute the request through the key manager
        status_code, response = self.key_manager.execute_with_retry(url, data)
        
        if status_code != 200:
            logger.error(f"Count tokens failed with status {status_code}")
            
        return response

    def get_models(self) -> Dict[str, Any]:
        """
        Get available models
        
        Returns:
            API response with model information
        """
        # Build the request URL
        url = f"{_GEMINI_ROOT}/v1/models"
        
        # Execute the request through the key manager
        status_code, response = self.key_manager.execute_with_retry(url, {})
        
        if status_code != 200:
            logger.error(f"Get models failed with status {status_code}")
            
        return response

# ---------------------------------------------------------------------------- #
# 5. UTILITY FUNCTIONS                                                         #
# ---------------------------------------------------------------------------- #

def test_proxy():
    """Test the proxy with a simple request"""
    proxy = GeminiProxy()
    
    # Simple content generation
    response = proxy.generate_content(
        model="gemini-1.5-pro",
        contents=[
            {
                "parts": [
                    {
                        "text": "Write a haiku about programming"
                    }
                ],
                "role": "user"
            }
        ],
        generation_config={
            "temperature": 0.7,
            "maxOutputTokens": 100
        }
    )
    
    if "candidates" in response:
        text = response["candidates"][0]["content"]["parts"][0]["text"]
        logger.info(f"Generated text: {text}")
        print("\nGenerated text:")
        print(text)
        print("\nProxy test successful!")
    else:
        logger.error(f"Test failed. Response: {response}")
        print("\nProxy test failed!")
        print(response)

if __name__ == "__main__":
    # Test the proxy when run directly
    test_proxy()