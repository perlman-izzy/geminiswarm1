"""
Client for interacting with the Gemini API Proxy
"""
import requests
import json
import time
from typing import Optional
from logger import setup_logger

logger = setup_logger("gemini_client")

# Rate limiting parameters
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds between retries

def propose_fix(proxy_url: str, code: str, error_output: str) -> str:
    """
    Send code with error to Gemini and get proposed fix.
    
    Args:
        proxy_url: URL of the Gemini proxy server
        code: The original code with issues
        error_output: Error output from running tests
        
    Returns:
        Fixed code as string, or empty string if failed
    """
    if not proxy_url.endswith("/gemini"):
        proxy_url = f"{proxy_url}/gemini"
    
    # Craft a prompt that will help Gemini fix the issue
    prompt = f"""You are debugging a Python file that has errors. Please fix the code based on the error messages.

## Original Code:
```python
{code}
```

## Error Output:
```
{error_output}
```

## Instructions:
1. Analyze the error message and identify the issues in the code.
2. Provide the complete fixed code (not just the changes).
3. Make minimal changes necessary to fix the errors.
4. Ensure your solution is complete and syntactically correct.
5. Do not change functionality, only fix what's broken.
6. Format your response with ONLY the complete fixed code, no explanations.

Respond with ONLY the fixed code with no extra text, markdown formatting, or code block markers.
"""
    
    logger.info(f"Sending code to Gemini API for fix proposals via {proxy_url}")
    logger.debug(f"Original code length: {len(code)} chars")
    logger.debug(f"Error output length: {len(error_output)} chars")
    
    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                logger.info(f"Retry attempt {attempt+1}/{MAX_RETRIES} after {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
                
            response = requests.post(
                proxy_url,
                json={"prompt": prompt},
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            # Handle rate limiting explicitly
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', RETRY_DELAY))
                logger.warning(f"Rate limit exceeded. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
                continue
                
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "error":
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Gemini API error: {error_msg}")
                
                # Check for rate limiting in the error message
                if "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                    if attempt < MAX_RETRIES - 1:
                        logger.warning("Rate limit error detected in response. Retrying...")
                        time.sleep(RETRY_DELAY)
                        continue
                
                return ""
            
            fixed_code = result.get("response", "")
            
            # Clean up any code block markers that might have been included
            fixed_code = fixed_code.replace("```python", "").replace("```", "").strip()
            
            logger.info(f"Received proposed fix with {len(fixed_code)} chars")
            return fixed_code
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error when calling Gemini API: {str(e)}")
            if "429" in str(e) and attempt < MAX_RETRIES - 1:
                logger.warning("Rate limit error detected. Retrying...")
                time.sleep(RETRY_DELAY)
                continue
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from Gemini API")
            
        except Exception as e:
            logger.error(f"Unexpected error when calling Gemini API: {str(e)}")
    
    # If we've exhausted all retries
    logger.error(f"Failed to get a response after {MAX_RETRIES} attempts")
    return ""