#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
import sys
import json
import time
import random
import logging
import requests
import traceback
from typing import Dict, List, Any, Optional, Union, Tuple

# Web search and content tools
from duckduckgo_search import DDGS
import wikipedia
from pytrends.request import TrendReq
import feedparser
import nltk
import re
import bs4
from textblob import TextBlob
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor
import trafilatura

# File and system manipulation
import subprocess
import importlib
import glob

# Import our AI helper
from ai_helper import configure_genai, get_model, generate_content, get_response_text
from config import API_KEYS, LOG_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "flask_proxy_extended.log"))
    ]
)
logger = logging.getLogger("flask_proxy_extended")

# Initialize the Flask app
app = Flask(__name__)

# Key rotation
key_usage = {}

# Initialize NLTK for text processing
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
except Exception as e:
    logger.error(f"Error initializing NLTK: {e}")

# Helper Functions for Web Search and Content

def web_search(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Perform a web search using DuckDuckGo.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        
    Returns:
        List of search results (dicts with title, url, body)
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        logger.info(f"Web search found {len(results)} results for query: {query}")
        return results
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return []

def get_trending_topics(region: str = 'US') -> List[str]:
    """
    Get current trending topics from Google Trends.
    
    Args:
        region: Country code for regional trends
        
    Returns:
        List of trending topics
    """
    try:
        pytrend = TrendReq()
        trending_searches = pytrend.trending_searches(pn=region)
        return trending_searches[0].tolist()
    except Exception as e:
        logger.error(f"Error getting trending topics: {e}")
        return []

def fetch_news(topic: Optional[str] = None, feed_url: Optional[str] = None, max_items: int = 10) -> List[Dict[str, str]]:
    """
    Fetch news from RSS feeds.
    
    Args:
        topic: Topic to search for (optional)
        feed_url: RSS feed URL (optional)
        max_items: Maximum number of items to return
        
    Returns:
        List of news items
    """
    try:
        # Default to a general news feed if none provided
        actual_feed_url = "http://rss.cnn.com/rss/cnn_topstories.rss"
        if feed_url is not None:
            actual_feed_url = feed_url
        
        feed = feedparser.parse(actual_feed_url)
        items = []
        
        for entry in feed.entries[:max_items]:
            item = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "")
            }
            
            # If no topic filter or topic is found in title/summary
            if topic is None or (isinstance(topic, str) and 
                                (topic.lower() in item["title"].lower() or 
                                 topic.lower() in item["summary"].lower())):
                items.append(item)
                
        return items
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return []

def get_wikipedia_content(topic: str, sentences: int = 5) -> str:
    """
    Get content from Wikipedia on a given topic.
    
    Args:
        topic: The topic to search for
        sentences: Number of sentences to return
        
    Returns:
        Wikipedia content
    """
    try:
        # Search for the page
        search_results = wikipedia.search(topic)
        if not search_results:
            return f"No Wikipedia page found for {topic}"
        
        # Get the first matching page
        try:
            page = wikipedia.page(search_results[0], auto_suggest=False)
        except wikipedia.DisambiguationError as e:
            # If disambiguation page, take the first option
            page = wikipedia.page(e.options[0], auto_suggest=False)
        
        # Get a summary
        summary = wikipedia.summary(page.title, sentences=sentences)
        return f"Wikipedia - {page.title}:\n\n{summary}\n\nURL: {page.url}"
    except Exception as e:
        logger.error(f"Error getting Wikipedia content: {e}")
        return f"Error retrieving Wikipedia content: {str(e)}"

