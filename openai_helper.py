#!/usr/bin/env python3
"""
Helper module for interacting with OpenAI API
Provides functions to generate content using OpenAI models as fallbacks
"""
import os
import logging
import json
from typing import Dict, Any, Optional

from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)

def initialize_openai_client(api_key: Optional[str] = None) -> Optional[OpenAI]:
    """
    Initialize the OpenAI client with the given API key.
    
    Args:
        api_key: Optional API key (will use env var if not provided)
        
    Returns:
        OpenAI client or None if initialization failed
    """
    try:
        # Use provided key or get from environment
        actual_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not actual_key:
            logger.warning("No OpenAI API key available")
            return None
            
        # Initialize client
        if actual_key:
            client = OpenAI(api_key=actual_key)
            logger.debug("OpenAI client initialized successfully")
            return client
        else:
            logger.warning("No OpenAI API key provided")
            return None
        
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {e}")
        return None

def generate_with_openai(
    prompt: str,
    model_name: str = "gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
    temperature: float = 0.7,
    max_tokens: int = 8192,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate content using OpenAI models.
    
    Args:
        prompt: The text prompt
        model_name: Model to use
        temperature: Creativity setting (0.0-1.0)
        max_tokens: Maximum tokens to generate
        api_key: Optional API key (will use env var if not provided)
        
    Returns:
        Dict with response, model_used, and status
    """
    result = {"response": "", "model_used": f"openai/{model_name}", "status": "error"}
    
    try:
        # Initialize client
        client = initialize_openai_client(api_key)
        if not client:
            result["response"] = "Failed to initialize OpenAI client"
            return result
            
        # Call the OpenAI Chat Completions API
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful, accurate, and concise assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Extract and return the response
        if response.choices and len(response.choices) > 0 and response.choices[0].message:
            message_content = response.choices[0].message.content
            if message_content is not None:
                result["response"] = message_content
            else:
                result["response"] = "No content returned from model"
        else:
            result["response"] = "Empty response from model"
            
        result["status"] = "success"
        return result
        
    except Exception as e:
        logger.error(f"Error generating with OpenAI: {e}")
        result["response"] = f"OpenAI generation error: {str(e)}"
        return result