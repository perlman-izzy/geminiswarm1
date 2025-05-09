#!/usr/bin/env python3
"""
Demo script to show how the autonomous researcher analyzes content
"""

import requests
import json
import sys

def scrape_url(url):
    """Scrape content from a URL using the proxy server"""
    response = requests.post(
        "http://localhost:5000/scrape_text",
        json={"url": url},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        return response.json().get("text", "")
    return ""

def analyze_content(content, query):
    """Analyze content in the context of a query"""
    prompt = f"""
    Analyze the following text content from a web page in the context of this query: "{query}"
    
    CONTENT:
    {content[:4000]}
    
    Extract the following information:
    1. Venue names mentioned (music venues with pianos)
    2. Features of these venues
    3. Locations/addresses where provided
    4. Key facts about piano bars in San Francisco
    
    Format your response as a JSON object with these keys:
    {{
        "venue_names": ["name1", "name2", ...],
        "features": ["feature1", "feature2", ...],
        "locations": ["location1", "location2", ...],
        "key_facts": ["fact1", "fact2", ...]
    }}
    
    Only include information that is explicitly found in the provided content.
    """
    
    response = requests.post(
        "http://localhost:5000/gemini",
        json={"prompt": prompt, "priority": "high"},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        if "response" in result:
            # Try to extract JSON from the response
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', result["response"])
                if json_match:
                    analysis = json.loads(json_match.group(0))
                    return analysis
            except Exception as e:
                print(f"Error extracting analysis JSON: {e}")
                return {"error": str(e), "raw_response": result.get("response", "")}
    
    return {"error": "Failed to analyze content"}

def main():
    # Example usage
    url = "https://www.discoverwalks.com/blog/san-francisco/10-best-piano-bars-in-san-francisco/"
    query = "Find piano bars in San Francisco"
    
    print(f"Scraping URL: {url}")
    content = scrape_url(url)
    
    if content:
        print("\nContent Preview (first 300 characters):")
        print("-" * 80)
        print(content[:300])
        print("-" * 80)
        
        print("\nAnalyzing content...")
        analysis = analyze_content(content, query)
        
        print("\nAnalysis Results:")
        print("-" * 80)
        print(json.dumps(analysis, indent=2))
        print("-" * 80)
    else:
        print("Failed to scrape content from URL")

if __name__ == "__main__":
    main()