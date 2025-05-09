from flask import Flask, request, jsonify
import google.generativeai as genai
import itertools
import os
import shutil
import subprocess
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Rotate through Gemini API keys
API_KEYS = [
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

# Remove None values
API_KEYS = [key for key in API_KEYS if key]

key_iter = itertools.cycle(API_KEYS)

# Model selection for delegation
# Small model for low-priority (dumb) tasks
SMALL_MODEL = 'models/gemini-1.5-flash'  # low-cost model for straightforward tasks

# Large model for high-priority (thinking) tasks
LARGE_MODEL = 'models/gemini-1.5-pro'  # advanced reasoning model

# --- Gemini endpoint with delegation ---
@app.route('/gemini', methods=['POST'])
def call_gemini():
    try:
        data = request.get_json() or {}
        prompt = data.get('prompt', '')
        # Priority: 'low' for simple, 'high' for complex reasoning
        priority = data.get('priority', 'low')
        
        if not prompt:
            logger.error("No prompt provided in request")
            return jsonify({'error': 'Missing prompt', 'status': 'error'}), 400
            
        api_key = next(key_iter)
        logger.info(f"Using API key: {api_key[:5]}... with priority {priority}")
        
        # Import and use our helper functions
        from ai_helper import configure_genai, get_model, generate_content, get_response_text
        configure_genai(api_key)
        
        # Choose model based on priority
        model_name = LARGE_MODEL if priority == 'high' else SMALL_MODEL
        logger.info(f"Selected model: {model_name} for {priority} priority task")
        
        model = get_model(model_name)
        
        # Configure safety settings to minimize filtering
        try:
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        except ImportError:
            safety_settings = {
                "HARASSMENT": "BLOCK_NONE",
                "HATE": "BLOCK_NONE",
                "SEXUAL": "BLOCK_NONE",
                "DANGEROUS": "BLOCK_NONE",
            }
            
        # Generation configuration
        gen_config = {
            "temperature": 0.7,
            "max_output_tokens": 8192,
            "top_p": 0.95,
            "top_k": 40,
        }
        
        response = generate_content(
            model,
            prompt, 
            safety_settings=safety_settings,
            generation_config=gen_config
        )
        
        response_text = get_response_text(response)
        logger.info(f"Successfully processed request with model {model_name}")
        logger.debug(f"Response text: {response_text[:100]}...")
        
        return jsonify({
            'response': response_text, 
            'model_used': model_name,
            'status': 'success',
            'priority': priority
        })
    except Exception as e:
        logger.error(f"Error in call_gemini: {str(e)}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

# --- Web Search endpoint ---
@app.route('/search', methods=['POST'])
def web_search():
    data = request.get_json() or {}
    query = data.get('query', '')
    max_results = data.get('max_results', 20)
    if not query:
        return jsonify({'error': 'Missing query'}), 400
    try:
        # Using duckduckgo_search library
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
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
    logger.info("Starting Extended Gemini API Proxy server on port 3000")
    app.run(host='0.0.0.0', port=3000, debug=True)