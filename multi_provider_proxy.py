#!/usr/bin/env python3
"""
Multi-provider stealth proxy for handling API rate limits
Integrates Gemini as primary with fallbacks to OpenAI and Anthropic
"""

import os
import logging
import json
import requests
import random
import time
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("multi_provider_proxy")

# Import API keys from config
try:
    from config import GEMINI_API_KEYS, OPENAI_API_KEY, ANTHROPIC_API_KEY
    API_KEYS = GEMINI_API_KEYS
except ImportError:
    # Default fallback if config import fails
    API_KEYS = [
        os.environ.get("GOOGLE_API_KEY1", ""),
        os.environ.get("GOOGLE_API_KEY2", ""),
        os.environ.get("GOOGLE_API_KEY3", ""),
    ]
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    
# Filter out empty keys
API_KEYS = [key for key in API_KEYS if key]

# Runtime configuration
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0

# Model mappings for different providers
MODEL_MAPPINGS = {
    "gemini-1.5-pro": {
        "openai": "gpt-4o",  # Map to equivalent OpenAI model
        "anthropic": "claude-3-5-sonnet-20241022"  # Map to equivalent Anthropic model
    },
    "gemini-1.5-flash": {
        "openai": "gpt-3.5-turbo",
        "anthropic": "claude-3-haiku-20240307"
    },
    "gemini-1.0-pro": {
        "openai": "gpt-4-turbo",
        "anthropic": "claude-3-opus-20240229"
    }
}

