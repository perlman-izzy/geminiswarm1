import os
import logging
import itertools
import time
import shutil
import subprocess
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# Import configuration from config.py
from config import (
    API_KEYS, DEFAULT_MODELS, SAFETY_SETTINGS, 
    GENERATION_CONFIG, MAIN_PROXY_PORT, LOG_FORMAT
)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# API keys are loaded from config.py

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
                from ai_helper import configure_genai, get_model, generate_content, get_response_text
                configure_genai(api_key)
                
                # Use models from config
                model_names = DEFAULT_MODELS
                
                # Try each model until one works
                for model_name in model_names:
                    try:
                        model = get_model(model_name)
                        logger.debug(f"Trying model: {model_name}")
                        logger.debug(f"Sending prompt: {prompt[:50]}...")
                        
                        response = generate_content(
                            model,
                            prompt, 
                            safety_settings=SAFETY_SETTINGS,
                            generation_config=GENERATION_CONFIG
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


# --- Web Search endpoint ---
@app.route('/search', methods=['POST'])
def web_search():
    data = request.get_json() or {}
    query = data.get('query', '')
    if not query:
        return jsonify({'error': 'Missing query'}), 400
    try:
        # Simple search implementation using requests
        search_url = f"https://duckduckgo.com/html/?q={query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        
        for result in soup.select('.result'):
            title_el = result.select_one('.result__title')
            url_el = result.select_one('.result__url')
            snippet_el = result.select_one('.result__snippet')
            
            title = title_el.get_text() if title_el else ""
            url = url_el.get_text() if url_el else ""
            snippet = snippet_el.get_text() if snippet_el else ""
            
            if title and url:
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })
                
        return jsonify({'results': results})
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# --- HTTP GET / Scrape endpoint ---
@app.route('/fetch_url', methods=['POST'])
def fetch_url():
    data = request.get_json() or {}
    url = data.get('url', '')
    if not url:
        return jsonify({'error': 'Missing url'}), 400
    try:
        resp = requests.get(url, timeout=10)
        return jsonify({'status_code': resp.status_code, 'text': resp.text})
    except Exception as e:
        logger.error(f"Fetch URL error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# --- Text Scraping endpoint ---
@app.route('/scrape_text', methods=['POST'])
def scrape_text():
    data = request.get_json() or {}
    url = data.get('url', '')
    selector = data.get('selector', None)
    if not url:
        return jsonify({'error': 'Missing url'}), 400
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        if selector:
            elements = soup.select(selector)
            text = '\n'.join([el.get_text() for el in elements])
        else:
            text = soup.get_text()
        return jsonify({'text': text})
    except Exception as e:
        logger.error(f"Scrape text error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# --- File System Endpoints ---
@app.route('/list_files', methods=['GET'])
def list_files():
    path = request.args.get('path', '.')
    files = []
    for root, dirs, fs in os.walk(path):
        for f in fs:
            files.append(os.path.join(root, f))
    return jsonify({'files': files})


@app.route('/read_file', methods=['POST'])
def read_file():
    data = request.get_json() or {}
    path = data.get('path', '')
    if not path or not os.path.isfile(path):
        return jsonify({'error': 'Invalid path'}), 400
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        logger.error(f"Read file error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/write_file', methods=['POST'])
def write_file():
    data = request.get_json() or {}
    path = data.get('path', '')
    content = data.get('content', None)
    if not path or content is None:
        return jsonify({'error': 'Missing path or content'}), 400
    
    # Create a backup if the file exists
    bak = path + '.bak'
    try:
        if os.path.exists(path):
            shutil.copy2(path, bak)
    except Exception as e:
        logger.warning(f"Failed to create backup of {path}: {str(e)}")
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Write file error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# --- Execute script endpoint ---
@app.route('/exec', methods=['POST'])
def execute_script():
    data = request.get_json() or {}
    cmd = data.get('cmd', '')
    cwd = data.get('cwd', None)
    timeout = data.get('timeout', 60)
    if not cmd:
        return jsonify({'error': 'Missing cmd'}), 400
    
    cmd_list = cmd.split() if isinstance(cmd, str) else cmd
    try:
        proc = subprocess.run(cmd_list, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return jsonify({
            'returncode': proc.returncode,
            'stdout': proc.stdout,
            'stderr': proc.stderr
        })
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {cmd}")
        return jsonify({'error': f"Command timed out after {timeout}s"}), 500
    except Exception as e:
        logger.error(f"Execute script error: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    logger.info("Starting Gemini API Proxy server on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