def fetch_url_content(url: str) -> str:
    """
    Fetch the raw content from a URL.
    
    Args:
        url: The URL to fetch
        
    Returns:
        Text content of the URL
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return f"Error fetching URL: {str(e)}"

def extract_text_from_html(html_content: str) -> str:
    """
    Extract meaningful text from HTML content using trafilatura.
    
    Args:
        html_content: HTML content
        
    Returns:
        Extracted text
    """
    try:
        extracted_text = trafilatura.extract(html_content)
        if extracted_text:
            return extracted_text
        else:
            # Fallback to BeautifulSoup if trafilatura fails
            soup = bs4.BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text
            text = soup.get_text()
            
            # Break into lines and remove leading/trailing space
            lines = (line.strip() for line in text.splitlines())
            
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return "Error extracting text from HTML"

def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze the sentiment of text using TextBlob.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dict with sentiment analysis
    """
    try:
        blob = TextBlob(text)
        # Get polarity and subjectivity values
        polarity = blob.sentiment.polarity if hasattr(blob.sentiment, 'polarity') else 0.0
        subjectivity = blob.sentiment.subjectivity if hasattr(blob.sentiment, 'subjectivity') else 0.0
        
        # Determine sentiment label
        if polarity > 0.1:
            label = "Positive"
        elif polarity < -0.1:
            label = "Negative"
        else:
            label = "Neutral"
        
        return {
            "sentiment": label,
            "polarity": float(polarity),
            "subjectivity": float(subjectivity)
        }
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return {"error": str(e), "sentiment": "Unknown", "polarity": 0.0, "subjectivity": 0.0}

def extract_keywords(text: str, num_keywords: int = 10) -> List[str]:
    """
    Extract the main keywords from text using NLTK.
    
    Args:
        text: Text to analyze
        num_keywords: Number of keywords to extract
        
    Returns:
        List of keywords
    """
    try:
        # Tokenize and convert to lowercase
        tokens = nltk.word_tokenize(text.lower())
        
        # Remove stopwords and punctuation
        stopwords = set(nltk.corpus.stopwords.words('english'))
        words = [word for word in tokens if word.isalnum() and word not in stopwords]
        
        # Count word frequency
        freq_dist = nltk.FreqDist(words)
        
        # Get the most common words
        keywords = [word for word, _ in freq_dist.most_common(num_keywords)]
        return keywords
    except Exception as e:
        logger.error(f"Error extracting keywords: {e}")
        return []

# System Functions

def execute_system_command(command: str) -> Dict[str, Any]:
    """
    Execute a system command safely.
    
    Args:
        command: The command to execute
        
    Returns:
        Dict with stdout, stderr, and return code
    """
    try:
        # List of allowed commands for safety
        allowed_prefixes = [
            "ls", "dir", "cd", "pwd", "echo", "cat", "head", "tail",
            "grep", "find", "wc", "date", "python", "pip", "jupyter",
            "mkdir", "touch", "rm", "cp", "mv"
        ]
        
        # Check if command is allowed
        if not any(command.strip().startswith(prefix) for prefix in allowed_prefixes):
            return {
                "stdout": "",
                "stderr": "Command not allowed for security reasons",
                "returncode": 1
            }
        
        # Execute command
        process = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # Timeout after 30 seconds
        )
        
        return {
            "stdout": process.stdout,
            "stderr": process.stderr,
            "returncode": process.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "Command timed out after 30 seconds",
            "returncode": 1
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Error executing command: {str(e)}",
            "returncode": 1
        }

def install_python_package(package_name: str) -> Dict[str, Any]:
    """
    Install a Python package using pip.
    
    Args:
        package_name: Name of the package to install
        
    Returns:
        Dict with success status and output/error message
    """
    try:
        # Check if package is in allowed list (basic data science and NLP packages)
        allowed_packages = [
            "numpy", "pandas", "matplotlib", "seaborn", "scikit-learn",
            "nltk", "textblob", "spacy", "gensim", "pytorch", "tensorflow", 
            "keras", "jupyter", "pytest", "black", "flake8", "mypy", 
            "requests", "beautifulsoup4", "flask", "django", "fastapi"
        ]
        
        # Strip version specifiers for checking
        base_package = package_name.split("==")[0].split(">=")[0].split("<=")[0]
        
        if base_package not in allowed_packages:
            return {
                "success": False,
                "message": f"Package {package_name} is not in the allowed list for security reasons"
            }
        
        # Install the package
        process = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            # Try to import the package to verify it was installed
            try:
                importlib.import_module(base_package)
                return {
                    "success": True,
                    "message": f"Successfully installed {package_name}"
                }
            except ImportError:
                return {
                    "success": True,
                    "message": f"Installed {package_name}, but import check failed. The module may have a different name than the package."
                }
        else:
            return {
                "success": False,
                "message": f"Failed to install {package_name}: {process.stderr}"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error installing package: {str(e)}"
        }

# File operations

