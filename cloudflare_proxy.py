#!/usr/bin/env python3
"""
Implementation of a Cloudflare Workers proxy for the Gemini API
This helps bypass rate limits by distributing requests across multiple IPs
"""

import os
import requests
import json
import time
import logging
import random
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("cloudflare_proxy")

# Cloudflare proxy settings - would be provided by user for production
CLOUDFLARE_WORKER_URL = "https://your-cloudflare-worker.username.workers.dev/proxy"

# This is the expected worker script code that would be deployed to Cloudflare
WORKER_SCRIPT = """
// Cloudflare Worker script for Gemini API proxy
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  // Only allow POST requests
  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }
  
  try {
    // Parse the incoming request
    const data = await request.json();
    const { apiKey, model, payload } = data;
    
    if (!apiKey || !model || !payload) {
      return new Response('Missing required parameters', { status: 400 });
    }

    // Format URL correctly
    const url = `https://generativelanguage.googleapis.com/v1/${model}:generateContent`;
    
    // Forward to Gemini with the provided API key
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-goog-api-key': apiKey
      },
      body: JSON.stringify(payload)
    });
    
    // Get the response data
    const responseData = await response.json();
    
    // Return the response with additional metadata
    return new Response(JSON.stringify({
      status: response.status,
      statusText: response.statusText,
      data: responseData,
      worker_id: crypto.randomUUID().substring(0, 8),
      timestamp: Date.now()
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    return new Response(JSON.stringify({
      error: error.message,
      status: 500
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
"""

