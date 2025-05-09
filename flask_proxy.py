import os
import logging
import itertools
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Use environment variable for API key
gemini_api_key = os.environ.get("GEMINI_API_KEY")

# API keys for Gemini - use the environment variable if available, otherwise fallback to the list
API_KEYS = [gemini_api_key] if gemini_api_key else [
    "cwV8AcSbpNvcvrMwhDTArKjQsk",  # These are placeholder keys
    "AIzaSyBcwbIZPq3yqVonOG-8AqPSaUuv6vzQWyRE",
    "AIzaSyDln6sUGiaidN5CmKDGw3qt1spvgz94QKo",
    "AIzaSyDozMeIBRZrvGYSt8Ffua3rGp4DlDnONEo",
    "AIzaSyBAvBbhU71l63Ei25F-eHb0QMKjuotDPIg",
    "AIzaSyCre8WOWbchKsT7l67V7aIsMGneIEOa59s",
    "AIzaSyCV3OauLHIpUHV722MszP2JTir_tkC1ECM",
    "AIzaSyCvKDI8jyoWDYGIaolxsi5A95MPxR2EDKQ",
    "AIzaSyAeONfijWy8EPJqAY3B0DJedepcGyYRrWU",
]
# Remove any None values from API_KEYS
API_KEYS = [key for key in API_KEYS if key]

# Create a cyclic iterator through the API keys
key_iter = itertools.cycle(API_KEYS)

# Track API key usage and failures
key_statistics = {key: {"uses": 0, "failures": 0} for key in API_KEYS}


@app.route("/", methods=["GET"])
def index():
    """Render the web interface for the Gemini proxy."""
    return render_template("index.html")


@app.route("/gemini", methods=["POST"])
def call_gemini():
    """Proxy endpoint for Gemini API calls with key rotation."""
    try:
        logger.info("Received request to /gemini endpoint")
        data = request.get_json()
        logger.debug(f"Request data: {data}")
        
        if not data:
            logger.error("No JSON data received in request")
            return jsonify({"error": "No data provided", "status": "error"}), 400
        
        prompt = data.get("prompt", "")
        logger.info(f"Prompt received: {prompt[:50]}...")
        
        if not prompt:
            logger.error("No prompt provided in request")
            return jsonify({"error": "No prompt provided", "status": "error"}), 400
        
        # Try up to 3 different API keys in case of failures
        for attempt in range(min(3, len(API_KEYS))):
            api_key = next(key_iter)
            key_statistics[api_key]["uses"] += 1
            
            try:
                logger.info(f"Attempt {attempt+1}: Using API key: {api_key[:5]}... for request")
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("models/gemini-1.5-pro")
                
                logger.debug(f"Sending prompt to Gemini: {prompt[:50]}...")
                response = model.generate_content(prompt)
                
                # Log successful request
                logger.info(f"Successfully processed request with key {api_key[:5]}...")
                logger.debug(f"Response text: {response.text[:100]}...")
                
                return jsonify({
                    "response": response.text,
                    "status": "success"
                })
                
            except Exception as e:
                # Log the failure and try next key
                key_statistics[api_key]["failures"] += 1
                logger.warning(f"API key {api_key[:5]}... failed: {str(e)}")
                logger.exception("Detailed exception info:")
                continue
        
        # If we've tried multiple keys and all failed
        logger.error("All API keys failed to process the request")
        return jsonify({
            "error": "All available API keys failed to process your request",
            "status": "error"
        }), 500
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.exception("Detailed exception info:")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


@app.route("/stats", methods=["GET"])
def get_stats():
    """Return anonymized API key usage statistics."""
    # Create anonymized version of stats
    anonymized_stats = {}
    for i, key in enumerate(API_KEYS):
        anonymized_stats[f"key_{i+1}"] = key_statistics[key]
    
    return jsonify({
        "total_keys": len(API_KEYS),
        "key_stats": anonymized_stats
    })


if __name__ == "__main__":
    logger.info("Starting Gemini API Proxy server on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
