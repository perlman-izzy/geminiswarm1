#!/usr/bin/env python3
import requests
import json
import time
import sys
import os

BASE_URL = "http://localhost:5000"

def print_separator():
    print("\n" + "=" * 80 + "\n")

def call_api(endpoint, data=None, method="POST"):
    url = f"{BASE_URL}/{endpoint}"
    
    if method == "POST":
        response = requests.post(url, json=data)
    else:
        response = requests.get(url, params=data)
    
    try:
        return response.json()
    except:
        return {"error": response.text}

def main():
    print("AUTONOMOUS RESEARCH AGENT TEST")
    print_separator()
    
    # Step 1: Define a research topic and collect information
    research_topic = "Renewable energy solutions for urban environments"
    print(f"Research Topic: {research_topic}")
    print_separator()
    
    # Step 2: Search for information
    print("Searching for information...")
    search_results = call_api("web_search", {"query": research_topic, "max_results": 5})
    
    # Step 3: Get Wikipedia information
    print("Getting Wikipedia information...")
    wiki_data = call_api("wikipedia", {"topic": "Renewable energy", "sentences": 10})
    
    # Step 4: Create a research document with collected information
    print("Creating research document with collected information...")
    document_content = f"""# Research Report: {research_topic}
Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Web Search Results

"""
    
    # Add web search results
    if "results" in search_results and search_results["results"]:
        for i, result in enumerate(search_results["results"], 1):
            document_content += f"### Source {i}: {result.get('title', 'No title')}\n"
            document_content += f"URL: {result.get('href', 'No URL')}\n"
            document_content += f"Summary: {result.get('body', 'No content')}\n\n"
    else:
        document_content += "No web search results available.\n\n"
    
    # Add Wikipedia content
    document_content += "## Wikipedia Information\n\n"
    document_content += wiki_data.get("content", "No Wikipedia information available.") + "\n\n"
    
    # Step 5: Generate analysis based on collected information
    print("Generating analysis based on collected information...")
    prompt = f"""
    Based on the following information about {research_topic}, create a concise analysis
    highlighting key technologies, challenges, and potential solutions for implementation
    in urban settings. Focus on practical applications.
    
    Limit your response to 500 words.
    """
    
    analysis = call_api("gemini", {"prompt": prompt, "priority": "high"})
    
    # Add analysis to document
    document_content += "## Analysis\n\n"
    document_content += analysis.get("response", "Analysis not available due to API limitations.") + "\n\n"
    
    # Step 6: Extract keywords
    print("Extracting keywords from research...")
    all_text = wiki_data.get("content", "") + " " + document_content
    keywords = call_api("keywords", {"text": all_text, "num_keywords": 15})
    
    # Add keywords to document
    document_content += "## Key Terms\n\n"
    if "keywords" in keywords and keywords["keywords"]:
        document_content += ", ".join(keywords["keywords"]) + "\n\n"
    else:
        document_content += "No keywords extracted.\n\n"
    
    # Step 7: Save the document to a file
    print("Saving research document to file...")
    research_filename = "renewable_energy_research.md"
    file_result = call_api("write_file", {
        "filepath": research_filename,
        "content": document_content
    })
    
    if file_result.get("success", False):
        print(f"Research document saved to: {research_filename}")
    else:
        print(f"Error saving research document: {file_result.get('message', 'Unknown error')}")
    
    # Step 8: Verify the file was created and read its contents
    print("Verifying file creation...")
    read_result = call_api("read_file", {"filepath": research_filename})
    if "content" in read_result and len(read_result["content"]) > 0:
        print(f"Successfully verified file creation. File size: {len(read_result['content'])} bytes")
    else:
        print(f"Error verifying file creation: {read_result.get('error', 'Unknown error')}")
    
    print_separator()
    print("AUTONOMOUS RESEARCH TASK COMPLETE")

if __name__ == "__main__":
    main()
