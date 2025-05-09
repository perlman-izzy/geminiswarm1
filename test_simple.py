#!/usr/bin/env python3
"""
Simple test script for the Gemini swarm system
"""
import sys
import json
import requests

def test_simple_prompt(prompt="What's the weather like today?", 
                       url="http://localhost:5000/gemini"):
    """Test a simple prompt to the Gemini API."""
    print(f"Testing prompt: '{prompt}'")
    try:
        response = requests.post(
            url,
            json={"prompt": prompt},
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        
        print("\nResponse:")
        print(result.get("response", "No response"))
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    """Run a simple test."""
    prompt = "What's the weather like today?"
    if len(sys.argv) > 1:
        prompt = sys.argv[1]
    
    success = test_simple_prompt(prompt)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())