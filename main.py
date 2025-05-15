#!/usr/bin/env python3
"""
Main entry point for the Multi-Agent Gemini AI System
Incorporates both the main interface and extended functionality
"""
import os
import sys
import logging
import random
import requests
import json
import traceback
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from flask import Flask, request, jsonify, render_template, redirect, url_for

# Import from config
from config import (
    LOG_DIR, API_KEYS, GEMINI_API_KEYS, GEMINI_MODELS, 
    OPENAI_MODELS, ANTHROPIC_MODELS,
    OPENAI_API_KEY, ANTHROPIC_API_KEY
)

# For extended proxy functionality
import google.generativeai as genai

# Import other provider helpers (optional fallbacks)
from openai_helper import generate_with_openai
from anthropic_helper import generate_with_anthropic
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
import subprocess
import importlib
import glob

# Import our AI helper
from ai_helper import configure_genai, get_model, generate_content, get_response_text, list_available_models

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

# Initialize NLTK for text processing
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
except Exception as e:
    logger.error(f"Error initializing NLTK: {e}")

# Create the Flask app
app = Flask(__name__)

# Key rotation tracking
key_usage = {}

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
    gemini_available = len([k for k in GEMINI_API_KEYS if k]) > 0
    openai_available = bool(OPENAI_API_KEY)
    anthropic_available = bool(ANTHROPIC_API_KEY)
    
    return jsonify({
        "status": "ok",
        "api_keys_available": {
            "gemini": len([k for k in GEMINI_API_KEYS if k]),
            "openai": openai_available,
            "anthropic": anthropic_available
        },
        "services": {
            "gemini": gemini_available,
            "openai": openai_available,
            "anthropic": anthropic_available,
            "web_search": True,
            "wikipedia": True,
            "news": True,
            "trends": True,
            "file_operations": True,
            "text_analysis": True
        }
    })

