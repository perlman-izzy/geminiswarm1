"""
Helper module for interacting with the Google GenerativeAI (Gemini) API
Handles version differences and provides consistent interfaces
"""
import logging
from typing import Dict, Any, Optional, List, Union

import google.generativeai as genai

logger = logging.getLogger(__name__)

def configure_genai(api_key: str) -> None:
    """
    Configure the Google GenerativeAI client with the given API key.
    Compatible with different versions of the library.
    
    Args:
        api_key: Google API key for Gemini
    """
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        logger.warning(f"Error configuring genai with standard method: {e}")
        # Try alternative configuration methods if the main one fails
        try:
            if hasattr(genai, 'set_api_key'):
                genai.set_api_key(api_key)
            else:
                logger.error("No compatible configuration method found for this version of google.generativeai")
        except Exception as e2:
            logger.error(f"All configuration attempts failed: {e2}")
            raise

def get_model(model_name: str) -> Any:
    """
    Get a generative model by name, with compatibility handling for 
    different versions of the GenerativeAI SDK.
    
    Args:
        model_name: Name of the Gemini model to use
        
    Returns:
        A GenerativeModel instance or compatible object
    """
    try:
        model = genai.GenerativeModel(model_name)
        return model
    except Exception as e:
        logger.warning(f"Error getting model with standard method: {e}")
        # Try alternative methods
        try:
            if hasattr(genai, 'get_model'):
                return genai.get_model(model_name)
            else:
                logger.error("No compatible model creation method found")
                raise
        except Exception as e2:
            logger.error(f"All model creation attempts failed: {e2}")
            raise

def generate_content(
    model: Any,
    prompt: str,
    safety_settings: Optional[Dict[str, Any]] = None,
    generation_config: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Generate content using the given model and prompt, with compatibility
    handling for different API versions.
    
    Args:
        model: The generative model to use
        prompt: The text prompt to send
        safety_settings: Optional safety settings
        generation_config: Optional generation configuration
        
    Returns:
        Response object from the API
    """
    kwargs = {}
    if safety_settings:
        kwargs['safety_settings'] = safety_settings
    if generation_config:
        kwargs['generation_config'] = generation_config
        
    try:
        return model.generate_content(prompt, **kwargs)
    except Exception as e:
        logger.warning(f"Error generating content with standard method: {e}")
        # Try alternative methods
        try:
            if hasattr(model, 'generate_text'):
                return model.generate_text(prompt, **kwargs)
            elif hasattr(model, 'predict'):
                return model.predict(prompt, **kwargs)
            else:
                logger.error("No compatible content generation method found")
                raise
        except Exception as e2:
            logger.error(f"All content generation attempts failed: {e2}")
            raise

def get_response_text(response: Any) -> str:
    """
    Extract text from a response object, with compatibility handling.
    
    Args:
        response: Response object from the API
        
    Returns:
        Text content from the response
    """
    try:
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'candidates') and len(response.candidates) > 0:
            if hasattr(response.candidates[0], 'content'):
                return response.candidates[0].content.text
        elif hasattr(response, 'result'):
            return response.result
        elif isinstance(response, str):
            return response
        else:
            logger.warning(f"Unknown response format, attempting to convert to string: {type(response)}")
            return str(response)
    except Exception as e:
        logger.error(f"Failed to extract text from response: {e}")
        return "Error: Failed to extract text from response"
    
    # This line should never be reached, but is added to satisfy the type checker
    return ""

def list_available_models() -> List[Dict[str, Any]]:
    """
    List available Gemini models, with compatibility handling.
    
    Returns:
        List of model information dictionaries
    """
    try:
        models = genai.list_models()
        if hasattr(models, '__iter__'):
            return list(models)
        else:
            logger.warning("list_models didn't return an iterable")
            return []
    except Exception as e:
        logger.warning(f"Error listing models with standard method: {e}")
        # Some versions might return model names directly
        try:
            if hasattr(genai, 'list_tuned_model_names'):
                return [{"name": name} for name in genai.list_tuned_model_names()]
            elif hasattr(genai, 'available_models'):
                return [{"name": name} for name in genai.available_models()]
            else:
                logger.error("No compatible method to list models found")
                return []
        except Exception as e2:
            logger.error(f"All model listing attempts failed: {e2}")
            return []