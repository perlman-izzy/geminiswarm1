#!/usr/bin/env python3
"""
Main entry point for the Multi-Agent Gemini AI System
"""
import os
import sys
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for

# Import from config
from config import LOG_DIR, API_KEYS

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "main.log"))
    ]
)
logger = logging.getLogger("main")

# Create the Flask app
app = Flask(__name__)

@app.route('/')
def index():
    """Render the main landing page."""
    # Check if API keys are configured
    api_keys_available = len([k for k in API_KEYS if k]) > 0
    
    return render_template(
        'index.html', 
        api_keys_available=api_keys_available,
        extended_proxy_url="http://localhost:3000"
    )

@app.route('/status')
def status():
    """Return the status of the system."""
    return jsonify({
        "status": "ok",
        "api_keys_available": len([k for k in API_KEYS if k]),
        "extended_proxy_running": is_service_running(3000)
    })

@app.route('/docs')
def docs():
    """Render the documentation page."""
    return render_template('index.html')

@app.route('/proxy')
def proxy_redirect():
    """Redirect to the extended proxy endpoint."""
    return redirect("http://localhost:3000")

def is_service_running(port):
    """Check if a service is running on the given port."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(("localhost", port))
        s.close()
        return True
    except:
        return False

if __name__ == "__main__":
    logger.info("Starting Multi-Agent Gemini AI System")
    
    # Check API keys
    api_keys_count = len([k for k in API_KEYS if k])
    if api_keys_count == 0:
        logger.warning("No API keys available! Please set GOOGLE_API_KEY1, GOOGLE_API_KEY2, GOOGLE_API_KEY3, or GEMINI_API_KEY")
    else:
        logger.info(f"Found {api_keys_count} API keys")
    
    # Start the Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)