def list_directory(path: str = ".") -> List[str]:
    """
    List files in a directory.
    
    Args:
        path: Directory path to list
        
    Returns:
        List of files
    """
    try:
        files = glob.glob(os.path.join(path, "*"))
        return sorted(files)
    except Exception as e:
        logger.error(f"Error listing directory {path}: {e}")
        return []

def read_file_content(filepath: str) -> str:
    """
    Read a file and return its contents.
    
    Args:
        filepath: Path to the file
        
    Returns:
        File content as string
    """
    try:
        if not os.path.exists(filepath):
            return f"File not found: {filepath}"
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
            content = file.read()
        return content
    except Exception as e:
        logger.error(f"Error reading file {filepath}: {e}")
        return f"Error reading file: {str(e)}"

def write_file_content(filepath: str, content: str) -> Dict[str, Any]:
    """
    Write content to a file.
    
    Args:
        filepath: Path to the file
        content: Content to write
        
    Returns:
        Dict with success status and message
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(content)
        
        return {
            "success": True,
            "message": f"Successfully wrote to {filepath}"
        }
    except Exception as e:
        logger.error(f"Error writing to file {filepath}: {e}")
        return {
            "success": False,
            "message": f"Error writing to file: {str(e)}"
        }

# Gemini API Functions

def get_api_key() -> str:
    """
    Get a random API key from the available keys.
    
    Returns:
        Random API key
    """
    # Filter out keys that are empty or None
    valid_keys = [key for key in API_KEYS if key]
    
    if not valid_keys:
        logger.error("No valid API keys available")
        return ""
    
    # Select a random key
    selected_key = random.choice(valid_keys)
    
    # Update usage count
    key_usage[selected_key] = key_usage.get(selected_key, 0) + 1
    
    return selected_key

def call_gemini_with_model_selection(
    prompt: str, 
    priority: str = "low", 
    verbose: bool = False,
    max_attempts: int = 5
) -> Dict[str, Any]:
    """
    Call the Gemini API with intelligent model selection based on priority.
    
    Args:
        prompt: The prompt to send to Gemini
        priority: Priority level (low or high)
        verbose: Whether to output verbose logs
        max_attempts: Maximum number of attempts to make
        
    Returns:
        Response from Gemini API
    """
    # Ensure we always return a dictionary, even in error cases
    result = {"response": "", "model_used": "none", "status": "error"}
    # Choose model based on priority
    # For high priority/complex tasks, use a more powerful model
    if priority.lower() == "high":
        primary_model = "models/gemini-1.5-pro"
        backup_model = "models/gemini-1.5-flash"
        model_description = "pro (complex reasoning)"
    else:
        primary_model = "models/gemini-1.5-flash"
        backup_model = "models/gemini-1.0-pro"
        model_description = "flash (faster response)"
    
    if verbose:
        logger.info(f"Task priority: {priority}, using {model_description} model")
        logger.info(f"Prompt: {prompt[:100]}...")
    
    # Try with the selected models
    for attempt in range(1, max_attempts + 1):
        api_key = get_api_key()
        if not api_key:
            return {
                "response": "Error: No valid API keys available",
                "model_used": "none",
                "status": "error"
            }
        
        # Configure the API
        configure_genai(api_key)
        
        # Choose model based on attempt number
        model_name = primary_model if attempt <= 3 else backup_model
        
        try:
            if verbose:
                logger.info(f"Attempt {attempt}/{max_attempts}: Using model {model_name}")
            
            model = get_model(model_name)
            
            # Set safety settings - allow more creative content
            safety_settings = {
                "HARASSMENT": "BLOCK_NONE",
                "HATE": "BLOCK_NONE",
                "SEXUALLY_EXPLICIT": "BLOCK_NONE",
                "DANGEROUS": "BLOCK_NONE"
            }
            
            # Set generation config for more consistent responses
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
            
            # Generate content
            response = generate_content(
                model=model,
                prompt=prompt,
                safety_settings=safety_settings,
                generation_config=generation_config
            )
            
            # Get the text from the response
            text = get_response_text(response)
            
            if verbose:
                logger.info(f"Successfully generated response with model {model_name}")
                logger.info(f"Response preview: {text[:100]}...")
            
            return {
                "response": text,
                "model_used": model_name,
                "status": "success"
            }
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error on attempt {attempt} with {model_name}: {error_message}")
            
            # If we've reached the maximum number of attempts, return the error
            if attempt == max_attempts:
                return {
                    "response": f"Error calling Gemini API: {error_message}",
                    "model_used": model_name,
                    "status": "error"
                }
            
            # Wait before trying again
            time.sleep(1)

# Flask Routes

@app.route('/')
def index():
    """Render the web interface for the Gemini proxy."""
    return render_template('index.html')

@app.route('/gemini', methods=['POST'])
def call_gemini():
    """
    Proxy endpoint for Gemini API calls with intelligent model selection.
    """
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return jsonify({"error": "No prompt provided"}), 400
        
        prompt = data['prompt']
        priority = data.get('priority', 'low')  # Default to low priority
        verbose = data.get('verbose', False)
        
        logger.info(f"Received request with priority={priority}, verbose={verbose}")
        logger.debug(f"Prompt: {prompt[:100]}...")
        
        result = call_gemini_with_model_selection(
            prompt=prompt,
            priority=priority,
            verbose=verbose
        )
        
        return jsonify(result)
    
    except Exception as e:
        error_message = f"Error processing request: {str(e)}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        return jsonify({"error": error_message, "status": "error"}), 500

@app.route('/web_search', methods=['POST'])
def web_search_endpoint():
    """Endpoint for web search."""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({"error": "No query provided"}), 400
        
        query = data['query']
        max_results = int(data.get('max_results', 10))
        
        logger.info(f"Web search request: {query}")
        
        results = web_search(query, max_results)
        
        return jsonify({
            "results": results,
            "count": len(results),
            "query": query
        })
    
    except Exception as e:
        error_message = f"Error processing web search: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/fetch_url', methods=['POST'])
def fetch_url_endpoint():
    """Endpoint for fetching URL content."""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({"error": "No URL provided"}), 400
        
        url = data['url']
        logger.info(f"Fetch URL request: {url}")
        
        content = fetch_url_content(url)
        
        return jsonify({
            "content": content,
            "url": url
        })
    
    except Exception as e:
        error_message = f"Error fetching URL: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/scrape_text', methods=['POST'])
def scrape_text_endpoint():
    """Endpoint for scraping text from a URL."""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({"error": "No URL provided"}), 400
        
        url = data['url']
        logger.info(f"Scrape text request: {url}")
        
        html_content = fetch_url_content(url)
        text_content = extract_text_from_html(html_content)
        
        # Extract keywords if requested
        extract_kw = data.get('extract_keywords', False)
        keywords = []
        if extract_kw:
            keywords = extract_keywords(text_content)
        
        # Analyze sentiment if requested
        analyze_sent = data.get('analyze_sentiment', False)
        sentiment = {}
        if analyze_sent:
            sentiment = analyze_sentiment(text_content)
        
        return jsonify({
            "url": url,
            "text": text_content,
            "length": len(text_content),
            "keywords": keywords,
            "sentiment": sentiment
        })
    
    except Exception as e:
        error_message = f"Error scraping text: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/wikipedia', methods=['POST'])
def wikipedia_endpoint():
    """Endpoint for fetching Wikipedia content."""
    try:
        data = request.get_json()
        
        if not data or 'topic' not in data:
            return jsonify({"error": "No topic provided"}), 400
        
        topic = data['topic']
        sentences = int(data.get('sentences', 5))
        
        logger.info(f"Wikipedia request: {topic}, sentences: {sentences}")
        
        content = get_wikipedia_content(topic, sentences)
        
        return jsonify({
            "topic": topic,
            "content": content
        })
    
    except Exception as e:
        error_message = f"Error fetching Wikipedia content: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/trends', methods=['GET'])
def trends_endpoint():
    """Endpoint for getting trending topics."""
    try:
        region = request.args.get('region', 'US')
        
        logger.info(f"Trends request for region: {region}")
        
        topics = get_trending_topics(region)
        
        return jsonify({
            "region": region,
            "trends": topics
        })
    
    except Exception as e:
        error_message = f"Error fetching trends: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/news', methods=['POST'])
def news_endpoint():
    """Endpoint for fetching news."""
    try:
        data = request.get_json() or {}
        
        topic = data.get('topic')
        feed_url = data.get('feed_url')
        max_items = int(data.get('max_items', 10))
        
        logger.info(f"News request: topic={topic}, feed={feed_url}, max_items={max_items}")
        
        news_items = fetch_news(topic, feed_url, max_items)
        
        return jsonify({
            "topic": topic,
            "feed_url": feed_url,
            "items": news_items,
            "count": len(news_items)
        })
    
    except Exception as e:
        error_message = f"Error fetching news: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/list_files', methods=['POST'])
def list_files_endpoint():
    """Endpoint for listing files."""
    try:
        data = request.get_json() or {}
        
        path = data.get('path', '.')
        
        logger.info(f"List files request for path: {path}")
        
        files = list_directory(path)
        
        return jsonify({
            "path": path,
            "files": files,
            "count": len(files)
        })
    
    except Exception as e:
        error_message = f"Error listing files: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/read_file', methods=['POST'])
def read_file_endpoint():
    """Endpoint for reading a file."""
    try:
        data = request.get_json()
        
        if not data or 'path' not in data:
            return jsonify({"error": "No file path provided"}), 400
        
        path = data['path']
        
        logger.info(f"Read file request for: {path}")
        
        content = read_file_content(path)
        
        return jsonify({
            "path": path,
            "content": content,
            "size": len(content)
        })
    
    except Exception as e:
        error_message = f"Error reading file: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/write_file', methods=['POST'])
def write_file_endpoint():
    """Endpoint for writing to a file."""
    try:
        data = request.get_json()
        
        if not data or 'path' not in data or 'content' not in data:
            return jsonify({"error": "Missing path or content"}), 400
        
        path = data['path']
        content = data['content']
        
        logger.info(f"Write file request for: {path}")
        
        result = write_file_content(path, content)
        
        return jsonify(result)
    
    except Exception as e:
        error_message = f"Error writing file: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/execute', methods=['POST'])
def execute_endpoint():
    """Endpoint for executing a system command."""
    try:
        data = request.get_json()
        
        if not data or 'command' not in data:
            return jsonify({"error": "No command provided"}), 400
        
        command = data['command']
        
        logger.info(f"Execute command request: {command}")
        
        result = execute_system_command(command)
        
        return jsonify(result)
    
    except Exception as e:
        error_message = f"Error executing command: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/install_package', methods=['POST'])
def install_package_endpoint():
    """Endpoint for installing a Python package."""
    try:
        data = request.get_json()
        
        if not data or 'package' not in data:
            return jsonify({"error": "No package name provided"}), 400
        
        package = data['package']
        
        logger.info(f"Install package request: {package}")
        
        result = install_python_package(package)
        
        return jsonify(result)
    
    except Exception as e:
        error_message = f"Error installing package: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/sentiment', methods=['POST'])
def sentiment_endpoint():
    """Endpoint for sentiment analysis."""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({"error": "No text provided"}), 400
        
        text = data['text']
        
        logger.info(f"Sentiment analysis request for text of length: {len(text)}")
        
        result = analyze_sentiment(text)
        
        return jsonify(result)
    
    except Exception as e:
        error_message = f"Error analyzing sentiment: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/keywords', methods=['POST'])
def keywords_endpoint():
    """Endpoint for keyword extraction."""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({"error": "No text provided"}), 400
        
        text = data['text']
        num_keywords = int(data.get('num_keywords', 10))
        
        logger.info(f"Keyword extraction request for text of length: {len(text)}")
        
        keywords = extract_keywords(text, num_keywords)
        
        return jsonify({
            "keywords": keywords,
            "count": len(keywords)
        })
    
    except Exception as e:
        error_message = f"Error extracting keywords: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Return anonymized API key usage statistics."""
    stats = {}
    for key, count in key_usage.items():
        # Only show the last 4 characters of the key for security
        key_id = key[-4:] if len(key) >= 4 else "****"
        stats[key_id] = count
    
    return jsonify(stats)

# Main function
if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Download NLTK data if needed
    try:
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)
    except:
        logger.warning("Could not download NLTK data")
    
    # Count valid API keys
    valid_keys = [key for key in API_KEYS if key]
    logger.info(f"Loaded {len(valid_keys)} API keys for rotation")
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=3000, debug=True)