"""
Gemini LLM implementation for SuperAGI, making direct calls to Google Gemini API.
"""
import json
import requests
import itertools
from typing import List, Dict, Union
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Assuming logger is correctly set up in this path.
from superagi_replit.lib.logger import logger
from superagi_replit.llms.base_llm import BaseLlm

# Constants from the original file (or sensible defaults)
MAX_RETRY_ATTEMPTS = 3
MIN_WAIT = 2  # seconds
MAX_WAIT = 20  # seconds

# --- Direct API Key Embedding ---
# Using a selection of 15 keys as provided by the user.
EMBEDDED_GEMINI_API_KEYS = [
    "AIzaSyA3IhGRt1--Dpa8RUWFp3thnMVsF8oSe2I", "AIzaSyBurTGhYgEzYnPQa0ig81B-YXdM2fwvnSs",
    "AIzaSyBWM9nF7YblOommwMjCq22Orj6Xwzn2YWQ", "AIzaSyDoMMy5cWL2bwzM6wO7-OHxRbjvF0Ulq0c",
    "AIzaSyBNl1AYLcbvhE3bgc8r8twjV1Ku4b4MCoA", "AIzaSyBp5hqJE5rfnEuTqKYNe33njm4cu7YeGok",
    "AIzaSyCKjsOFzWcIBAWy0qhX0cHDTVIYdbD-65o", "AIzaSyAWnjH8stitEDFiAf6_UlLNjvqZGdl1fOw",
    "AIzaSyB_4jcaNX0h-2UaavIPV97_jhcXImgEqIw", "AIzaSyDRwTG7X2dTXyDGElTePgoaETLskBHk82U",
    "AIzaSyC3VmL5v_CRgl5gyBS2j1EjYlIvQNrLrfM", "AIzaSyCOWe2MuROtQnaPKHy83APRlDZjZYfg6dc",
    "AIzaSyC4YnFQHATJ3epKXUJoz4syPO-TjqrkF5o", "AIzaSyDNrp__ft4Yx69DHE2wS4CaAk6ESrfAXjM",
    "AIzaSyCNRCCo5bKfvAPB7uSBxJ8dpui7Ior0ZFg"
    # Add more keys here from your list if desired, ensuring they are unique.
]

