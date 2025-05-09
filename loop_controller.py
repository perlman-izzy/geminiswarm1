"""Loop controller for the Gemini Swarm Debugger."""
import os
import subprocess
import json
import logging
import requests
import tempfile
import time
from typing import List, Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd: str) -> Tuple[int, str, str]:
    """Run a shell command and return the exit code, stdout, and stderr.
    
    Args:
        cmd: The command to run.
        
    Returns:
        A tuple of (exit_code, stdout, stderr).
    """
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr


def call_gemini(prompt: str, proxy_url: str) -> Optional[str]:
    """Send a prompt to the Gemini API via the proxy server.
    
    Args:
        prompt: The text prompt to send to Gemini.
        proxy_url: The URL of the Gemini proxy server.
        
    Returns:
        The response text from Gemini, or None if the request failed.
    """
    try:
        # Make sure we're sending to the /gemini endpoint
        if not proxy_url.endswith("/gemini"):
            proxy_url = f"{proxy_url}/gemini"
            
        data = {"prompt": prompt}
        response = requests.post(proxy_url, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        if result.get("status") == "error":
            logger.error(f"API Error: {result.get('error')}")
            return None
        
        return result.get("response")
        
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        return None


def generate_fix_prompt(file_path: str, error_output: str) -> str:
    """Generate a prompt for Gemini to fix a file based on error output.
    
    Args:
        file_path: Path to the file that needs fixing.
        error_output: Error output from running the test command.
        
    Returns:
        A formatted prompt for the Gemini API.
    """
    try:
        with open(file_path, 'r') as f:
            file_content = f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return ""
    
    # Create a detailed prompt with context and error information
    prompt = f"""You are debugging a Python file that has errors. Please fix the code below based on the error messages provided.

# File Path: {file_path}

## Current Code:
```python
{file_content}
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

Respond with ONLY the fixed code with no extra text or markdown formatting.
"""
    return prompt


def fix_file_loop(file_path: str, proxy_url: str, test_cmd: str, max_attempts: int) -> bool:
    """Attempt to fix a file by iteratively using Gemini AI.
    
    Args:
        file_path: Path to the file to fix.
        proxy_url: URL of the Gemini proxy server.
        test_cmd: Command to test if the file works correctly.
        max_attempts: Maximum number of fix attempts to try.
        
    Returns:
        True if the file was successfully fixed, False otherwise.
    """
    # First, check if the file already works
    logger.info(f"Initial test of {file_path}")
    exit_code, stdout, stderr = run_command(test_cmd)
    
    if exit_code == 0:
        logger.info(f"File {file_path} already works!")
        return True
    
    # File has issues, attempt to fix
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Fix attempt {attempt}/{max_attempts} for {file_path}")
        
        # Combine stdout and stderr for context in the prompt
        error_output = f"Exit code: {exit_code}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
        
        # Generate a prompt for Gemini
        prompt = generate_fix_prompt(file_path, error_output)
        
        # Call Gemini for a fix
        fixed_code = call_gemini(prompt, proxy_url)
        
        if not fixed_code:
            logger.warning(f"Failed to get a response from Gemini for {file_path}, attempt {attempt}")
            time.sleep(2)  # Wait before retry
            continue
        
        # Create a backup of the original file
        backup_path = f"{file_path}.bak{attempt}"
        try:
            with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
                dst.write(src.read())
        except Exception as e:
            logger.error(f"Error creating backup of {file_path}: {str(e)}")
            continue
        
        # Apply the fix
        try:
            with open(file_path, 'w') as f:
                f.write(fixed_code)
        except Exception as e:
            logger.error(f"Error writing fixed code to {file_path}: {str(e)}")
            # Restore from backup
            with open(backup_path, 'r') as src, open(file_path, 'w') as dst:
                dst.write(src.read())
            continue
        
        # Test the fixed version
        logger.info(f"Testing fix for {file_path}, attempt {attempt}")
        exit_code, stdout, stderr = run_command(test_cmd)
        
        if exit_code == 0:
            logger.info(f"Successfully fixed {file_path} on attempt {attempt}!")
            return True
        
        logger.warning(f"Fix attempt {attempt} for {file_path} failed with exit code {exit_code}")
    
    logger.error(f"Failed to fix {file_path} after {max_attempts} attempts")
    return False