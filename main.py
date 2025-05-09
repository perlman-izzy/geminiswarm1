#!/usr/bin/env python3
import requests
import sys
import json
import argparse
import logging
from typing import Dict, Any, Optional
from flask_proxy import app

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_request(prompt: str, server_url: str = "http://localhost:5000/gemini") -> Dict[str, Any]:
    """Send a prompt to the Gemini API proxy server.
    
    Args:
        prompt: The text prompt to send to Gemini
        server_url: The URL of the Gemini proxy server
        
    Returns:
        Dict containing the response from the server
    """
    try:
        data = {"prompt": prompt}
        
        logger.debug(f"Sending request to {server_url}")
        response = requests.post(server_url, json=data)
        
        # Check if request was successful
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.ConnectionError:
        logger.error(f"Could not connect to server at {server_url}")
        return {"error": f"Connection to {server_url} failed. Is the server running?", "status": "error"}
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        return {"error": f"HTTP error: {e}", "status": "error"}
        
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        return {"error": "Request timed out", "status": "error"}
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return {"error": f"Request error: {e}", "status": "error"}
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON response from server")
        return {"error": "Server did not return valid JSON", "status": "error"}
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": f"Unexpected error: {e}", "status": "error"}


def main():
    """Process command line arguments and send request to the Gemini API proxy."""
    parser = argparse.ArgumentParser(description="Command line client for Gemini AI proxy")
    parser.add_argument("prompt", nargs="?", help="The prompt to send to Gemini")
    parser.add_argument("--server", "-s", default="http://localhost:5000/gemini", 
                        help="Server URL (default: http://localhost:5000/gemini)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Configure logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # If no prompt is provided via command line, prompt the user
    if not args.prompt:
        logger.info("Enter your prompt (Ctrl+D or Ctrl+Z on a new line to finish):")
        prompt_lines = []
        try:
            while True:
                line = input()
                prompt_lines.append(line)
        except EOFError:
            args.prompt = "\n".join(prompt_lines)
    
    # Validate prompt
    if not args.prompt or args.prompt.strip() == "":
        logger.error("Error: No prompt provided")
        parser.print_help()
        sys.exit(1)
    
    logger.debug(f"Sending prompt: {args.prompt[:50]}...")
    
    # Send the request
    result = send_request(args.prompt, args.server)
    
    # Display the response
    if result.get("status") == "error":
        logger.error(f"Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    else:
        # Print just the response text without any additional formatting
        print(result.get("response", ""))


if __name__ == "__main__":
    main()