class MultiProviderProxy:
    """Proxy that automatically falls back to alternative providers when rate limited"""
    
    def __init__(self):
        """Initialize the proxy with multiple provider support"""
        # Gemini specific configuration
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
        self.requests_per_minute = 10    # Target requests per minute
        self.request_window = 60.0       # Window size in seconds
        self.request_timestamps = []     # Store timestamps of recent requests
        
        # Provider fallback settings
        self.gemini_consecutive_failures = 0
        self.max_gemini_failures = 5     # After this many failures, try alternate providers
        self.provider_priority = ["gemini", "openai", "anthropic"]
        self.provider_availability = {
            "gemini": True,
            "openai": OPENAI_API_KEY != "",
            "anthropic": ANTHROPIC_API_KEY != ""
        }
        
        # Browser fingerprinting
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        ]
        
        # Log initialization status
        if not API_KEYS:
            logger.warning("No Gemini API keys available")
        else:
            logger.info(f"Multi-provider proxy initialized with {len(self.api_keys)} Gemini API keys")
            
        logger.info(f"OpenAI integration: {'Available' if self.provider_availability['openai'] else 'Not available'}")
        logger.info(f"Anthropic integration: {'Available' if self.provider_availability['anthropic'] else 'Not available'}")
        
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
            
            # Increment consecutive failure counter
            self.gemini_consecutive_failures += 1
            logger.info(f"Gemini consecutive failures: {self.gemini_consecutive_failures}")
            
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
        """Get highly randomized browser-like request headers to avoid fingerprinting"""
        # Select random user agent
        user_agent = random.choice(self.user_agents)
        
        # Select random language
        accept_languages = [
            "en-US,en;q=0.9",
            "en-GB,en;q=0.9",
            "en-CA,en;q=0.9,fr-CA;q=0.8",
            "en-AU,en;q=0.9",
            "fr-FR,fr;q=0.9,en-US;q=0.8",
            "de-DE,de;q=0.9,en-US;q=0.8",
            "es-ES,es;q=0.9,en-US;q=0.8",
            "it-IT,it;q=0.9,en-US;q=0.8",
            "ja-JP,ja;q=0.9,en-US;q=0.8",
        ]
        accept_language = random.choice(accept_languages)
        
        # Common referrers that might mask API traffic
        referrers = [
            "https://ai.google.dev/",
            "https://developers.google.com/",
            "https://developers.generativeai.google/",
            "https://colab.research.google.com/",
            "https://jupyter.org/try",
            "https://huggingface.co/spaces",
            "https://console.cloud.google.com/",
            "https://kaggle.com/code",
            "https://vercel.com/dashboard",
            "https://streamlit.io/",
        ]
        
        # Generate plausible cache-control setting
        cache_control_options = [
            "no-cache",
            "max-age=0",
            "no-store, max-age=0",
            "no-cache, no-store, must-revalidate",
        ]
        
        # Create a client timestamp with slight randomness
        timestamp = int(time.time() * 1000) + random.randint(-5000, 5000)
        
        # Randomize header order and inclusion based on common browser behavior
        headers = {
            "User-Agent": user_agent,
            "Accept": random.choice([
                "application/json",
                "application/json, text/plain, */*",
                "*/*",
            ]),
            "Accept-Language": accept_language,
            "Accept-Encoding": random.choice([
                "gzip, deflate, br",
                "gzip, deflate",
                "br, gzip",
            ]),
            "Content-Type": "application/json",
            "Origin": random.choice([
                "https://ai.google.dev",
                "https://developers.google.com",
                "https://explorer.apis.google.com",
            ]),
            "Referer": random.choice(referrers),
            "X-Client-Data": f"{random.randbytes(16).hex()}",
            "X-Requested-With": random.choice(["XMLHttpRequest", "fetch"]),
            "X-Client-Timestamp": str(timestamp),
            "Cache-Control": random.choice(cache_control_options),
            "Pragma": random.choice(["no-cache", ""]),
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": random.choice(["cross-site", "same-origin", "same-site"]),
            "Connection": random.choice(["keep-alive", "close"]),
            "DNT": random.choice(["1", "0"]),
        }
        
        # Randomly remove some headers to create variation
        headers_to_remove = random.sample(list(headers.keys()), random.randint(0, 3))
        for header in headers_to_remove:
            if header not in ["User-Agent", "Content-Type", "Accept"]:  # Keep essential headers
                headers.pop(header, None)
                
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

    def _call_openai(self, prompt: str, model: str = "gpt-4o") -> Dict[str, Any]:
        """Call OpenAI API with the given prompt"""
        if not OPENAI_API_KEY:
            return {
                "text": "Error: OpenAI API key not available",
                "model_used": model,
                "status": "error"
            }
            
        logger.info(f"Falling back to OpenAI API with model {model}")
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        # Format the request data for OpenAI's API
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        
        try:
            response = requests.post(
                url=url,
                json=data,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    text = result["choices"][0]["message"]["content"]
                    return {
                        "text": text,
                        "model_used": model,
                        "provider": "openai",
                        "status": "success"
                    }
                except (KeyError, IndexError) as e:
                    return {
                        "text": f"Error parsing OpenAI response: {str(e)}",
                        "model_used": model,
                        "provider": "openai",
                        "status": "error"
                    }
            else:
                error_msg = "Unknown error"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"].get("message", str(error_data["error"]))
                except:
                    error_msg = f"API Error: Status code {response.status_code}"
                
                return {
                    "text": f"Error from OpenAI API: {error_msg}",
                    "model_used": model,
                    "provider": "openai",
                    "status": "error"
                }
                
        except Exception as e:
            return {
                "text": f"Error calling OpenAI API: {str(e)}",
                "model_used": model,
                "provider": "openai",
                "status": "error"
            }

    def _call_anthropic(self, prompt: str, model: str = "claude-3-5-sonnet-20241022") -> Dict[str, Any]:
        """Call Anthropic API with the given prompt"""
        if not ANTHROPIC_API_KEY:
            return {
                "text": "Error: Anthropic API key not available",
                "model_used": model,
                "status": "error"
            }
            
        logger.info(f"Falling back to Anthropic API with model {model}")
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        # Format the request data for Anthropic's API
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4096,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                url=url,
                json=data,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    text = result["content"][0]["text"]
                    return {
                        "text": text,
                        "model_used": model,
                        "provider": "anthropic",
                        "status": "success"
                    }
                except (KeyError, IndexError) as e:
                    return {
                        "text": f"Error parsing Anthropic response: {str(e)}",
                        "model_used": model,
                        "provider": "anthropic",
                        "status": "error"
                    }
            else:
                error_msg = "Unknown error"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                except:
                    error_msg = f"API Error: Status code {response.status_code}"
                
                return {
                    "text": f"Error from Anthropic API: {error_msg}",
                    "model_used": model,
                    "provider": "anthropic",
                    "status": "error"
                }
                
        except Exception as e:
            return {
                "text": f"Error calling Anthropic API: {str(e)}",
                "model_used": model,
                "provider": "anthropic",
                "status": "error"
            }
            
    def _call_gemini(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call Gemini API with the given prompt"""
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
                    "provider": "gemini",
                    "status": "error"
                }
                
            # Randomize API endpoint version to distribute load across different API versions
            # Google often has multiple API versions active simultaneously with separate rate limits
            api_versions = [
                "v1",                # Current stable version
                "v1beta",            # Beta version
                "v1beta1",           # Alternate beta
                "v1beta2",           # Another possible beta
                "v1beta/models",     # Different path structure
                "v1/models",         # Different path structure
            ]
            
            # 90% chance to use v1, 10% chance to use alternates
            version = random.choices(
                api_versions, 
                weights=[0.9, 0.02, 0.02, 0.02, 0.02, 0.02], 
                k=1
            )[0]
            
            # Use one of several possible endpoint formats
            endpoint_formats = [
                f"https://generativelanguage.googleapis.com/{version}/{model.replace('models/', '')}:generateContent",
                f"https://generativelanguage.googleapis.com/{version}/{model}:generateContent",
                f"https://generativelanguage.googleapis.com/{version.split('/')[0]}/models/{model.replace('models/', '')}:generateContent",
            ]
            
            # Choose an endpoint format with weights
            url = random.choices(
                endpoint_formats,
                weights=[0.1, 0.8, 0.1],  # Prefer the standard format but occasionally try alternatives
                k=1
            )[0]
            
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
                    
                    # Check if we've hit too many rate limits
                    if self.gemini_consecutive_failures >= self.max_gemini_failures:
                        logger.warning(f"Too many consecutive Gemini failures ({self.gemini_consecutive_failures}), will try alternate providers")
                        return {
                            "text": "Error: Gemini API rate limited, falling back to alternates",
                            "model_used": model,
                            "provider": "gemini",
                            "status": "rate_limited"
                        }
                    
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
                            "provider": "gemini",
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
                            
                            # Reset consecutive failure counter on success
                            self.gemini_consecutive_failures = 0
                            
                            logger.info(f"Successfully generated content with {model}")
                            return {
                                "text": text,
                                "model_used": model,
                                "provider": "gemini",
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
                
                # Increment failure counter
                self.gemini_consecutive_failures += 1
                
                return {
                    "text": f"Error: {error_msg}",
                    "model_used": model,
                    "provider": "gemini",
                    "status": "error"
                }
                
            except Exception as e:
                logger.error(f"Request failed: {str(e)}")
                self.gemini_consecutive_failures += 1
                
                if attempt < MAX_RETRIES - 1:
                    backoff = BACKOFF_FACTOR ** attempt * (1 + random.uniform(0, 0.1))
                    logger.info(f"Waiting {backoff:.2f}s before retry")
                    time.sleep(backoff)
                    continue
        
        # If we reach here, all attempts failed
        return {
            "text": "Error: All API requests failed after multiple attempts",
            "model_used": model,
            "provider": "gemini",
            "status": "error"
        }
    
    def generate_content(self, prompt: str, model: str = "gemini-1.5-pro") -> Dict[str, Any]:
        """
        Generate content using a multi-provider approach with fallbacks
        
        Args:
            prompt: The text prompt
            model: Primary model name (Gemini model)
            
        Returns:
            Response dictionary with text, model_used, provider and status
        """
        # Try providers in order based on availability and priority
        available_providers = [p for p in self.provider_priority if self.provider_availability[p]]
        
        # If Gemini has failed too many times recently, adjust the provider priority
        if self.gemini_consecutive_failures >= self.max_gemini_failures and "gemini" in available_providers:
            # Move Gemini to the end of the priority list
            available_providers.remove("gemini")
            available_providers.append("gemini")
            logger.info("Adjusted provider priority due to Gemini failures")
        
        # Try each provider in priority order
        for provider in available_providers:
            # Skip provider if not available
            if not self.provider_availability[provider]:
                continue
                
            if provider == "gemini":
                result = self._call_gemini(prompt, model)
                
                # If successful or a definitive error (not rate limiting), return the result
                if result["status"] in ["success", "error"] and "rate limit" not in result["text"].lower():
                    return result
                    
                # If rate limited, continue to next provider
                logger.warning("Gemini API rate limited, trying next provider")
                
            elif provider == "openai":
                # Map Gemini model to equivalent OpenAI model
                model_base = model.replace("models/", "")
                openai_model = MODEL_MAPPINGS.get(model_base, {}).get("openai", "gpt-4o")
                
                # Call OpenAI API
                result = self._call_openai(prompt, openai_model)
                if result["status"] == "success":
                    return result
                    
                # Log error and continue to next provider
                logger.warning(f"OpenAI API failed: {result['text']}")
                
            elif provider == "anthropic":
                # Map Gemini model to equivalent Anthropic model
                model_base = model.replace("models/", "")
                anthropic_model = MODEL_MAPPINGS.get(model_base, {}).get("anthropic", "claude-3-5-sonnet-20241022")
                
                # Call Anthropic API
                result = self._call_anthropic(prompt, anthropic_model)
                if result["status"] == "success":
                    return result
                    
                # Log error and continue to next provider
                logger.warning(f"Anthropic API failed: {result['text']}")
        
        # If we've tried all providers and none worked, return the last error
        logger.error("All providers failed")
        return {
            "text": "Error: All AI providers failed to generate content",
            "model_used": model,
            "provider": "none",
            "status": "error"
        }

# Create singleton instance
_proxy = None

def get_proxy():
    """Get the singleton proxy instance"""
    global _proxy
    if _proxy is None:
        _proxy = MultiProviderProxy()
    return _proxy

def generate_content(prompt: str, model: str = "gemini-1.5-pro", 
                    temperature: float = 0.7, max_output_tokens: int = 4096) -> Dict[str, Any]:
    """
    Generate content using the multi-provider proxy
    
    Args:
        prompt: The text prompt
        model: Model name
        temperature: Not directly used (optimized inside proxy)
        max_output_tokens: Not directly used (optimized inside proxy)
        
    Returns:
        Response with text, model_used, provider and status
    """
    proxy = get_proxy()
    return proxy.generate_content(prompt, model)

def test_proxy():
    """Test the multi-provider proxy"""
    print("Testing multi-provider proxy...")
    
    # Try a simple request first
    print("\nTest 1: Basic request")
    result = generate_content("Write a haiku about programming.")
    print(f"Status: {result['status']}")
    print(f"Provider: {result.get('provider', 'unknown')}")
    print(f"Model: {result['model_used']}")
    print(f"Text: {result['text'][:100]}..." if len(result.get('text', '')) > 100 else f"Text: {result.get('text', '')}")
    
    if result['status'] == 'success':
        # If successful, try a second request to test rate limiting
        print("\nTest 2: Follow-up request to test rate limiting")
        time.sleep(3)  # Short delay
        result2 = generate_content("Explain quantum computing in one sentence.")
        print(f"Status: {result2['status']}")
        print(f"Provider: {result2.get('provider', 'unknown')}")
        print(f"Model: {result2['model_used']}")
        print(f"Text: {result2['text'][:100]}..." if len(result2.get('text', '')) > 100 else f"Text: {result2.get('text', '')}")
    
    # Print statistics
    proxy = get_proxy()
    print(f"\nStatistics:")
    print(f"- API Keys total: {len(proxy.api_keys)}")
    print(f"- Rate limited keys: {len(proxy.rate_limited_keys)}")
    print(f"- Successful keys: {len(proxy.successful_keys)}")
    print(f"- Success count: {proxy.success_count}")
    print(f"- Available providers: {[p for p in proxy.provider_priority if proxy.provider_availability[p]]}")
    
if __name__ == "__main__":
    test_proxy()