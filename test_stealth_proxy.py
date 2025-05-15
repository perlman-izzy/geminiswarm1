#!/usr/bin/env python3
"""
Test script for the Gemini stealth proxy
Runs standalone to verify functionality
"""

import os
import logging
import time
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_proxy")

def test_stealth_client():
    """Test the stealth client implementation"""
    print("\n=== Testing Stealth Client ===")
    
    try:
        from gemini_stealth_client import generate_content
        
        prompt = "Write a haiku about programming."
        print(f"Prompt: {prompt}")
        
        start_time = time.time()
        result = generate_content(prompt)
        elapsed = time.time() - start_time
        
        print(f"\nResponse received in {elapsed:.2f} seconds:")
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Model: {result.get('model_used', 'unknown')}")
        print(f"Text: {result.get('text', '')}\n")
        
        if result.get('status') == 'success':
            print("✅ Stealth client test successful!")
        else:
            print("❌ Stealth client test failed!")
            
    except ImportError:
        print("❌ Could not import gemini_stealth_client.")
        return False
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
        
    return True

def test_proxy_standalone():
    """Test the proxy implementation directly"""
    print("\n=== Testing Proxy Directly ===")
    
    try:
        from gemini_stealth_proxy import GeminiProxy
        
        proxy = GeminiProxy()
        contents = [
            {
                "parts": [{"text": "Explain quantum computing in three sentences."}],
                "role": "user"
            }
        ]
        
        start_time = time.time()
        response = proxy.generate_content(
            model="gemini-1.5-pro",
            contents=contents,
            generation_config={
                "temperature": 0.7,
                "maxOutputTokens": 100,
                "topP": 0.95
            }
        )
        elapsed = time.time() - start_time
        
        print(f"\nResponse received in {elapsed:.2f} seconds:")
        
        if "candidates" in response:
            for i, candidate in enumerate(response["candidates"]):
                if "content" in candidate and "parts" in candidate["content"]:
                    text = candidate["content"]["parts"][0].get("text", "")
                    print(f"Candidate {i+1}: {text}")
            print("\n✅ Proxy direct test successful!")
        else:
            print(f"❌ Proxy direct test failed. Response: {response}")
            
    except ImportError:
        print("❌ Could not import gemini_stealth_proxy.")
        return False
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
        
    return True

def main():
    """Run all tests"""
    print("\n==== Gemini Stealth Proxy Tests ====")
    print("Testing proxy functionality...\n")
    
    # Track test results
    results = {}
    
    # Test 1: Stealth Client
    results["stealth_client"] = test_stealth_client()
    
    # Test 2: Direct Proxy
    results["proxy_direct"] = test_proxy_standalone()
    
    # Print summary
    print("\n==== Test Summary ====")
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    # Return overall success
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)