class GeminiProxy(BaseLlm): # Keeping class name for compatibility with existing SuperAGI code
    def __init__(self, model="gemini-1.5-pro", temperature=0.7, max_tokens=4096,
                 top_p=1.0, frequency_penalty=0, presence_penalty=0): # Args like frequency/presence_penalty are not directly used by Gemini
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p

        self.api_keys = EMBEDDED_GEMINI_API_KEYS
        if not self.api_keys:
            logger.error("CRITICAL: No API keys embedded for Gemini LLM.")
            raise ValueError("CRITICAL: No API keys embedded for Gemini LLM.")
        self.key_iterator = itertools.cycle(self.api_keys)
        self.base_gemini_url = "https://generativelanguage.googleapis.com/v1beta/models"
        logger.info(f"GeminiDirectClient initialized with {len(self.api_keys)} keys. First key ends with ...{self.api_keys[0][-4:] if self.api_keys else 'N/A'}")

    def get_source(self) -> str:
        return "gemini_direct"

    def get_model(self) -> str:
        return self.model

    def get_models(self) -> List[str]:
        # This list might need to be updated based on actual model availability with the keys.
        return ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest", "gemini-pro"]

    def verify_access_key(self) -> bool:
        return bool(self.api_keys) # Basic check; a true verification would ping the API.

    @retry(
        stop=stop_after_attempt(len(EMBEDDED_GEMINI_API_KEYS) * MAX_RETRY_ATTEMPTS if EMBEDDED_GEMINI_API_KEYS else MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=MIN_WAIT, max=MAX_WAIT),
        retry=retry_if_exception_type((requests.exceptions.RequestException, json.JSONDecodeError, ValueError)),
        reraise=True
    )
    def chat_completion(self, prompt: Union[str, List[Dict[str, str]]]) -> str:
        current_api_key = next(self.key_iterator)
        logger.info(f"Attempting Gemini API call with key ending ...{current_api_key[-4:]}")

        model_path = self.model if self.model.startswith("models/") else f"models/{self.model}"
        url = f"{self.base_gemini_url}/{model_path}:generateContent?key={current_api_key}"

        gemini_contents = []
        if isinstance(prompt, str):
            gemini_contents.append({"role": "user", "parts": [{"text": prompt}]})
        else:
            for message in prompt:
                role = message.get("role", "user").lower()
                gemini_role = "model" if role in ["assistant", "system"] else "user" # Map system/assistant to model
                gemini_contents.append({"role": gemini_role, "parts": [{"text": message.get("content", "")}]})

        # Ensure contents are not empty and have valid text
        valid_contents = [c for c in gemini_contents if c.get("parts") and c["parts"][0].get("text", "").strip()]
        if not valid_contents:
            logger.error("No valid content to send to Gemini after transformation. Original prompt was: %s", prompt)
            return "Error: No valid content derived from prompt to send to Gemini."

        payload = {
            "contents": valid_contents,
            "generationConfig": {
                "temperature": float(self.temperature), # Ensure correct type
                "maxOutputTokens": int(self.max_tokens), # Ensure correct type
                "topP": float(self.top_p) # Ensure correct type
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        }
        logger.debug(f"Sending payload to Gemini: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=120) # Increased timeout
            response.raise_for_status()

            result = response.json()
            logger.debug(f"Received response from Gemini: {json.dumps(result, indent=2)}")

            if "candidates" in result and result["candidates"]:
                candidate = result["candidates"][0]
                finish_reason = candidate.get("finishReason")

                if finish_reason == "SAFETY":
                    logger.warning(f"Gemini response filtered due to safety settings (key ...{current_api_key[-4:]}). Candidate: {candidate}")
                    # Even if blocked, sometimes there's partial content.
                    if candidate.get("content") and candidate["content"].get("parts") and candidate["content"]["parts"][0].get("text"):
                         return candidate["content"]["parts"][0].get("text")
                    return "Response blocked by Gemini due to safety settings. No content available."

                if "content" in candidate and "parts" in candidate["content"] and candidate["content"]["parts"]:
                    text_response = candidate["content"]["parts"][0].get("text", "")
                    if not text_response and finish_reason and finish_reason != "STOP":
                         logger.warning(f"Empty text from Gemini with finishReason: {finish_reason} (key ...{current_api_key[-4:]})")
                         return f"Received empty response from Gemini (finish reason: {finish_reason})."
                    logger.info(f"Successfully received response from Gemini (key ...{current_api_key[-4:]})")
                    return text_response
                else:
                    logger.error(f"Unexpected Gemini response structure (no content/parts) (key ...{current_api_key[-4:]}): {result}")
                    raise ValueError(f"Unexpected Gemini response structure (no content/parts) for key ...{current_api_key[-4:]}")

            elif "error" in result:
                error_details = result["error"]
                error_message = error_details.get('message', str(error_details))
                error_code = error_details.get('code')
                logger.error(f"Error from Gemini API (key ...{current_api_key[-4:]}): {error_message} (Code: {error_code})")
                if error_code in [400, 401, 403, 429]:
                    raise ValueError(f"Gemini API error (key ...{current_api_key[-4:]}, code {error_code}): {error_message}") # Retry for these
                return f"Error from Gemini API: {error_message}" # Don't retry for others
            else:
                logger.error(f"No candidates or error field in Gemini response (key ...{current_api_key[-4:]}): {result}")
                raise ValueError(f"No candidates or error field in Gemini response for key ...{current_api_key[-4:]}")

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error calling Gemini API (key ...{current_api_key[-4:]}): Status {e.response.status_code}, Response: {e.response.text}")
            if e.response.status_code in [400, 401, 403, 429]: # Likely key-related or quota
                raise ValueError(f"HTTP Error {e.response.status_code} (key ...{current_api_key[-4:]}). Retrying.")
            raise # Reraise other HTTP errors
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error calling Gemini API (key ...{current_api_key[-4:]}): {str(e)}")
            raise # Retry for network issues
        except Exception as e:
            logger.error(f"Unexpected error in Gemini chat_completion (key ...{current_api_key[-4:]}): {str(e)} - {traceback.format_exc()}")
            raise ValueError(f"Unexpected error: {str(e)}")
