import os
import logging
import itertools
import time
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Get API keys from environment variables (new keys provided by user)
API_KEYS = [
    # Fresh API keys provided by the user
    "AIzaSyCcqC_3qZjfunJmEVDwH25cYiT6EoyVCqA",
    "AIzaSyAqsSH2B0ZrFrBqcs7QJZle6hFlx9O3zC4",
    "AIzaSyDcf_j8sk-gQK_z3QRupDOBxSQbzGPPwbs",
    "AIzaSyAF66TFgv2o_BNNNXTt4IPNz38Zf0CcfR4",
    "AIzaSyBPizTLUOcA_Gx27aeQ9E0KSKgAePNfERM",
    "AIzaSyDn4whqPnQVnLCeqE42lWwdRoDahTC_9vc",
    "AIzaSyB5nL_8t7sOpfnRaEs0-FldlqXoFCkEcbA",
    "AIzaSyC6wrXb9L4yJTqFo21HjTwTgnlNPl-m4pU",
    "AIzaSyB7hWAfS1EoH3pdXGHP6DVQkJsGqhlW1k8",
    "AIzaSyCxjnfVbSr2xTkyEqll_p9CH-QrlToBV8g",
    "AIzaSyDQ7_nCuQ4G8bDRUm9zF630qKrzpWzNA74",
    "AIzaSyDiIEjcIu2BiLdx-p5c_tNdi80cq1awn6w",
    # Environment variable keys
    os.environ.get("GEMINI_API_KEY"),
    os.environ.get("GOOGLE_API_KEY1"),
    os.environ.get("GOOGLE_API_KEY2"),
    os.environ.get("GOOGLE_API_KEY3"),
]

# Remove any None or empty values from API_KEYS
API_KEYS = [key for key in API_KEYS if key]

logger.info(f"Loaded {len(API_KEYS)} API keys for rotation")

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
        
        # Try up to 5 different API keys in case of failures
        max_attempts = min(5, len(API_KEYS))
        retry_delay = 2  # seconds between retries
        
        for attempt in range(max_attempts):
            api_key = next(key_iter)
            key_statistics[api_key]["uses"] += 1
            
            try:
                logger.info(f"Attempt {attempt+1}/{max_attempts}: Using API key: {api_key[:5]}... for request")
                genai.configure(api_key=api_key)
                
                # Try with different models if available - start with newer models
                model_names = [
                    "models/gemini-1.5-flash",      # Faster, lower quality
                    "models/gemini-1.5-pro",        # Higher quality, slower
                    "models/gemini-pro-vision",     # Fallback older model
                ]
                
                # Try each model until one works
                for model_name in model_names:
                    try:
                        model = genai.GenerativeModel(model_name)
                        logger.debug(f"Trying model: {model_name}")
                        logger.debug(f"Sending prompt: {prompt[:50]}...")
                        
                        # Safety settings to minimize filtering
                        safety_settings = {
                            "HARASSMENT": "BLOCK_NONE",
                            "HATE": "BLOCK_NONE",
                            "SEXUAL": "BLOCK_NONE",
                            "DANGEROUS": "BLOCK_NONE",
                        }
                        
                        response = model.generate_content(
                            prompt, 
                            safety_settings=safety_settings,
                            generation_config={"temperature": 0.7, "max_output_tokens": 1000}
                        )
                        
                        # Log successful request
                        logger.info(f"Successfully processed request with key {api_key[:5]}... and model {model_name}")
                        logger.debug(f"Response text: {response.text[:100]}...")
                        
                        return jsonify({
                            "response": response.text,
                            "status": "success",
                            "model": model_name
                        })
                    
                    except Exception as model_error:
                        logger.warning(f"Model {model_name} failed: {str(model_error)}")
                        continue  # Try next model
                
                # If we get here, all models failed with this key
                raise Exception(f"All models failed with API key {api_key[:5]}...")
                
            except Exception as e:
                # Handle rate limiting specially
                if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                    logger.warning(f"Rate limit hit with key {api_key[:5]}... : {str(e)}")
                else:
                    logger.warning(f"API key {api_key[:5]}... failed: {str(e)}")
                
                # Log the failure and try next key
                key_statistics[api_key]["failures"] += 1
                
                # Wait before trying next key
                if attempt < max_attempts - 1:
                    logger.info(f"Waiting {retry_delay}s before trying next key...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Increase delay for each retry
        
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
