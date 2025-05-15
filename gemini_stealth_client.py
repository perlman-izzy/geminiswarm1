#!/usr/bin/env python3
"""
gemini_stealth_client.py - Client for the Gemini Stealth Proxy
Enables transparent integration with the rest of the codebase
"""

import os
import sys
import logging
import json
from typing import Dict, List, Any, Optional, Union

# Import the proxy
from gemini_stealth_proxy import GeminiProxy, KeyManager

# Configure logging
logger = logging.getLogger("gemini_stealth_client")

# Initialize global proxy instance
_proxy = None

def get_proxy() -> GeminiProxy:
    """
    Get or initialize the proxy instance
    
    Returns:
        GeminiProxy instance
    """
    global _proxy
    if _proxy is None:
        _proxy = GeminiProxy()
    return _proxy

def text_to_gemini_content(text: str, role: str = "user") -> List[Dict[str, Any]]:
    """
    Convert text to Gemini API content format
    
    Args:
        text: Text content
        role: Role (user or model)
        
    Returns:
        Content in Gemini API format
    """
    return [
        {
            "parts": [
                {
                    "text": text
                }
            ],
            "role": role
        }
    ]

def generate_content(prompt: str, 
                   model: str = "gemini-1.5-pro", 
                   temperature: float = 0.7,
                   max_output_tokens: int = 4096) -> Dict[str, Any]:
    """
    Generate content using the stealth proxy
    Simplified interface compatible with existing code
    
    Args:
        prompt: Text prompt
        model: Model name
        temperature: Creativity parameter (0-1)
        max_output_tokens: Maximum output length
        
    Returns:
        Response dictionary with 'text' and 'model_used' keys
    """
    # Convert prompt to Gemini API format
    contents = text_to_gemini_content(prompt)
    
    # Build generation config
    generation_config = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
        "topP": 0.95,
        "topK": 40
    }
    
    # Get proxy instance
    proxy = get_proxy()
    
    try:
        # Make the API call
        response = proxy.generate_content(
            model=model,
            contents=contents,
            generation_config=generation_config,
            safety_settings=[
                {"category": "HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HATE", "threshold": "BLOCK_NONE"},
                {"category": "SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "DANGEROUS", "threshold": "BLOCK_NONE"}
            ]
        )
        
        # Extract text from response
        if "candidates" in response and response["candidates"]:
            candidate = response["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                text = candidate["content"]["parts"][0].get("text", "")
                
                # Return structured response compatible with existing code
                return {
                    "text": text,
                    "model_used": model,
                    "status": "success"
                }
        
        # Handle errors
        error_msg = "Unknown error"
        if "error" in response:
            error_msg = response["error"].get("message", str(response["error"]))
        
        return {
            "text": f"Error: {error_msg}",
            "model_used": model,
            "status": "error"
        }
        
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        return {
            "text": f"Error: {str(e)}",
            "model_used": model,
            "status": "error"
        }

def test_client():
    """Test the client with a simple request"""
    response = generate_content(
        prompt="Explain quantum computing in three sentences.",
        model="gemini-1.5-pro",
        temperature=0.7
    )
    
    print("\nGenerated Response:")
    print(f"Status: {response['status']}")
    print(f"Model: {response['model_used']}")
    print(f"Text: {response['text']}")
    
if __name__ == "__main__":
    # Configure logging when run directly
    logging.basicConfig(level=logging.INFO)
    
    # Test the client
    test_client()