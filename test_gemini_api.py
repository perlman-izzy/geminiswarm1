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
        
        # List available models
        print("\nListing available models:")
        models = genai.list_models()
        for model in models:
            print(f"- {model.name}")
        
        # Try to find a model that supports text generation
        model_name = None
        for model in models:
            if "gemini" in model.name.lower() and hasattr(model, 'supported_generation_methods'):
                if 'generateContent' in getattr(model, 'supported_generation_methods', []):
                    model_name = model.name
                    break
        
        if not model_name:
            # Try with a model from the list directly
            model_name = "models/gemini-1.5-pro"  # Use the latest model
            print(f"\nNo suitable model found automatically, trying with model: {model_name}")
        else:
            print(f"\nUsing model: {model_name}")
        
        # Create a model object
        model = genai.GenerativeModel(model_name)
        
        # Generate a simple response
        response = model.generate_content("Hello! Can you tell me a short joke?")
        
        # Print the response
        print(f"\nAPI test successful! Response: {response.text}")
        return True
    
    except Exception as e:
        print(f"\nAPI test failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_gemini_api()
    sys.exit(0 if success else 1)