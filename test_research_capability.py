#!/usr/bin/env python3
"""
Test script for evaluating the research capabilities of our multi-agent system.
This script tests the integration of web search, Wikipedia, and AI analysis.
"""
import requests
import time
import json
import sys
import os
from typing import Dict, Any, List, Optional

# Define endpoints
BASE_URL = "http://localhost:5000"
WEB_SEARCH_URL = f"{BASE_URL}/web_search"
WIKIPEDIA_URL = f"{BASE_URL}/wikipedia"
GEMINI_URL = f"{BASE_URL}/gemini"

# Test topics for research
RESEARCH_TOPICS = [
    "quantum computing advances",
    "renewable energy technologies",
    "artificial intelligence ethics",
    "autonomous vehicle technology",
    "blockchain in supply chain",
]

def get_web_search_results(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Perform a web search using the system's API.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        
    Returns:
        List of search results
    """
    try:
        response = requests.post(
            WEB_SEARCH_URL,
            json={"query": query, "max_results": max_results},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
        else:
            print(f"Error in web search: {response.status_code} - {response.text}")
            return []
    
    except Exception as e:
        print(f"Exception in web search: {e}")
        return []

def get_wikipedia_content(topic: str, sentences: int = 3) -> str:
    """
    Get Wikipedia content using the system's API.
    
    Args:
        topic: Topic to search for
        sentences: Number of sentences to return
        
    Returns:
        Wikipedia content or empty string if failed
    """
    try:
        response = requests.post(
            WIKIPEDIA_URL,
            json={"topic": topic, "sentences": sentences},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("content", "")
        else:
            print(f"Error in Wikipedia search: {response.status_code} - {response.text}")
            return ""
    
    except Exception as e:
        print(f"Exception in Wikipedia search: {e}")
        return ""

def analyze_with_gemini(prompt: str, priority: str = "high") -> Dict[str, Any]:
    """
    Analyze content using the Gemini API.
    
    Args:
        prompt: The prompt to send to Gemini
        priority: Priority level (low, medium, high)
        
    Returns:
        Dict with response and model used
    """
    try:
        response = requests.post(
            GEMINI_URL,
            json={"prompt": prompt, "priority": priority, "verbose": True},
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error in Gemini analysis: {response.status_code} - {response.text}")
            return {"response": f"Error: {response.status_code}", "model_used": "none"}
    
    except Exception as e:
        print(f"Exception in Gemini analysis: {e}")
        return {"response": f"Exception: {str(e)}", "model_used": "none"}

def create_research_document(topic: str, output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a comprehensive research document on a topic by combining web search,
    Wikipedia, and AI analysis.
    
    Args:
        topic: Research topic
        output_file: Optional file to save the research to
        
    Returns:
        Dict with the research results
    """
    start_time = time.time()
    print(f"\nStarting research on: {topic}")
    
    # Step 1: Get web search results
    print("Performing web search...")
    web_results = get_web_search_results(topic, max_results=5)
    web_search_time = time.time() - start_time
    print(f"Found {len(web_results)} web results in {web_search_time:.2f} seconds")
    
    # Extract summaries from web results
    web_summaries = []
    for i, result in enumerate(web_results):
        title = result.get("title", "No title")
        snippet = result.get("body", "No content")
        url = result.get("href", "No URL")
        web_summaries.append(f"{i+1}. {title}\n   - {snippet}\n   - Source: {url}")
    
    # Step 2: Get Wikipedia content
    print("Retrieving Wikipedia information...")
    wiki_start_time = time.time()
    wiki_content = get_wikipedia_content(topic, sentences=5)
    wiki_time = time.time() - wiki_start_time
    print(f"Retrieved Wikipedia content in {wiki_time:.2f} seconds")
    
    # Step 3: Analyze the information with Gemini
    print("Analyzing information with AI...")
    analysis_start_time = time.time()
    
    # Create research prompt
    research_prompt = f"""
    Create a comprehensive research summary on the topic: "{topic}"
    
    Web Search Results:
    {"".join(f"\\n{summary}" for summary in web_summaries)}
    
    Wikipedia Information:
    {wiki_content}
    
    Please analyze this information and create a well-structured research document with the following sections:
    1. Introduction to {topic}
    2. Current State of the Technology/Field
    3. Key Developments and Innovations
    4. Challenges and Limitations
    5. Future Prospects
    6. Conclusion
    
    For each point, cite the sources you're drawing from (web search or Wikipedia).
    """
    
    analysis_result = analyze_with_gemini(research_prompt, priority="high")
    analysis_time = time.time() - analysis_start_time
    print(f"Completed AI analysis in {analysis_time:.2f} seconds using {analysis_result.get('model_used', 'unknown')}")
    
    # Assemble the final research document
    research_content = analysis_result.get("response", "Analysis failed")
    
    # Save to file if requested
    if output_file:
        try:
            with open(output_file, "w") as f:
                f.write(f"# Research on {topic}\n\n")
                f.write(research_content)
            print(f"Research saved to {output_file}")
        except Exception as e:
            print(f"Error saving research to file: {e}")
    
    # Calculate total time
    total_time = time.time() - start_time
    
    # Return research data
    return {
        "topic": topic,
        "web_results_count": len(web_results),
        "has_wikipedia": bool(wiki_content),
        "content": research_content,
        "model_used": analysis_result.get("model_used", "unknown"),
        "web_search_time": web_search_time,
        "wiki_time": wiki_time,
        "analysis_time": analysis_time,
        "total_time": total_time
    }

def run_research_test(topic: str = None, save_to_file: bool = True) -> Dict[str, Any]:
    """
    Run a single research test.
    
    Args:
        topic: Research topic (or random if None)
        save_to_file: Whether to save results to a file
        
    Returns:
        Research results
    """
    if topic is None:
        import random
        topic = random.choice(RESEARCH_TOPICS)
    
    # Create output directory if needed
    output_dir = "research_results"
    if save_to_file and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate filename
    filename = None
    if save_to_file:
        safe_topic = topic.replace(" ", "_").replace("/", "_").lower()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"research_{safe_topic}_{timestamp}.md")
    
    # Run the research
    research_results = create_research_document(topic, filename)
    
    return research_results

def main():
    """Main entry point for the test script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the research capabilities of the multi-agent system")
    parser.add_argument("--topic", type=str, help="Specific topic to research")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to file")
    
    args = parser.parse_args()
    
    run_research_test(args.topic, not args.no_save)

if __name__ == "__main__":
    main()