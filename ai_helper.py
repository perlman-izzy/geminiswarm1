#!/usr/bin/env python3
"""
Helper module for interacting with the Google GenerativeAI (Gemini) API
Handles version differences and provides consistent interfaces
"""
import os
import sys
import logging
from typing import Any, Dict, List, Optional, Union, Tuple

# Import Google's GenerativeAI library
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)

def configure_genai(api_key: str) -> None:
    """
    Configure the Google GenerativeAI client with the given API key.
    Compatible with different versions of the library.
    
    Args:
        api_key: Google API key for Gemini
    """
    try:
        # Try the new API configuration method first
        genai.configure(api_key=api_key)
        logger.debug("Configured GenerativeAI using configure() method")
    except AttributeError:
        # Fall back to the older method for backward compatibility
        try:
            # Some versions use a different method
            genai.set_api_key(api_key)
            logger.debug("Configured GenerativeAI using set_api_key() method")
        except AttributeError:
            # If all fails, try setting the environment variable
            os.environ["GOOGLE_API_KEY"] = api_key
            logger.warning("Configured GenerativeAI using environment variable (fallback method)")

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
        # Try using the GenerativeModel constructor from the newer versions
        model = genai.GenerativeModel(model_name=model_name)
        logger.debug(f"Created model {model_name} using GenerativeModel constructor")
        return model
    except AttributeError:
        try:
            # Try using the get_model method from older versions
            model = genai.get_model(model_name=model_name)
            logger.debug(f"Created model {model_name} using get_model method")
            return model
        except Exception as e:
            logger.error(f"Failed to get model {model_name}: {str(e)}")
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
    try:
        # Check what method is available on the model instance
        if hasattr(model, "generate_content"):
            # Newer version of the API
            if safety_settings and generation_config:
                response = model.generate_content(
                    prompt, 
                    safety_settings=safety_settings,
                    generation_config=generation_config
                )
            elif safety_settings:
                response = model.generate_content(
                    prompt, 
                    safety_settings=safety_settings
                )
            elif generation_config:
                response = model.generate_content(
                    prompt, 
                    generation_config=generation_config
                )
            else:
                response = model.generate_content(prompt)
                
            logger.debug("Generated content using generate_content method")
            return response
            
        elif hasattr(model, "generate"):
            # Older version of the API
            kwargs = {}
            if safety_settings:
                kwargs["safety_settings"] = safety_settings
            if generation_config:
                kwargs.update(generation_config)
                
            response = model.generate(prompt, **kwargs)
            logger.debug("Generated content using generate method")
            return response
            
        else:
            # Last resort - try a direct call
            logger.warning("No recognized generation method found, attempting direct call")
            return model(prompt)
            
    except Exception as e:
        logger.error(f"Error generating content: {str(e)}")
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
        # For newer SDK versions
        if hasattr(response, "text"):
            return response.text
            
        # For candidate-based responses
        if hasattr(response, "candidates"):
            cand = response.candidates[0]
            if hasattr(cand, "content") and hasattr(cand.content, "parts"):
                return cand.content.parts[0].text
            elif hasattr(cand, "text"):
                return cand.text
                
        # For result-based responses
        if hasattr(response, "result"):
            result = response.result
            if hasattr(result, "response") and hasattr(result.response, "text"):
                return result.response.text
                
        # For dictionary-style responses
        if isinstance(response, dict):
            if "candidates" in response and len(response["candidates"]) > 0:
                cand = response["candidates"][0]
                if "content" in cand and "parts" in cand["content"]:
                    return cand["content"]["parts"][0]["text"]
                elif "text" in cand:
                    return cand["text"]
                    
        # Last resort - try string conversion
        return str(response)
        
    except Exception as e:
        logger.error(f"Error extracting text from response: {str(e)}")
        return f"Error extracting response: {str(e)}"

def list_available_models() -> List[Dict[str, Any]]:
    """
    List available Gemini models, with compatibility handling.
    
    Returns:
        List of model information dictionaries
    """
    try:
        # Try newer methods first
        models = genai.list_models()
        logger.debug("Listed models using list_models method")
        
        # Filter for Gemini models only
        gemini_models = [m for m in models if "gemini" in m.name.lower()]
        
        # Convert to dictionaries for consistent handling
        return [{"name": m.name, "version": getattr(m, "version", "unknown")} for m in gemini_models]
        
    except AttributeError:
        try:
            # Try older methods
            gemini_models = genai.list_tuned_model_names()
            logger.debug("Listed models using list_tuned_model_names method")
            return [{"name": m, "version": "unknown"} for m in gemini_models]
        except AttributeError:
            # Last resort - check if the available_models is directly accessible
            if hasattr(genai, "available_models"):
                models = [{"name": m, "version": "unknown"} for m in genai.available_models 
                         if "gemini" in m.lower()]
                logger.debug("Listed models using available_models attribute")
                return models
                
            # If all fails, return a list of known models
            logger.warning("Could not list models dynamically, returning hardcoded list")
            return [
                {"name": "gemini-2.5-pro", "version": "latest"},
                {"name": "gemini-2.5-flash", "version": "latest"},
                {"name": "gemini-1.5-pro", "version": "latest"},
                {"name": "gemini-1.5-flash", "version": "latest"},
                {"name": "gemini-1.0-pro", "version": "latest"},
                {"name": "gemini-1.0-pro-vision", "version": "latest"}
            ]

if __name__ == "__main__":
    # Set up console logging when run directly
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Read API key from environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = os.environ.get("GOOGLE_API_KEY")
        
    if not api_key:
        print("Error: No API key found in environment variables. Please set GEMINI_API_KEY or GOOGLE_API_KEY.")
        sys.exit(1)
    
    # Configure the API
    configure_genai(api_key)
    
    # List available models
    try:
        models = list_available_models()
        print(f"Available Gemini models ({len(models)}):")
        for i, model in enumerate(models, 1):
            print(f"  {i}. {model['name']} (version: {model['version']})")
    except Exception as e:
        print(f"Error listing models: {e}")
        
    # Test the API with a simple prompt
    try:
        model = get_model("models/gemini-1.5-flash")
        print("\nTesting API with a simple prompt...")
        
        response = generate_content(model, "Write a haiku about artificial intelligence.")
        text = get_response_text(response)
        
        print("\nResponse:")
        print(text)
    except Exception as e:
        print(f"Error testing API: {e}")