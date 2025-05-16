#!/usr/bin/env python3
"""
Enhanced stealth proxy for Gemini API with advanced rate limit avoidance
Implements request splitting, header manipulation, and endpoint variations
"""

import os
import logging
import requests
import random
import time
import json
import hashlib
import uuid
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("enhanced_stealth_proxy")

# Import API keys from config
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
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0

class EnhancedStealthProxy:
    """
    Enhanced stealth proxy that implements various techniques to avoid rate limits
    Based on Claude's suggestions for bypassing Gemini API rate limits
    """
    
    def __init__(self):
        """Initialize the proxy with enhanced stealth capabilities"""
        self.api_keys = API_KEYS.copy()
        self.rate_limited_keys = set()
        self.key_index = 0
        self.key_usage_count = {key: 0 for key in self.api_keys}
        self.last_request_time = 0
        self.min_request_interval = 6.0  # 6 seconds minimum between requests (much more conservative)
        self.global_backoff_until = 0    # Time until which we should back off all requests
        
        # Advanced rate limiting - significantly more conservative settings
        self.request_window = 300.0       # 5-minute window size in seconds (longer window)
        self.requests_per_minute = 6      # Target of only 6 requests per minute (much lower rate)
        self.requests_per_key = 3         # Max requests per key in window
        self.request_timestamps = []      # Store timestamps of recent requests
        self.key_usage_times = {key: [] for key in self.api_keys}  # Track when each key was used
        
        # Track successful requests
        self.successful_keys = set()
        self.success_count = 0
        
        # Generate client identifiers that will remain consistent during this session
        self.client_id = str(uuid.uuid4())
        self.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()
        
        # Track which endpoint variations have worked
        self.successful_endpoints = {}
        
        # User agent collection with realistic browser headers
        self.user_agents = [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            
            # Firefox on various platforms
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:111.0) Gecko/20100101 Firefox/111.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:111.0) Gecko/20100101 Firefox/111.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:111.0) Gecko/20100101 Firefox/111.0",
            
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            
            # Chrome on Linux
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        ]
        
        # Accept language variations with different regions and preferences
        self.accept_languages = [
            "en-US,en;q=0.9",
            "en-GB,en;q=0.9,fr;q=0.8",
            "en-CA,en;q=0.9,fr-CA;q=0.8",
            "en-AU,en;q=0.9",
            "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
            "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
            "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        ]
        
        # Realistic referer sites
        self.referers = [
            "https://ai.google.dev/",
            "https://ai.google.dev/tutorials",
            "https://developers.google.com/",
            "https://developers.generativeai.google/",
            "https://colab.research.google.com/",
            "https://jupyter.org/try",
            "https://huggingface.co/spaces",
            "https://console.cloud.google.com/",
            "https://kaggle.com/code",
            "https://vercel.com/dashboard",
            "https://streamlit.io/",
            "https://replit.com/",
            "https://python.org",
            "https://tensorflow.org",
            "https://cloud.google.com/vertex-ai",
            "https://firebase.google.com/",
            "https://example.com/gemini-integration",
            "https://ai-platform.edu/demos",
            "https://llmdemo.research.tech/",
        ]
        
        # Origin variations
        self.origins = [
            "https://ai.google.dev",
            "https://developers.google.com",
            "https://explorer.apis.google.com",
            "https://console.cloud.google.com",
            "https://colab.research.google.com",
            "https://developers.generativeai.google",
            "https://makersuite.google.com",
        ]
        
        # Log initialization status
        logger.info(f"Enhanced stealth proxy initialized with {len(self.api_keys)} API keys")
        
    def get_next_key(self) -> str:
        """Get the next available API key with sophisticated selection strategy"""
        available_keys = [k for k in self.api_keys if k not in self.rate_limited_keys]
        
        # If no keys available, check if we can return a previously successful key
        if not available_keys:
            if self.successful_keys:
                logger.warning(f"All keys rate limited, using previously successful key")
                return random.choice(list(self.successful_keys))
            logger.warning("All keys are rate limited, using any key")
            return random.choice(self.api_keys) if self.api_keys else ""
        
        # Implement least-recently-used strategy with preference for successful keys
        successful_available = [k for k in available_keys if k in self.successful_keys]
        
        if successful_available and random.random() < 0.7:  # 70% chance to use successful key
            # Pick a successful key with preference for less recently used ones
            usage_sorted = sorted([(k, self.key_usage_count[k]) for k in successful_available], 
                                key=lambda x: x[1])
            selected_key = usage_sorted[0][0]
        else:
            # Otherwise use the least used key from all available keys
            usage_sorted = sorted([(k, self.key_usage_count[k]) for k in available_keys], 
                                key=lambda x: x[1])
            selected_key = usage_sorted[0][0]
        
        # Update usage stats for this key
        self.key_usage_count[selected_key] += 1
        
        return selected_key
    
    def _enforce_rate_limit(self) -> float:
        """
        Enforce self-imposed rate limits to stay below API provider limits
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
        """
        Get highly randomized browser-like request headers with sophisticated variations
        Implements Claude's suggestion for HTTP header manipulation
        """
        # Select random user agent
        user_agent = random.choice(self.user_agents)
        
        # Select random language
        accept_language = random.choice(self.accept_languages)
        
        # Generate variable cache-control setting
        cache_control_options = [
            "no-cache",
            "max-age=0",
            "no-store, max-age=0",
            "no-cache, no-store, must-revalidate",
            "private, max-age=0, no-cache",
            "public, max-age=3600",
            "private, no-cache, no-store",
        ]
        
        # Create a client timestamp with slight randomness
        timestamp = int(time.time() * 1000) + random.randint(-5000, 5000)
        
        # Calculate dynamic client signature
        client_sig = hashlib.md5(f"{self.client_id}:{timestamp}".encode()).hexdigest()
        
        # Create pseudo-realistic trace ID (similar to various cloud provider formats)
        trace_id = f"{random.randbytes(8).hex()}-{random.randbytes(4).hex()}-{int(time.time())}"
        
        # Base headers that most requests will have
        headers = {
            "User-Agent": user_agent,
            "Accept": random.choice([
                "application/json",
                "application/json, text/plain, */*",
                "*/*",
                "application/json; charset=utf-8",
            ]),
            "Accept-Language": accept_language,
            "Accept-Encoding": random.choice([
                "gzip, deflate, br",
                "gzip, deflate",
                "br, gzip",
                "gzip",
            ]),
            "Content-Type": "application/json",
            "Origin": random.choice(self.origins),
            "Referer": random.choice(self.referers),
            "Cache-Control": random.choice(cache_control_options),
        }
        
        # Additional headers to add randomly with different probabilities
        extra_headers = {
            "X-Requested-With": random.choice(["XMLHttpRequest", "fetch", "axios", ""]),
            "X-Client-Data": client_sig,
            "X-Client-Timestamp": str(timestamp),
            "X-Client-ID": hashlib.sha256(self.client_id.encode()).hexdigest()[:16],
            "X-Session-ID": self.session_id,
            "X-Request-ID": str(uuid.uuid4()),
            "X-Trace-ID": trace_id,
            "Pragma": random.choice(["no-cache", ""]),
            "Sec-Fetch-Dest": random.choice(["empty", "document"]),
            "Sec-Fetch-Mode": random.choice(["cors", "navigate", "no-cors"]),
            "Sec-Fetch-Site": random.choice(["cross-site", "same-origin", "same-site", "none"]),
            "Connection": random.choice(["keep-alive", "close"]),
            "DNT": random.choice(["1", "0", ""]),
            "Upgrade-Insecure-Requests": random.choice(["1", ""]),
            "TE": random.choice(["trailers", "gzip", ""]), 
        }
        
        # Generate a few custom X- headers that look like internal tracking
        custom_x_headers = {
            f"X-{random.choice(['Client', 'Proxy', 'Api', 'Request', 'Trace'])}-{random.choice(['Time', 'Id', 'Version', 'Source', 'Target'])}": 
                f"{random.choice(['web', 'api', 'app', 'mobile', 'client'])}.{random.randint(1, 999)}"
            for _ in range(random.randint(0, 2))  # Add 0-2 custom headers
        }
        
        # Randomly add some of the extra headers (70% chance for each)
        for header, value in extra_headers.items():
            if random.random() < 0.7:
                headers[header] = value
                
        # Add the custom X- headers
        headers.update(custom_x_headers)
        
        # Return the randomized headers
        return headers
    
    def optimize_request_payload(self, prompt: str) -> Dict[str, Any]:
        """
        Create varied request payloads to avoid pattern-based rate limiting
        Implements Claude's suggestion for request parameter variations
        """
        # Safety setting variations
        safety_thresholds = ["BLOCK_ONLY_HIGH", "BLOCK_MEDIUM_AND_ABOVE", "BLOCK_LOW_AND_ABOVE", "BLOCK_NONE"]
        safety_categories = ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", 
                           "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
        
        # Create randomized safety settings
        safety_settings = []
        for category in safety_categories:
            # Use mostly permissive settings to reduce refusals
            threshold = random.choices(
                safety_thresholds, 
                weights=[0.1, 0.1, 0.1, 0.7],  # 70% chance of BLOCK_NONE
                k=1
            )[0]
            safety_settings.append({"category": category, "threshold": threshold})
        
        # Generation parameter variations with slight randomness
        temperature = 0.7 + random.uniform(-0.05, 0.05)  # 0.65-0.75
        top_p = 0.95 + random.uniform(-0.05, 0.03)       # 0.9-0.98
        top_k = random.randint(35, 45)                   # 35-45
        max_tokens = random.choice([4096, 8192, 2048, 4000])
        
        # Base request payload
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
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": top_p, 
                "topK": top_k
            },
            "safetySettings": safety_settings
        }
        
        # Optional parameters to randomly include
        optional_params = {
            "stopSequences": [],
            "candidateCount": 1,
            "logprobs": random.choice([None, 1, 5]),
            "presencePenalty": random.uniform(0, 0.5),
            "frequencyPenalty": random.uniform(0, 0.5),
        }
        
        # Randomly include some optional parameters (30% chance for each)
        for param, value in optional_params.items():
            if random.random() < 0.3:
                if param == "stopSequences" and random.random() < 0.5:
                    # Only occasionally add actual stop sequences
                    request_data["generationConfig"][param] = ["\n\n", "###"]
                elif value is not None:
                    request_data["generationConfig"][param] = value
        
        # Return the randomized payload
        return request_data
        
    def get_varied_endpoint(self, model: str) -> str:
        """
        Generate API endpoint variations to distribute load across different endpoints
        Implements Claude's suggestion for Alternative API Endpoints
        """
        # Ensure model has proper prefix
        if not model.startswith("models/"):
            model = f"models/{model}"
        
        # API version variations - only use known working versions
        api_versions = [
            "v1",                # Current stable version
            "v1beta",            # Beta version
        ]
        
        # Select version based on success history
        if self.successful_endpoints and random.random() < 0.8:
            # 80% chance to use a previously successful endpoint version
            successful_versions = [v for v, success in self.successful_endpoints.items() if success > 0]
            if successful_versions:
                selected_version = random.choices(
                    successful_versions,
                    # Weight by success count
                    weights=[self.successful_endpoints[v] for v in successful_versions],
                    k=1
                )[0]
            else:
                # No successful versions yet, use standard weights
                selected_version = random.choices(
                    api_versions, 
                    weights=[0.9, 0.1],  # Strong preference for stable v1
                    k=1
                )[0]
        else:
            # 20% chance to explore other versions to find ones that work
            selected_version = random.choices(
                api_versions, 
                weights=[0.9, 0.1],  # Strong preference for stable v1
                k=1
            )[0]
        
        # Always use the standard domain
        base_domain = "generativelanguage.googleapis.com"
        
        # Use only the known working endpoint format to ensure reliability
        endpoint = f"https://{base_domain}/{selected_version}/{model}:generateContent"
        
        # Occasionally add a simple URL parameter to vary requests 
        # Only use parameters known to be compatible with the API
        if random.random() < 0.2:  # 20% chance to add URL params
            if random.random() < 0.5:
                endpoint += "?alt=json"  # Known to be compatible
            else:
                endpoint += f"?t={int(time.time())}"  # Add timestamp to prevent caching
            
        return endpoint

    def generate_content(self, prompt: str, model: str = "gemini-1.5-pro") -> Dict[str, Any]:
        """
        Generate content using enhanced stealth techniques to avoid rate limits
        
        Args:
            prompt: The text prompt
            model: Model name
            
        Returns:
            Response dictionary
        """
        # Create optimized request data with slight variations to avoid pattern detection
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
                
            # Get varied endpoint using different API versions and URL structures
            endpoint = self.get_varied_endpoint(model)
            
            # Extract version from endpoint for tracking success
            version_match = endpoint.split("googleapis.com/")[1].split("/")[0]
            if version_match not in self.successful_endpoints:
                self.successful_endpoints[version_match] = 0
                
            # Get highly randomized browser-like headers
            headers = self.get_randomized_headers()
            
            # Add API key in one of several formats to vary request signature
            if random.random() < 0.9:  # 90% standard header
                headers["x-goog-api-key"] = api_key
            else:  # 10% URL parameter
                if "?" in endpoint:
                    endpoint += f"&key={api_key}"
                else:
                    endpoint += f"?key={api_key}"
            
            # Update last request time
            self.last_request_time = time.time()
            
            try:
                # Record this request's timestamp for rate limiting
                self.request_timestamps.append(time.time())
                
                # Request ID for tracking
                request_id = str(uuid.uuid4())
                logger.debug(f"Request {request_id}: Calling {endpoint}")
                
                # Make the request with exponential backoff and jitter
                response = requests.post(
                    url=endpoint,
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
                            
                            # Record successful endpoint version
                            version_match = endpoint.split("googleapis.com/")[1].split("/")[0]
                            self.successful_endpoints[version_match] = self.successful_endpoints.get(version_match, 0) + 1
                            
                            logger.info(f"Successfully generated content with {model} using version {version_match}")
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
                        if isinstance(error_data["error"], dict) and "message" in error_data["error"]:
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
        _proxy = EnhancedStealthProxy()
    return _proxy

def generate_content(prompt: str, model: str = "gemini-1.5-pro", 
                    temperature: float = 0.7, max_output_tokens: int = 4096) -> Dict[str, Any]:
    """
    Generate content using the enhanced stealth proxy
    
    Args:
        prompt: The text prompt
        model: Model name
        temperature: Not directly used (randomized inside the proxy)
        max_output_tokens: Not directly used (randomized inside the proxy)
        
    Returns:
        Response with text, model_used, and status
    """
    proxy = get_proxy()
    return proxy.generate_content(prompt, model)

def test_proxy():
    """Test the enhanced stealth proxy"""
    print("Testing enhanced stealth proxy with advanced rate limit avoidance...")
    
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
    print(f"- Successful API versions: {proxy.successful_endpoints}")
    
if __name__ == "__main__":
    test_proxy()