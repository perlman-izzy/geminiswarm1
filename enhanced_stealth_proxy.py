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
        """
        Get the next available API key with sophisticated selection strategy
        Implements a time-based distribution approach for key usage
        """
        now = time.time()
        available_keys = [k for k in self.api_keys if k not in self.rate_limited_keys]
        
        # Clean up old usage timestamps
        for key in self.api_keys:
            self.key_usage_times[key] = [t for t in self.key_usage_times.get(key, []) 
                                        if now - t <= self.request_window]
        
        # Filter out keys that have been used too frequently in the window
        lightly_used_keys = [k for k in available_keys 
                            if len(self.key_usage_times.get(k, [])) < self.requests_per_key]
        
        # If all keys are rate limited or heavily used, implement fallback strategy
        if not lightly_used_keys:
            # If we have any available keys, find the least recently used one
            if available_keys:
                logger.warning(f"All keys used frequently, selecting least recently used key")
                # Sort by most recent usage time
                last_used_times = {}
                for key in available_keys:
                    times = self.key_usage_times.get(key, [])
                    last_used_times[key] = max(times) if times else 0
                
                # Pick the key that was used longest ago
                selected_key = min(last_used_times.items(), key=lambda x: x[1])[0]
                logger.info(f"Selected least recently used key (last used {now - last_used_times[selected_key]:.1f}s ago)")
            # If all keys are rate limited but we have successful keys, try one
            elif self.successful_keys:
                successful_not_limited = [k for k in self.successful_keys if k not in self.rate_limited_keys]
                if successful_not_limited:
                    selected_key = random.choice(successful_not_limited)
                    logger.warning(f"Using previously successful key as fallback")
                else:
                    # If all successful keys are rate limited, try any non-rate limited key
                    non_limited = [k for k in self.api_keys if k not in self.rate_limited_keys]
                    if non_limited:
                        selected_key = random.choice(non_limited)
                        logger.warning(f"Using random non-rate-limited key as last resort")
                    else:
                        # Absolute last resort - use any key
                        selected_key = random.choice(self.api_keys) if self.api_keys else ""
                        logger.warning(f"All keys are rate limited, using any key as emergency fallback")
            else:
                # Absolutely no keys available - emergency fallback
                selected_key = random.choice(self.api_keys) if self.api_keys else ""
                logger.warning(f"All keys are rate limited, using any key as emergency fallback")
        else:
            # Normal case: we have lightly used keys available
            
            # Prioritize successful keys that haven't been used much
            successful_lightly_used = [k for k in lightly_used_keys if k in self.successful_keys]
            
            if successful_lightly_used and random.random() < 0.7:  # 70% chance to use successful key
                # Find the least recently used successful key
                key_last_used = {}
                for key in successful_lightly_used:
                    times = self.key_usage_times.get(key, [])
                    key_last_used[key] = max(times) if times else 0
                
                # Sort by last used time (oldest first)
                usage_sorted = sorted(key_last_used.items(), key=lambda x: x[1])
                selected_key = usage_sorted[0][0] if usage_sorted else random.choice(successful_lightly_used)
                logger.debug(f"Selected successful & lightly used key")
            else:
                # Otherwise use any lightly used key - preferring ones used longer ago
                key_last_used = {}
                for key in lightly_used_keys:
                    times = self.key_usage_times.get(key, [])
                    key_last_used[key] = max(times) if times else 0
                
                # Sort by last used time (oldest first)
                usage_sorted = sorted(key_last_used.items(), key=lambda x: x[1])
                selected_key = usage_sorted[0][0] if usage_sorted else random.choice(lightly_used_keys)
                logger.debug(f"Selected lightly used key")
        
        # Update usage stats for this key
        self.key_usage_count[selected_key] = self.key_usage_count.get(selected_key, 0) + 1
        self.key_usage_times.setdefault(selected_key, []).append(now)
        
        # Add some logging to show key distribution
        if random.random() < 0.2:  # Only log occasionally to avoid spam
            usage_counts = {k: len(times) for k, times in self.key_usage_times.items() if times}
            top_used = sorted(usage_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            logger.info(f"Key usage distribution (top 3): {top_used}")
        
        return selected_key
    
    def _enforce_rate_limit(self) -> float:
        """
        Enforce self-imposed rate limits to stay below API provider limits
        Implements Claude's suggestion for time-based distribution of requests
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
        
        # Calculate current request rate (requests per minute)
        current_requests = len(self.request_timestamps)
        window_size_minutes = self.request_window / 60.0
        current_rate = current_requests / window_size_minutes if window_size_minutes > 0 else current_requests
        
        # Add randomness to rate limits (+-20%) to avoid detection patterns
        adjusted_limit = self.requests_per_minute * (0.8 + (random.random() * 0.4))  # 80-120% of limit
        
        # If we're already exceeding even our adjusted rate limit
        if current_rate >= adjusted_limit:
            # Apply backoff: exponential based on how much we're over the limit
            ratio = current_rate / adjusted_limit
            backoff_factor = max(1.0, min(3.0, ratio))  # Cap between 1.0 and 3.0
            
            # Base delay calculation
            if self.request_timestamps:
                # Calculate how long until we're back under limit
                newest_timestamp = max(self.request_timestamps)
                oldest_timestamp = min(self.request_timestamps)
                
                # Theoretical time when we'd be under limit if we waited for oldest to expire
                time_to_expire = (oldest_timestamp + self.request_window) - now
                
                # Scale by backoff factor and add jitter
                sleep_time = time_to_expire * backoff_factor
                jitter = sleep_time * random.uniform(0, 0.2)  # 0-20% jitter
                sleep_time += jitter
                
                # Ensure minimum sleep time and cap maximum
                sleep_time = max(self.min_request_interval, min(sleep_time, 30.0))
                
                logger.info(f"Rate limiting: {current_requests} requests at {current_rate:.1f}/min. Sleeping {sleep_time:.2f}s")
                return sleep_time
        
        # Even if we're under rate limit, enforce a minimum delay between requests
        # with randomization to prevent detection patterns
        min_delay = self.min_request_interval * (0.8 + (random.random() * 0.4))  # 80-120% of minimum
        logger.debug(f"Enforcing minimum delay of {min_delay:.2f}s between requests")
        return min_delay
        
    def mark_rate_limited(self, key: str) -> None:
        """
        Mark a key as rate limited and implement advanced backoff strategy
        Implements Claude's suggestion for adaptive backoff based on rate limits
        """
        if key and key not in self.rate_limited_keys:
            self.rate_limited_keys.add(key)
            logger.warning(f"API key marked as rate limited")
            logger.info(f"Currently {len(self.rate_limited_keys)}/{len(self.api_keys)} keys are rate limited")
            
            # Calculate the ratio of rate-limited keys for adaptive backoff
            rate_limited_ratio = len(self.rate_limited_keys) / len(self.api_keys)
            
            # Progressive global backoff based on how many keys are rate limited
            # More aggressive as more keys become rate limited
            if rate_limited_ratio < 0.1:  # Less than 10% of keys rate limited
                # Minor backoff - just for this key
                backoff_time = 0  # No global backoff
                logger.info(f"Only {rate_limited_ratio:.1%} of keys rate limited - no global backoff")
            elif rate_limited_ratio < 0.25:  # 10-25% of keys rate limited
                # Moderate backoff - short global pause
                backoff_time = 60 + (random.random() * 30)  # 60-90 seconds
                self.global_backoff_until = time.time() + backoff_time
                logger.warning(f"Moderate rate limiting ({rate_limited_ratio:.1%} of keys) - global backoff for {backoff_time:.1f}s")
            elif rate_limited_ratio < 0.5:  # 25-50% of keys rate limited
                # Significant backoff - longer pause
                backoff_time = 180 + (random.random() * 120)  # 3-5 minutes
                self.global_backoff_until = time.time() + backoff_time
                logger.warning(f"Significant rate limiting ({rate_limited_ratio:.1%} of keys) - global backoff for {backoff_time:.1f}s")
            else:  # More than 50% of keys rate limited
                # Severe backoff - very long pause
                backoff_time = 600 + (random.random() * 300)  # 10-15 minutes
                self.global_backoff_until = time.time() + backoff_time
                logger.warning(f"Severe rate limiting ({rate_limited_ratio:.1%} of keys) - global backoff for {backoff_time:.1f}s")
            
            # Also reduce per-minute request limit when many keys are rate limited
            new_limit = max(1, int(self.requests_per_minute * (1.0 - rate_limited_ratio)))
            if new_limit < self.requests_per_minute:
                logger.info(f"Reducing requests per minute from {self.requests_per_minute} to {new_limit} due to rate limiting")
                self.requests_per_minute = new_limit
            
            # Auto-clear rate limited keys after a variable time based on severity
            def clear_rate_limited_key():
                # More keys rate limited = longer timeout before retry
                clear_delay = 180 + (rate_limited_ratio * 420)  # 3-10 minutes based on severity
                time.sleep(clear_delay)
                
                if key in self.rate_limited_keys:
                    self.rate_limited_keys.remove(key)
                    logger.info(f"Cleared rate limit for a key after {clear_delay:.1f}s, now {len(self.rate_limited_keys)}/{len(self.api_keys)} keys are rate limited")
            
            # Start a thread to clear the rate limit after the adaptive delay
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
        Create highly varied request payloads to smuggle requests past rate limiting
        Implements Claude's suggestions for request parameter variations and smuggling
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
        
        # REQUEST SMUGGLING TECHNIQUE 1: Message format variations
        # Vary how the prompt is structured to avoid pattern detection
        message_format_type = random.randint(1, 4)
        
        if message_format_type == 1:
            # Standard format
            contents = [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ],
                    "role": "user"
                }
            ]
        elif message_format_type == 2:
            # Format with system message
            contents = [
                {
                    "parts": [
                        {
                            "text": "You are a helpful assistant."
                        }
                    ],
                    "role": "system"
                },
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ],
                    "role": "user"
                }
            ]
        elif message_format_type == 3:
            # Format with chat history context
            contents = [
                {
                    "parts": [
                        {
                            "text": "Hello, I have a question."
                        }
                    ],
                    "role": "user"
                },
                {
                    "parts": [
                        {
                            "text": "I'd be happy to help with your question. What would you like to know?"
                        }
                    ],
                    "role": "model"
                },
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ],
                    "role": "user"
                }
            ]
        else:
            # Format with multimedia-like structure (even though it's just text)
            contents = [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ],
                    "role": "user"
                }
            ]
            
        # REQUEST SMUGGLING TECHNIQUE 2: Parameter naming variations
        # Sometimes use alternative parameter names that the API might still recognize
        generation_config = {}
        
        # Temperature parameter - vary parameter name
        temp_param = random.choices(
            ["temperature", "Temperature", "temp"],
            weights=[0.8, 0.1, 0.1],
            k=1
        )[0]
        generation_config[temp_param] = temperature
        
        # Max tokens parameter - vary parameter name
        max_tokens_param = random.choices(
            ["maxOutputTokens", "max_output_tokens", "max_tokens"],
            weights=[0.8, 0.1, 0.1],
            k=1
        )[0]
        generation_config[max_tokens_param] = max_tokens
        
        # Top-p parameter - vary parameter name
        top_p_param = random.choices(
            ["topP", "top_p"],
            weights=[0.9, 0.1],
            k=1
        )[0]
        generation_config[top_p_param] = top_p
        
        # Top-k parameter - vary parameter name
        top_k_param = random.choices(
            ["topK", "top_k"],
            weights=[0.9, 0.1],
            k=1
        )[0]
        generation_config[top_k_param] = top_k
        
        # REQUEST SMUGGLING TECHNIQUE 3: Structure variations
        # Base request payload with variations in structure
        request_data = {
            "contents": contents,
            "generationConfig": generation_config
        }
        
        # Sometimes use safetySettings at root level, sometimes inside generationConfig
        if random.random() < 0.8:
            request_data["safetySettings"] = safety_settings
        else:
            request_data["generationConfig"]["safetySettings"] = safety_settings
        
        # Optional parameters with varied naming conventions
        optional_params = {
            "stopSequences": ["\n\n", "###"],
            "stop_sequences": ["\n\n", "###"],
            "candidateCount": 1,
            "candidate_count": 1,
            "logprobs": random.choice([1, 5]),
            "log_probs": random.choice([1, 5]),
            "presencePenalty": random.uniform(0, 0.5),
            "presence_penalty": random.uniform(0, 0.5),
            "frequencyPenalty": random.uniform(0, 0.5),
            "frequency_penalty": random.uniform(0, 0.5),
        }
        
        # Add 1-3 optional parameters randomly
        for _ in range(random.randint(1, 3)):
            param = random.choice(list(optional_params.keys()))
            value = optional_params[param]
            if random.random() < 0.7:
                request_data["generationConfig"][param] = value
            else:
                request_data[param] = value
        
        # REQUEST SMUGGLING TECHNIQUE 4: Add irrelevant but harmless parameters
        # Add benign extra parameters that shouldn't affect operation but change the request signature
        if random.random() < 0.3:
            extra_params = {
                "client_info": {
                    "client_id": f"replit-app-{random.randint(1000, 9999)}",
                    "session_id": str(uuid.uuid4())[:8],
                    "user_agent": f"python-client/{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
                },
                "api_version": f"{random.randint(1, 3)}.{random.randint(0, 9)}",
                "request_source": random.choice(["web", "api", "sdk", "cli"]),
                "request_id": str(uuid.uuid4()),
                "timestamp": int(time.time() * 1000)
            }
            
            # Add 1-2 extra parameters
            for _ in range(random.randint(1, 2)):
                param = random.choice(list(extra_params.keys()))
                request_data[param] = extra_params[param]
        
        # Return the highly randomized payload
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