@app.route('/gemini', methods=['POST'])
def call_gemini():
    """
    Proxy endpoint for Gemini API calls with intelligent model selection.
    """
    try:
        data = request.get_json()
        
        if not data or "prompt" not in data:
            return jsonify({"error": "Missing prompt in request"}), 400
        
        prompt = data.get("prompt", "")
        priority = data.get("priority", "low")
        verbose = data.get("verbose", False)
        
        if not prompt.strip():
            return jsonify({"error": "Empty prompt"}), 400
        
        # Call Gemini with model selection
        result = call_gemini_with_model_selection(prompt, priority, verbose)
        
        if result["status"] == "success":
            return jsonify({
                "response": result["response"],
                "model_used": result["model_used"]
            })
        else:
            return jsonify({"error": result["response"]}), 500
            
    except Exception as e:
        logger.error(f"Error in Gemini endpoint: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/web_search', methods=['POST'])
def web_search_endpoint():
    """Endpoint for web search."""
    try:
        data = request.get_json()
        query = data.get("query", "")
        max_results = int(data.get("max_results", 10))
        
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400
        
        results = web_search(query, max_results)
        return jsonify({"results": results})
    
    except Exception as e:
        logger.error(f"Error in web search endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/fetch_url', methods=['POST'])
def fetch_url_endpoint():
    """Endpoint for fetching URL content."""
    try:
        data = request.get_json()
        url = data.get("url", "")
        
        if not url:
            return jsonify({"error": "URL parameter is required"}), 400
        
        content = fetch_url_content(url)
        return jsonify({"content": content})
    
    except Exception as e:
        logger.error(f"Error in fetch URL endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/scrape_text', methods=['POST'])
def scrape_text_endpoint():
    """Endpoint for scraping text from a URL."""
    try:
        data = request.get_json()
        url = data.get("url", "")
        
        if not url:
            return jsonify({"error": "URL parameter is required"}), 400
        
        # First fetch the raw content
        html_content = fetch_url_content(url)
        
        # Then extract the text
        extracted_text = extract_text_from_html(html_content)
        
        return jsonify({
            "url": url,
            "text": extracted_text
        })
    
    except Exception as e:
        logger.error(f"Error in scrape text endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/wikipedia', methods=['POST'])
def wikipedia_endpoint():
    """Endpoint for fetching Wikipedia content."""
    try:
        data = request.get_json()
        topic = data.get("topic", "")
        sentences = int(data.get("sentences", 5))
        
        if not topic:
            return jsonify({"error": "Topic parameter is required"}), 400
        
        content = get_wikipedia_content(topic, sentences)
        return jsonify({"content": content})
    
    except Exception as e:
        logger.error(f"Error in Wikipedia endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/trends', methods=['GET'])
def trends_endpoint():
    """Endpoint for getting trending topics."""
    try:
        region = request.args.get("region", "US")
        trending = get_trending_topics(region)
        return jsonify({"trends": trending, "region": region})
    
    except Exception as e:
        logger.error(f"Error in trends endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/news', methods=['POST'])
def news_endpoint():
    """Endpoint for fetching news."""
    try:
        data = request.get_json()
        topic = data.get("topic")
        feed_url = data.get("feed_url")
        max_items = int(data.get("max_items", 10))
        
        news_items = fetch_news(topic, feed_url, max_items)
        return jsonify({"news": news_items})
    
    except Exception as e:
        logger.error(f"Error in news endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/list_files', methods=['POST'])
def list_files_endpoint():
    """Endpoint for listing files."""
    try:
        data = request.get_json()
        path = data.get("path", ".")
        
        files = list_directory(path)
        return jsonify({"files": files})
    
    except Exception as e:
        logger.error(f"Error in list_files endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/read_file', methods=['POST'])
def read_file_endpoint():
    """Endpoint for reading a file."""
    try:
        data = request.get_json()
        filepath = data.get("filepath", "")
        
        if not filepath:
            return jsonify({"error": "Filepath parameter is required"}), 400
        
        content = read_file_content(filepath)
        return jsonify({"content": content})
    
    except Exception as e:
        logger.error(f"Error in read_file endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/write_file', methods=['POST'])
def write_file_endpoint():
    """Endpoint for writing to a file."""
    try:
        data = request.get_json()
        filepath = data.get("filepath", "")
        content = data.get("content", "")
        
        if not filepath:
            return jsonify({"error": "Filepath parameter is required"}), 400
        
        result = write_file_content(filepath, content)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in write_file endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/sentiment', methods=['POST'])
def sentiment_endpoint():
    """Endpoint for sentiment analysis."""
    try:
        data = request.get_json()
        text = data.get("text", "")
        
        if not text:
            return jsonify({"error": "Text parameter is required"}), 400
        
        sentiment = analyze_sentiment(text)
        return jsonify(sentiment)
    
    except Exception as e:
        logger.error(f"Error in sentiment endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/keywords', methods=['POST'])
def keywords_endpoint():
    """Endpoint for keyword extraction."""
    try:
        data = request.get_json()
        text = data.get("text", "")
        num_keywords = int(data.get("num_keywords", 10))
        
        if not text:
            return jsonify({"error": "Text parameter is required"}), 400
        
        keywords = extract_keywords(text, num_keywords)
        return jsonify({"keywords": keywords})
    
    except Exception as e:
        logger.error(f"Error in keywords endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/docs')
def docs():
    """Render the documentation page."""
    return render_template('index.html')

@app.route('/job_application')
def job_application():
    """Render the job application form page."""
    return render_template('job_application.html')

@app.route('/task_completion')
def task_completion():
    """Render the task completion testing page."""
    return render_template('task_completion.html')

@app.route('/run_task', methods=['POST'])
def run_task():
    """Run a task and return the results."""
    try:
        data = request.get_json()
        task_type = data.get('task_type', 'general')
        query = data.get('query', '')
        max_iterations = int(data.get('max_iterations', 10))
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
            
        # Import task_manager here to avoid circular imports
        import task_manager
        
        # Run the task
        result = task_manager.run_task(task_type, query, max_iterations)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error running task: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/list_results')
def list_results():
    """List all saved task results."""
    try:
        # Import task_manager here to avoid circular imports
        import task_manager
        
        # Get the list of results
        results = task_manager.list_saved_results()
        
        return jsonify({"results": results})
    except Exception as e:
        logger.error(f"Error listing results: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_result/<filename>')
def get_result(filename):
    """Get a specific task result."""
    try:
        # Import task_manager here to avoid circular imports
        import task_manager
        
        # Get the result content
        content = task_manager.get_result_content(filename)
        
        return jsonify(content)
    except Exception as e:
        logger.error(f"Error getting result: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/auto-fill-form', methods=['POST'])
def auto_fill_form():
    """
    Auto-fill a job application form using AI analysis of a resume.
    """
    try:
        data = request.get_json()
        specific_job_title = data.get("jobTitle")
        
        # This is the resume content for testing - in a real application,
        # this would be loaded from a user-uploaded file or a database
        resume_content = """
William White

50 5th Ave
San Francisco, CA
(310) 867-5603
billywhitemusic@gmail.com

EXPERIENCE

California Conservatory of Music, Redwood City, CA  — Studio Piano Teacher  (Sep. 2023 - Jun 2024)
• Created and implemented individual piano curricula for students aged 6-17
Supervisor: Chris Mallettinfo@thecaliforniaconservatory.com

R.E.S.P.E.C.T : The Aretha Franklin Musical, National Tour Music Director (November 2023 - March 2023)
Conducted 9 musicians, coordinated rehearsals, handled personnel and logistics issues, played keyboard 1, and created musical score for successful touring musical
Supervisor: Jim Lanahan
https://www.jimlanahan.com/contact

Hooper Avenue Elementary, Los Angeles, CA — Classroom Music Teacher (Sep-Jan 2018)
• Designed and implemented culturally-relevant curriculum focused primarily on Latin/Latin-American music for grades 3-5.  Received extremely positive feedback from students, teachers and parents
Special Ed Teacher: Dorene Scala, dorene64@gmail.com; 5th Grade Teacher: Jose Perdomo, jap1474@lausd.net

EDUCATION
University of California, Los Angeles –  B.A., Ethnomusicology(2000-2005)
San Francisco State University, San Francisco, CA - M.A. Composition(Jan 2020-ongoing)

LANGUAGES
English, French (fluent), Spanish (intermediate), Hebrew (intermediate), Japanese (beginner)

SKILLS
Music (piano, percussion, trombone, drums, voice, orchestration, arrangement, theory, production, composition)
Lesson planning/curriculum design
Technology (audio, signal processing, python, ML, AI)
Soft skills: listening, making others feel heard and empowered

AWARDS
- Education Through Music Fellowship (2009)
- UCLA Gluck Fellowship (2005)
- Martin Feldman Award (2000-2005)
- David A. Abell Jazz Award (2000-2005)
- Duke Ellington Jazz Award (2000-2005)
- CMEA Command Performance (1996-2000)
- Honorarium – New Journey Baptist Church (2009) (as Music Minister)
- Mensa Member, Los Angeles Chapter (2018)
*Music credits listed separately
        """
        
        # Define the form fields and options
        form_fields = {
            "jobTitle": {
                "label": "Job Title",
                "type": "text",
                "id": "jobTitle",
                "required": True
            },
            "company": {
                "label": "Company",
                "type": "text",
                "id": "company",
                "required": True
            },
            "location": {
                "label": "Location",
                "type": "text",
                "id": "location",
                "required": False
            },
            "startDate": {
                "label": "Start Date",
                "type": "date",
                "id": "startDate",
                "required": True
            },
            "endDate": {
                "label": "End Date",
                "type": "date",
                "id": "endDate",
                "required": False
            },
            "currentlyWork": {
                "label": "I currently work here",
                "type": "checkbox",
                "id": "currentlyWork",
                "required": False
            },
            "description": {
                "label": "Description",
                "type": "textarea",
                "id": "description",
                "required": True
            },
            "skills": {
                "label": "Skills used",
                "type": "multi-select",
                "id": "skills",
                "required": False,
                "options": ["Teaching", "Curriculum Development", "Piano", "Music Theory", 
                           "Orchestration", "Conducting", "Management", "Leadership"]
            },
            "referenceContact": {
                "label": "Reference Contact Information",
                "type": "text",
                "id": "referenceContact",
                "required": False
            }
        }
        
        # Create a prompt for the AI system
        example_json = '''{
          "jobTitle": "Studio Piano Teacher",
          "company": "California Conservatory of Music",
          "location": "Redwood City, CA",
          "startDate": "2023-09-01",
          "endDate": "2024-06-30",
          "currentlyWork": false,
          "description": "Created and implemented individual piano curricula for students aged 6-17.",
          "skills": ["Teaching", "Piano", "Curriculum Development", "Music Theory"],
          "referenceContact": "Chris Mallett, info@thecaliforniaconservatory.com"
        }'''
        
        job_instruction = "Please fill out the form for the job titled '" + str(specific_job_title) + "'." if specific_job_title else "Please fill out the form for the most recent job experience."
        
        prompt = f"""
        Task: Analyze the resume below and extract the most appropriate information to fill out a job application form.
        
        RESUME:
        {resume_content}
        
        FORM FIELDS TO FILL:
        {json.dumps(form_fields, indent=2)}
        
        {job_instruction}
        
        Important instructions:
        1. For date fields, use the format YYYY-MM-DD (e.g., 2023-09-01).
        2. For currentlyWork, if the job has an end date that is the current month and year or doesn't have an end date, set it to true.
        3. For description, include key responsibilities and achievements from the resume.
        4. For skills, select all applicable skills from the provided options that match the person's experience.
        5. For referenceContact, use supervisor information if available.
        
        Return your answer in valid JSON format with field names matching the form field IDs. Example:
        {example_json}
        """
        
        # Call the Gemini API to analyze the resume and fill the form
        result = call_gemini_with_model_selection(prompt, "high", True)
        
        if result["status"] == "success":
            response_text = result["response"]
            
            # Try to extract JSON from the response text
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    form_data = json.loads(json_match.group(0))
                else:
                    # If we can't find JSON pattern, try parsing the whole response
                    form_data = json.loads(response_text)
                
                # Add model information for logging/tracking
                form_data["_model_used"] = result["model_used"]
                
                return jsonify(form_data)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON from response: {e}")
                logger.debug(f"Response text: {response_text}")
                return jsonify({
                    "error": "Failed to parse form data from AI response",
                    "_model_used": result["model_used"],
                    "_raw_response": response_text
                }), 500
        else:
            return jsonify({"error": result["response"]}), 500
            
    except Exception as e:
        logger.error(f"Error in auto-fill form endpoint: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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
        # Use a simple implementation to avoid TextBlob property access issues
        blob = TextBlob(text)
        
        # Manual access to avoid property access errors
        # The sentiment attribute is actually a namedtuple with polarity and subjectivity
        polarity = 0.0
        subjectivity = 0.0
        
        try:
            # Try different methods for accessing the sentiment values
            polarity = float(blob.sentiment.polarity)
            subjectivity = float(blob.sentiment.subjectivity)
        except (AttributeError, TypeError):
            try:
                # Alternative: directly use the __dict__ method
                sentiment_data = blob.sentiment
                if hasattr(sentiment_data, "__dict__"):
                    polarity = float(sentiment_data.__dict__.get("polarity", 0.0))
                    subjectivity = float(sentiment_data.__dict__.get("subjectivity", 0.0))
            except Exception:
                # Last resort: implement a simple sentiment analyzer ourselves
                # Count positive and negative words
                positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic", 
                                 "terrific", "outstanding", "superb", "awesome", "brilliant"]
                negative_words = ["bad", "terrible", "awful", "horrible", "poor", "disappointing", 
                                 "dreadful", "appalling", "atrocious", "abysmal"]
                
                words = text.lower().split()
                positive_count = sum(1 for word in words if word in positive_words)
                negative_count = sum(1 for word in words if word in negative_words)
                
                total_words = len(words) if words else 1  # Avoid division by zero
                
                # Simple calculation of polarity and subjectivity
                polarity = (positive_count - negative_count) / total_words if total_words > 0 else 0
                subjectivity = (positive_count + negative_count) / total_words if total_words > 0 else 0
        
        # Determine sentiment label
        if polarity > 0.1:
            label = "Positive"
        elif polarity < -0.1:
            label = "Negative"
        else:
            label = "Neutral"
        
        return {
            "sentiment": label,
            "polarity": polarity,
            "subjectivity": subjectivity
        }
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return {"error": str(e), "sentiment": "Unknown", "polarity": 0.0, "subjectivity": 0.0}

def extract_keywords(text: str, num_keywords: int = 10) -> List[str]:
    """
    Extract the main keywords from text using basic word frequency.
    
    Args:
        text: Text to analyze
        num_keywords: Number of keywords to extract
        
    Returns:
        List of keywords
    """
    try:
        # First, try to use NLTK if available
        try:
            # Make sure required NLTK data is downloaded
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            
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
            
        except Exception as nltk_error:
            logger.warning(f"NLTK keyword extraction failed: {nltk_error}. Using fallback method.")
            
            # Fallback to a basic implementation if NLTK fails
            # Define basic English stopwords
            basic_stopwords = set([
                'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
                'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 
                'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
                'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them',
                'their', 'theirs', 'themselves', 'this', 'that', 'these', 'those', 'am',
                'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
                'having', 'do', 'does', 'did', 'doing', 'would', 'should', 'could', 'ought',
                'i\'m', 'you\'re', 'he\'s', 'she\'s', 'it\'s', 'we\'re', 'they\'re', 'i\'ve',
                'you\'ve', 'we\'ve', 'they\'ve', 'i\'d', 'you\'d', 'he\'d', 'she\'d', 'we\'d',
                'they\'d', 'i\'ll', 'you\'ll', 'he\'ll', 'she\'ll', 'we\'ll', 'they\'ll',
                'isn\'t', 'aren\'t', 'wasn\'t', 'weren\'t', 'hasn\'t', 'haven\'t', 'hadn\'t',
                'doesn\'t', 'don\'t', 'didn\'t', 'won\'t', 'wouldn\'t', 'shan\'t', 'shouldn\'t',
                'can\'t', 'cannot', 'couldn\'t', 'mustn\'t', 'let\'s', 'that\'s', 'who\'s',
                'what\'s', 'here\'s', 'there\'s', 'when\'s', 'where\'s', 'why\'s', 'how\'s',
                'for', 'of', 'to', 'in', 'on', 'at', 'by', 'with', 'about', 'against',
                'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
                'from', 'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further',
                'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any',
                'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
                'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very'
            ])
            
            # Simple tokenization (split by whitespace and remove punctuation)
            words = []
            for word in text.lower().split():
                # Remove punctuation from the word
                word = ''.join(c for c in word if c.isalnum())
                if word and word not in basic_stopwords:
                    words.append(word)
            
            # Count word frequency using a dictionary
            word_freq = {}
            for word in words:
                if word in word_freq:
                    word_freq[word] += 1
                else:
                    word_freq[word] = 1
            
            # Sort by frequency and get top words
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            keywords = [word for word, _ in sorted_words[:num_keywords]]
            return keywords
            
    except Exception as e:
        logger.error(f"Error extracting keywords: {e}")
        return []

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

# Cache for available models to avoid frequent API calls
_available_models_cache = []
_last_model_check_time = 0
_MODEL_CACHE_TTL = 3600  # Cache TTL in seconds (1 hour)

def get_available_models(api_key: str, verbose: bool = False) -> List[str]:
    """
    Get a list of available Gemini models by querying the API directly.
    Uses caching to avoid frequent API calls.
    
    Args:
        api_key: API key to use for the request
        verbose: Whether to output verbose logs
        
    Returns:
        List of available model names
    """
    global _available_models_cache, _last_model_check_time
    
    current_time = time.time()
    
    # If cache is valid, use it
    if (_available_models_cache and 
        current_time - _last_model_check_time < _MODEL_CACHE_TTL):
        if verbose:
            logger.info(f"Using cached model list ({len(_available_models_cache)} models)")
        return _available_models_cache
    
    # Otherwise, refresh the cache
    if verbose:
        logger.info("Refreshing available models list from API")
    
    try:
        # Configure the GenAI client with the API key
        configure_genai(api_key)
        
        # Get the available models using the helper function
        model_info = list_available_models()
        
        # Extract model names
        model_names = [info["name"] for info in model_info]
        
        if verbose:
            logger.info(f"Found {len(model_names)} models via API")
            for name in model_names:
                logger.info(f"  - {name}")
        
        # Update cache
        _available_models_cache = model_names
        _last_model_check_time = current_time
        
        return model_names
    
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        
        # If cache exists, use it even if expired
        if _available_models_cache:
            logger.warning("Using expired model cache due to API error")
            return _available_models_cache
        
        # Otherwise, return standard model names from config
        logger.warning("Using fallback model list from configuration")
        return list(set(GEMINI_MODELS.values()))

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
    
    # Get an API key
    api_key = get_api_key()
    if not api_key:
        result["response"] = "No valid API key available"
        return result
    
    # Get available models directly from the API
    available_models = get_available_models(api_key, verbose)
    
    # Filter available models into tiers
    pro_models = []
    flash_models = []
    fallback_models = []
    
    # Helper function to check if model matches patterns
    def model_matches(model: str, patterns: List[str]) -> bool:
        return any(pattern in model.lower() for pattern in patterns)
    
    # Categorize available models
    for model in available_models:
        model_lower = model.lower()
        
        # Use model name patterns to categorize
        if "gemini-1.5-pro" in model_lower and "vision" not in model_lower:
            pro_models.append(model)
        elif "gemini-1.5-flash" in model_lower:
            flash_models.append(model)
        elif "gemini-1.0" in model_lower or "vision" in model_lower:
            fallback_models.append(model)
    
    if verbose:
        logger.info(f"Available API models - Pro: {len(pro_models)}, Flash: {len(flash_models)}, Fallback: {len(fallback_models)}")
    
    # Initialize the model list
    models_to_try = []
    
    # For high priority tasks, try pro models first, then flash, then fallbacks
    if priority.lower() == "high":
        models_to_try.extend(pro_models)
        models_to_try.extend(flash_models)
        models_to_try.extend(fallback_models)
    else:
        # For regular tasks, try flash models first, then pro, then fallbacks
        models_to_try.extend(flash_models)
        models_to_try.extend(pro_models)
        models_to_try.extend(fallback_models)
    
    # Remove any duplicates while preserving order
    models_to_try = list(dict.fromkeys(models_to_try))
    
    # If no models found from API, fall back to configured models
    if not models_to_try:
        logger.warning("No available models from API, falling back to configured models")
        
        # Use configured models
        configured_models = list(set(GEMINI_MODELS.values()))
        if verbose:
            logger.info(f"Using {len(configured_models)} configured models")
        
        models_to_try.extend(configured_models)
    
    # If still no models, return an error
    if not models_to_try:
        result["response"] = "No valid models configured or available"
        return result
        
    # We already have an API key from earlier in the function
    
    # Configure the GenAI client
    configure_genai(api_key)
    
    # Try models in order until we get a valid response
    for i, model_name in enumerate(models_to_try):
        # Skip any None models
        if not model_name:
            continue
            
        attempt = 0
        while attempt < max_attempts:
            try:
                if verbose:
                    logger.info(f"Trying model {model_name}, attempt {attempt+1}/{max_attempts}")
                
                # Get the generative model (model_name is guaranteed to be a string at this point)
                model = get_model(model_name)
                
                # Generate content
                response = generate_content(
                    model, 
                    prompt,
                    safety_settings={
                        "HARASSMENT": "BLOCK_NONE",
                        "HATE": "BLOCK_NONE",
                        "SEXUALLY_EXPLICIT": "BLOCK_NONE",
                        "DANGEROUS": "BLOCK_NONE"
                    },
                    generation_config={
                        "temperature": 0.7,
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": 8192,
                    }
                )
                
                # Extract text from response
                text = get_response_text(response)
                
                # Return the result
                result = {
                    "response": text,
                    "model_used": model_name,
                    "status": "success"
                }
                
                # Successfully received response
                return result
                
            except Exception as e:
                attempt += 1
                error_msg = str(e)
                if verbose:
                    logger.error(f"Error with model {model_name}, attempt {attempt}: {error_msg}")
                
                # If we can't connect, switch models immediately
                if "Failed to connect" in error_msg or "Could not connect" in error_msg:
                    break
                
                # If we're rate limited or quota exceeded, try another key
                if "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                    api_key = get_api_key()
                    if api_key:
                        configure_genai(api_key)
                        continue
                    else:
                        # No more keys to try
                        break
                
                # Other errors, sleep and retry
                time.sleep(1)  # Sleep to prevent overloading the API
    
    # If all Gemini models failed, try OpenAI fallback
    if OPENAI_API_KEY:
        logger.info("All Gemini models failed, trying OpenAI fallback")
        try:
            # Try OpenAI with appropriate model based on priority
            openai_model = OPENAI_MODELS["primary"] if priority.lower() == "high" else OPENAI_MODELS["economy"]
            openai_result = generate_with_openai(
                prompt=prompt,
                model_name=openai_model,
                temperature=0.7,
                max_tokens=4096
            )
            
            if openai_result["status"] == "success":
                logger.info(f"Successfully generated content with OpenAI {openai_model}")
                return openai_result
            else:
                logger.warning(f"OpenAI fallback failed: {openai_result['response']}")
                
        except Exception as e:
            logger.error(f"Error during OpenAI fallback: {e}")
    
    # If OpenAI failed or isn't configured, try Anthropic fallback
    if ANTHROPIC_API_KEY:
        logger.info("Trying Anthropic fallback")
        try:
            # Try Anthropic with appropriate model based on priority
            anthropic_model = ANTHROPIC_MODELS["primary"] if priority.lower() == "high" else ANTHROPIC_MODELS["economy"]
            anthropic_result = generate_with_anthropic(
                prompt=prompt,
                model_name=anthropic_model,
                temperature=0.7,
                max_tokens=4096
            )
            
            if anthropic_result["status"] == "success":
                logger.info(f"Successfully generated content with Anthropic {anthropic_model}")
                return anthropic_result
            else:
                logger.warning(f"Anthropic fallback failed: {anthropic_result['response']}")
                
        except Exception as e:
            logger.error(f"Error during Anthropic fallback: {e}")
    
    # If we reach here, all providers and models failed
    result["response"] = "Failed to get a response from all available providers (Gemini, OpenAI, Anthropic)"
    return result

@app.route('/proxy')
def proxy_redirect():
    """Redirect to the API documentation page."""
    return redirect(url_for('index'))

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
    gemini_keys_count = len([k for k in GEMINI_API_KEYS if k])
    if gemini_keys_count == 0:
        logger.warning("No Gemini API keys available! Please set GOOGLE_API_KEY1, GOOGLE_API_KEY2, GOOGLE_API_KEY3, or GEMINI_API_KEY")
    else:
        logger.info(f"Found {gemini_keys_count} Gemini API keys")
        
    # Check other provider keys (optional)
    if OPENAI_API_KEY:
        logger.info("OpenAI API key available for fallback")
    if ANTHROPIC_API_KEY:
        logger.info("Anthropic API key available for fallback")
    
    # Start the Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)