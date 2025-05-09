#!/usr/bin/env python3
"""
Quick test for the system's basic functionality.
"""
import sys
import json

# Import the function directly
from main import call_gemini_with_model_selection

def test_basic_functionality():
    """Test basic functionality with a simple prompt."""
    print("Testing basic functionality...")
    
    prompt = """
    Based on the following resume excerpt, extract the most recent job information in JSON format:
    
    California Conservatory of Music, Redwood City, CA — Studio Piano Teacher (Sep. 2023 - Jun 2024)
    • Created and implemented individual piano curricula for students aged 6-17
    Supervisor: Chris Mallettinfo@thecaliforniaconservatory.com
    
    Return result in this format:
    {
      "jobTitle": "job title",
      "company": "company name",
      "location": "location",
      "duties": "brief description of duties"
    }
    """
    
    result = call_gemini_with_model_selection(prompt, "low", True)
    
    print(f"Model used: {result.get('model_used', 'unknown')}")
    
    if result["status"] == "success":
        print("\nResponse:")
        print(result["response"])
    else:
        print(f"\nError: {result.get('response', 'Unknown error')}")

if __name__ == "__main__":
    test_basic_functionality()