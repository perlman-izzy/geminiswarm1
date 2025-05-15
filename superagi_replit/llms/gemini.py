"""
Gemini LLM implementation for SuperAGI, using the local proxy.
"""
import json
import requests
from typing import List, Dict, Union
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from superagi_replit.config import get_config
from superagi_replit.lib.logger import logger
from superagi_replit.llms.base_llm import BaseLlm

# Constants
MAX_RETRY_ATTEMPTS = 3
MIN_WAIT = 2  # seconds
MAX_WAIT = 20  # seconds


class GeminiProxy(BaseLlm):
    def __init__(self, model="gemini-2.5-pro", temperature=0.7, max_tokens=4096, 
                 top_p=1.0, frequency_penalty=0, presence_penalty=0):
        """
        Initialize the Gemini LLM with the proxy.
        
        Args:
            model: The model name to use
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter (0-1)
            frequency_penalty: Penalizes repeated tokens
            presence_penalty: Penalizes tokens already in context
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.proxy_url = get_config("GEMINI_PROXY_URL")
        
    def get_source(self) -> str:
        """Get the source of the LLM."""
        return "gemini"
    
    def get_model(self) -> str:
        """Get the model name."""
        return self.model
    
    def get_models(self) -> List[str]:
        """Get available models."""
        return ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]
    
    def verify_access_key(self) -> bool:
        """Verify that the access key is valid."""
        # The proxy handles authentication
        return True
    
    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=MIN_WAIT, max=MAX_WAIT),
        retry=retry_if_exception_type((requests.exceptions.RequestException, json.JSONDecodeError)),
        reraise=True
    )
    def chat_completion(self, prompt: Union[str, List[Dict[str, str]]]) -> str:
        """
        Generate a chat completion for the given prompt.
        
        Args:
            prompt: A list of messages in the format {"role": role, "content": content}
                   or a string
        
        Returns:
            The response text
        """
        try:
            # Convert string to chat format if needed
            if isinstance(prompt, str):
                messages = [{"role": "user", "content": prompt}]
            else:
                messages = prompt
                
            # Prepare the request payload
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "top_p": self.top_p,
                "frequency_penalty": self.frequency_penalty,
                "presence_penalty": self.presence_penalty
            }
            
            # Send the request to the proxy
            response = requests.post(
                self.proxy_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            # Check for errors
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Extract the response text
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                error_msg = f"Unexpected response format: {result}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error in Gemini proxy: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Gemini proxy: {str(e)}")
            raise