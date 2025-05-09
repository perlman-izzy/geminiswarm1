#!/usr/bin/env python3
"""
Script to start the extended Gemini proxy server on port 3000.
"""
import os
import sys
import logging
import subprocess

logging.basicConfig(level=logging.INFO,
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Start the extended proxy server."""
    logger.info("Starting Extended Gemini Proxy on port 3000...")
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the project root
    root_dir = os.path.dirname(script_dir)
    # Path to flask_proxy_extended.py
    proxy_path = os.path.join(root_dir, "flask_proxy_extended.py")
    
    # Check if the extended proxy script exists
    if not os.path.exists(proxy_path):
        logger.error(f"Could not find {proxy_path}")
        return 1
    
    try:
        # Start the extended proxy server
        cmd = [sys.executable, proxy_path]
        logger.info(f"Running command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            cwd=root_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Print output in real-time
        for line in process.stdout:
            print(line, end='')
        
        # Wait for the process to complete
        return_code = process.wait()
        
        if return_code != 0:
            logger.error(f"Extended proxy server exited with code {return_code}")
            return return_code
            
        return 0
    
    except Exception as e:
        logger.exception(f"Error starting extended proxy: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())