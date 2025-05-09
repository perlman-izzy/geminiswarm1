#!/usr/bin/env python3
"""
Test script to verify Gemini API functionality
"""
import requests
import sys
import json
import time
from typing import Dict, Any
import os

def test_gemini_api(url: str = "http://localhost:5000/gemini") -> bool:
    """
    Test the Gemini API with a simple prompt
    
    Args:
        url: URL of the Gemini proxy endpoint
        
    Returns:
        True if the test was successful, False otherwise
    """
    # Simple test prompt
    test_prompt = "Write a concise one-sentence joke about programming."
    
    print(f"Testing Gemini API at {url}")
    print(f"Sending prompt: '{test_prompt}'")
    
    try:
        # Make the API request
        response = requests.post(
            url,
            json={"prompt": test_prompt},
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        # Check if the request was successful
        response.raise_for_status()
        result = response.json()
        
        if result.get("status") == "error":
            print(f"API Error: {result.get('error')}")
            return False
        
        # Print the response
        print("\nAPI Response:")
        print(f"{result.get('response', '')}")
        print(f"\nModel used: {result.get('model', 'unknown')}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {str(e)}")
        return False
    
    except json.JSONDecodeError:
        print("Invalid JSON response from API")
        return False
    
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        return False

def test_swarm_with_buggy_code():
    """
    Test the swarm.py with the buggy_code.py file
    """
    import subprocess
    
    print("\nTesting swarm.py with buggy_code.py...")
    
    try:
        # Run the swarm command
        cmd = ["python", "swarm.py", "fix", "buggy_code.py", "--test-cmd", "python test_buggy_code.py"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Display output
        print("\nSwarm Command Output:")
        print(result.stdout)
        
        if result.stderr:
            print("\nErrors:")
            print(result.stderr)
        
        # Check if the command was successful
        if result.returncode == 0:
            print("\nSwarm debugger fixed the code successfully!")
            return True
        else:
            print(f"\nSwarm debugger failed with exit code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"Error running swarm: {str(e)}")
        return False

if __name__ == "__main__":
    # Test the Gemini API
    api_success = test_gemini_api()
    
    if api_success:
        print("\n✅ Gemini API test successful!")
        
        # Uncomment to test swarm with buggy code
        # Note: This will modify the buggy_code.py file
        # swarm_success = test_swarm_with_buggy_code()
    else:
        print("\n❌ Gemini API test failed!")
        sys.exit(1)