class CloudflareGeminiProxy:
    """
    Cloudflare Workers-based proxy for Gemini API
    Distributes requests across multiple worker instances to avoid rate limits
    """
    
    def __init__(self, 
                worker_url: Optional[str] = None, 
                api_keys: Optional[List[str]] = None,
                request_delay: float = 1.0):
        """
        Initialize the Cloudflare proxy
        
        Args:
            worker_url: URL of your deployed Cloudflare Worker
            api_keys: List of Gemini API keys to use
            request_delay: Minimum delay between requests in seconds
        """
        # Import API keys from config if not provided
        if not api_keys:
            try:
                from config import GEMINI_API_KEYS
                self.api_keys = GEMINI_API_KEYS
            except ImportError:
                self.api_keys = [
                    os.environ.get("GOOGLE_API_KEY1", ""),
                    os.environ.get("GOOGLE_API_KEY2", ""),
                    os.environ.get("GOOGLE_API_KEY3", ""),
                ]
                
            # Filter out empty keys
            self.api_keys = [key for key in self.api_keys if key]
        else:
            self.api_keys = api_keys
            
        # Set worker URL
        self.worker_url = worker_url or CLOUDFLARE_WORKER_URL
        
        # Request tracking
        self.last_request_time = 0
        self.request_delay = request_delay
        self.key_index = 0
        
        # Log initialization status
        logger.info(f"Cloudflare Gemini proxy initialized with {len(self.api_keys)} API keys")
        
        # Show help text if no Worker URL is provided
        if self.worker_url == CLOUDFLARE_WORKER_URL:
            logger.warning("Using placeholder Cloudflare Worker URL. For production use:")
            logger.warning("1. Deploy the Worker script to Cloudflare Workers")
            logger.warning("2. Update the CLOUDFLARE_WORKER_URL in this file or provide it when initializing")
            logger.warning(f"Example worker script:\n{WORKER_SCRIPT}")
    
    def get_next_key(self) -> str:
        """Get the next API key in rotation"""
        if not self.api_keys:
            return ""
            
        # Simple round-robin for now
        self.key_index = (self.key_index + 1) % len(self.api_keys)
        return self.api_keys[self.key_index]
    
    def generate_content(self, prompt: str, model: str = "gemini-1.5-pro") -> Dict[str, Any]:
        """
        Generate content using Gemini API through Cloudflare Workers
        
        Args:
            prompt: The text prompt
            model: Model name
            
        Returns:
            Response dictionary
        """
        # Ensure model has proper prefix
        if not model.startswith("models/"):
            model = f"models/{model}"
            
        # Enforce minimum delay between requests
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.request_delay:
            sleep_time = self.request_delay - elapsed
            logger.debug(f"Enforcing minimum delay: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
            
        # Update last request time
        self.last_request_time = time.time()
        
        # Get next API key
        api_key = self.get_next_key()
        if not api_key:
            return {
                "text": "Error: No API keys available",
                "model_used": model,
                "status": "error"
            }
            
        # Prepare request payload for Gemini API
        gemini_payload = {
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
        
        # Prepare data to send to Cloudflare Worker
        worker_payload = {
            "apiKey": api_key,
            "model": model,
            "payload": gemini_payload
        }
        
        try:
            # Make the request to the Cloudflare Worker
            logger.info(f"Sending request to Cloudflare Worker for {model}")
            response = requests.post(
                url=self.worker_url,
                json=worker_payload,
                timeout=30
            )
            
            # Handle response
            if response.status_code == 200:
                worker_response = response.json()
                
                # Check if the Worker got a successful response from Gemini
                if worker_response.get("status") == 200:
                    gemini_data = worker_response.get("data", {})
                    
                    # Extract text from Gemini response
                    if "candidates" in gemini_data and gemini_data["candidates"]:
                        candidate = gemini_data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            text = candidate["content"]["parts"][0].get("text", "")
                            
                            logger.info(f"Successfully generated content via Cloudflare Worker (worker_id: {worker_response.get('worker_id')})")
                            return {
                                "text": text,
                                "model_used": model,
                                "worker_id": worker_response.get("worker_id"),
                                "status": "success"
                            }
                
                # Handle errors in the Gemini API response
                error_msg = "Unknown error in Gemini API response"
                gemini_data = worker_response.get("data", {})
                if "error" in gemini_data:
                    error_data = gemini_data["error"]
                    if isinstance(error_data, dict) and "message" in error_data:
                        error_msg = error_data["message"]
                    else:
                        error_msg = str(error_data)
                        
                return {
                    "text": f"Error from Gemini API: {error_msg}",
                    "model_used": model,
                    "worker_id": worker_response.get("worker_id"),
                    "status": "error"
                }
            
            # Handle errors in the Worker response
            return {
                "text": f"Error from Cloudflare Worker: {response.status_code} - {response.text}",
                "model_used": model,
                "status": "error"
            }
                
        except Exception as e:
            logger.error(f"Request to Cloudflare Worker failed: {str(e)}")
            return {
                "text": f"Error: {str(e)}",
                "model_used": model,
                "status": "error"
            }

# Singleton instance
_proxy = None

def get_proxy(worker_url: Optional[str] = None) -> CloudflareGeminiProxy:
    """Get or create the proxy instance"""
    global _proxy
    if _proxy is None:
        _proxy = CloudflareGeminiProxy(worker_url=worker_url)
    return _proxy

def generate_content(prompt: str, model: str = "gemini-1.5-pro") -> Dict[str, Any]:
    """
    Generate content using Gemini via Cloudflare Workers
    
    Args:
        prompt: The text prompt
        model: Model name
        
    Returns:
        Response with text, model_used and status
    """
    proxy = get_proxy()
    return proxy.generate_content(prompt, model)

def print_worker_deployment_instructions():
    """Print instructions for deploying the Cloudflare Worker"""
    print("\n=== Cloudflare Worker Deployment Instructions ===")
    print("\n1. Sign up for Cloudflare Workers at https://workers.cloudflare.com/")
    print("2. Create a new Worker")
    print("3. Copy and paste the following code into your Worker:")
    print("\n```javascript")
    print(WORKER_SCRIPT)
    print("```")
    print("\n4. Deploy your Worker")
    print("5. Update the CLOUDFLARE_WORKER_URL in this file to your Worker's URL")
    print("   Example: https://your-worker-name.your-account.workers.dev/proxy")
    print("\nOnce deployed, your requests will be distributed across Cloudflare's global network,")
    print("helping to avoid IP-based rate limits from the Gemini API.")

def test_proxy():
    """Test the Cloudflare proxy if a Worker URL is provided"""
    if CLOUDFLARE_WORKER_URL != "https://your-cloudflare-worker.username.workers.dev/proxy":
        print("Testing Cloudflare Gemini proxy...")
        result = generate_content("Write a haiku about programming.")
        print(f"Status: {result['status']}")
        print(f"Model: {result['model_used']}")
        if "worker_id" in result:
            print(f"Worker ID: {result['worker_id']}")
        print(f"Text: {result['text']}")
    else:
        print_worker_deployment_instructions()

if __name__ == "__main__":
    test_proxy()