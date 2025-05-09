import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Google Gemini API settings
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

# Gemini model configuration
DEFAULT_MODELS = [
    "models/gemini-1.5-flash",      # Faster, lower quality
    "models/gemini-1.5-pro",        # Higher quality, slower
    "models/gemini-pro-vision",     # Fallback older model
]

# Server configurations
MAIN_PROXY_PORT = 5000
EXTENDED_PROXY_PORT = 3000

# Safety settings configuration
try:
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    # Set up safety settings with the new API format
    SAFETY_SETTINGS = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
except ImportError:
    # Fallback for older versions of the SDK
    SAFETY_SETTINGS = {
        "HARASSMENT": "BLOCK_NONE",
        "HATE": "BLOCK_NONE",
        "SEXUAL": "BLOCK_NONE",
        "DANGEROUS": "BLOCK_NONE",
    }

# Generation configuration
GENERATION_CONFIG = {
    "temperature": 0.7,
    "max_output_tokens": 8192,  # Increased for more detailed responses
    "top_p": 0.95,
    "top_k": 40,
}

# Swarm configuration
MAX_WORKERS = 4
MAX_ATTEMPTS = 3
DEFAULT_TEST_CMD = "python -m unittest discover"

# Logging configuration
LOG_LEVEL = "DEBUG"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# File paths
LOG_DIR = "logs"