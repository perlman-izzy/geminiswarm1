#!/usr/bin/env python3
import requests
import json
import time
import sys

BASE_URL = "http://localhost:5000"

def print_separator():
    print("\n" + "=" * 80 + "\n")

def test_api_endpoint(endpoint, data=None, method="POST"):
    url = f"{BASE_URL}/{endpoint}"
    print(f"Testing endpoint: {url}")
    print(f"Request data: {data}")
    
    if method == "POST":
        response = requests.post(url, json=data)
    else:
        response = requests.get(url, params=data)
    
    print(f"Status code: {response.status_code}")
    try:
        result = response.json()
        print(json.dumps(result, indent=2))
        return result
    except:
        print(f"Raw response: {response.text}")
        return None

def main():
    print("MULTI-CAPABILITY TEST SUITE")
    print_separator()
    
    # Step 1: Search for information about quantum computing
    print("STEP 1: Web search for quantum computing")
    search_results = test_api_endpoint("web_search", {"query": "quantum computing", "max_results": 3})
    print_separator()
    
    # Step 2: Get detailed information from Wikipedia
    print("STEP 2: Get Wikipedia info on quantum computing")
    wiki_results = test_api_endpoint("wikipedia", {"topic": "Quantum computing", "sentences": 7})
    print_separator()
    
    # Step 3: Generate insights based on the information
    prompt = f"""
    Based on the following information about quantum computing, explain the potential
    impact it might have on artificial intelligence and machine learning in the next decade:
    
    Web search results:
    {json.dumps(search_results, indent=2) if search_results else 'No results'}
    
    Wikipedia content:
    {wiki_results.get('content', 'Not available') if wiki_results else 'Not available'}
    
    Provide specific examples and potential applications.
    """
    
    print("STEP 3: Generate analysis with Gemini")
    print(f"Prompt: {prompt[:150]}...")
    analysis = test_api_endpoint("gemini", {"prompt": prompt, "priority": "high"})
    print_separator()
    
    # Step 4: Perform sentiment analysis on the response
    if analysis and 'response' in analysis:
        print("STEP 4: Analyze sentiment of generated content")
        sentiment = test_api_endpoint("sentiment", {"text": analysis['response']})
        print_separator()
        
        # Step 5: Extract keywords from the generated content
        print("STEP 5: Extract keywords from generated content")
        keywords = test_api_endpoint("keywords", {"text": analysis['response'], "num_keywords": 10})
        print_separator()

    print("MULTI-CAPABILITY TEST COMPLETE")

if __name__ == "__main__":
    main()
