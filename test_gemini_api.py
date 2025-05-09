#!/usr/bin/env python3
import os
import sys
import google.generativeai as genai

def test_gemini_api():
    """Test if the Gemini API key works properly"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        return False
    
    print(f"Testing Gemini API key: {api_key[:5]}...")
    
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Create a model object
        model = genai.GenerativeModel("gemini-pro")
        
        # Generate a simple response
        response = model.generate_content("Hello! Can you tell me a short joke?")
        
        # Print the response
        print(f"API test successful! Response: {response.text}")
        return True
    
    except Exception as e:
        print(f"API test failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_gemini_api()
    sys.exit(0 if success else 1)