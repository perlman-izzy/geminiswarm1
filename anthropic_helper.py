#!/usr/bin/env python3
"""
Helper module for interacting with Anthropic's Claude API
Provides functions to generate content using Claude models as fallbacks
"""
import os
import logging
import json
import sys
from typing import Dict, Any, Optional

from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT

# Configure logging
logger = logging.getLogger(__name__)

def initialize_anthropic_client(api_key: Optional[str] = None) -> Optional[Anthropic]:
    """
    Initialize the Anthropic client with the given API key.
    
    Args:
        api_key: Optional API key (will use env var if not provided)
        
    Returns:
        Anthropic client or None if initialization failed
    """
    try:
        # Use provided key or get from environment
        actual_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if not actual_key:
            logger.warning("No Anthropic API key available")
            return None
            
        # Initialize client
        client = Anthropic(api_key=actual_key)
        logger.debug("Anthropic client initialized successfully")
        return client
        
    except Exception as e:
        logger.error(f"Error initializing Anthropic client: {e}")
        return None

def generate_with_anthropic(
    prompt: str,
    model_name: str = "claude-3-5-sonnet-20241022", # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024.
    temperature: float = 0.7,
    max_tokens: int = 4096,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate content using Anthropic's Claude models.
    
    Args:
        prompt: The text prompt
        model_name: Claude model to use
        temperature: Creativity setting (0.0-1.0)
        max_tokens: Maximum tokens to generate
        api_key: Optional API key (will use env var if not provided)
        
    Returns:
        Dict with response, model_used, and status
    """
    result = {"response": "", "model_used": f"anthropic/{model_name}", "status": "error"}
    
    try:
        # Initialize client
        client = initialize_anthropic_client(api_key)
        if not client:
            result["response"] = "Failed to initialize Anthropic client"
            return result
            
        # Call the Anthropic API
        response = client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            system="You are a helpful, accurate, and concise assistant.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract and return the text
        if response.content and len(response.content) > 0:
            result["response"] = response.content[0].text if hasattr(response.content[0], "text") else str(response.content[0])
        else:
            result["response"] = str(response) 
        result["status"] = "success"
        return result
        
    except Exception as e:
        logger.error(f"Error generating with Anthropic: {e}")
        result["response"] = f"Anthropic generation error: {str(e)}"
        return result