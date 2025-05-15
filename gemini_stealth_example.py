#!/usr/bin/env python3
"""
Example demonstration of the Gemini stealth proxy vs. standard API
Shows how to integrate the stealth proxy into existing code
"""

import os
import logging
import time
import json
import requests
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gemini_example")

# Import our stealth client
try:
    from gemini_stealth_client import generate_content as stealth_generate
    HAS_STEALTH_PROXY = True
except ImportError:
    HAS_STEALTH_PROXY = False
    logger.warning("Stealth proxy not available, will use standard API only")

def call_regular_gemini_api(prompt: str, model: str = "gemini-1.5-pro") -> Dict[str, Any]:
    """
    Call the Gemini API through our standard REST proxy
    
    Args:
        prompt: Text prompt
        model: Model name
        
    Returns:
        Response dictionary
    """
    logger.info(f"Using standard API with model {model}")
    start_time = time.time()
    
    try:
        # Standard REST API
        url = "http://localhost:5000/gemini"
        response = requests.post(
            url,
            json={
                "prompt": prompt,
                "model": f"models/{model}",
                "priority": "high"
            },
            headers={"Content-Type": "application/json"}
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Standard API response received in {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            return {
                "response": result.get("response", ""),
                "model_used": model,
                "elapsed_time": elapsed,
                "status": "success"
            }
        else:
            return {
                "response": f"Error: API returned status {response.status_code}",
                "model_used": model,
                "elapsed_time": elapsed,
                "status": "error"
            }
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error calling standard API: {e}")
        return {
            "response": f"Error: {str(e)}",
            "model_used": model,
            "elapsed_time": elapsed,
            "status": "error"
        }

def call_stealth_gemini_api(prompt: str, model: str = "gemini-1.5-pro") -> Dict[str, Any]:
    """
    Call the Gemini API through our stealth proxy
    
    Args:
        prompt: Text prompt
        model: Model name
        
    Returns:
        Response dictionary
    """
    if not HAS_STEALTH_PROXY:
        return {
            "response": "Stealth proxy not available",
            "model_used": "none",
            "elapsed_time": 0,
            "status": "error"
        }
        
    logger.info(f"Using stealth proxy with model {model}")
    start_time = time.time()
    
    try:
        # Use our stealth client
        result = stealth_generate(
            prompt=prompt,
            model=model,
            temperature=0.7,
            max_output_tokens=4096
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Stealth proxy response received in {elapsed:.2f} seconds")
        
        if result.get("status") == "success":
            return {
                "response": result.get("text", ""),
                "model_used": f"{model} (stealth)",
                "elapsed_time": elapsed,
                "status": "success"
            }
        else:
            return {
                "response": f"Error: {result.get('text', 'Unknown error')}",
                "model_used": f"{model} (stealth)",
                "elapsed_time": elapsed,
                "status": "error"
            }
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error calling stealth API: {e}")
        return {
            "response": f"Error: {str(e)}",
            "model_used": f"{model} (stealth)",
            "elapsed_time": elapsed,
            "status": "error"
        }

def compare_api_calls():
    """Compare responses from both API methods"""
    prompt = "Explain how quantum computing differs from classical computing in three sentences."
    
    print("\n==== COMPARING API CALLS ====")
    print(f"Prompt: {prompt}\n")
    
    # Call both APIs
    stealth_result = call_stealth_gemini_api(prompt)
    regular_result = call_regular_gemini_api(prompt)
    
    # Display results
    print("\n==== STEALTH PROXY RESULT ====")
    print(f"Status: {stealth_result['status']}")
    print(f"Model: {stealth_result['model_used']}")
    print(f"Time: {stealth_result['elapsed_time']:.2f} seconds")
    print(f"Response: {stealth_result['response']}")
    
    print("\n==== STANDARD API RESULT ====")
    print(f"Status: {regular_result['status']}")
    print(f"Model: {regular_result['model_used']}")
    print(f"Time: {regular_result['elapsed_time']:.2f} seconds")
    print(f"Response: {regular_result['response']}")
    
def test_stealth_api_rate_limits():
    """Test stealth API with multiple sequential requests to check rate limiting"""
    prompt = "Give me a one sentence response to test rate limiting."
    
    print("\n==== TESTING RATE LIMIT HANDLING ====")
    print("Making 5 sequential requests to test rate limit handling...\n")
    
    for i in range(5):
        print(f"\nRequest #{i+1}")
        start_time = time.time()
        result = call_stealth_gemini_api(prompt)
        elapsed = time.time() - start_time
        
        print(f"Status: {result['status']}")
        print(f"Model: {result['model_used']}")
        print(f"Time: {elapsed:.2f} seconds")
        print(f"Response: {result['response']}")
        
        # Small delay to make output readable
        if i < 4:
            time.sleep(1)

def main():
    """Run example demonstrations"""
    print("\n====== GEMINI STEALTH PROXY EXAMPLE ======")
    
    # Compare API call methods
    compare_api_calls()
    
    # Test sequential calls to check rate limiting
    if HAS_STEALTH_PROXY:
        test_stealth_api_rate_limits()
    else:
        print("\nStealth proxy not available, skipping rate limit test.")
    
    print("\n====== EXAMPLE COMPLETE ======")

if __name__ == "__main__":
    main()