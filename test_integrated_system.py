#!/usr/bin/env python3
import requests
import json
import time
import os
import sys

BASE_URL = "http://localhost:5000"

def print_separator():
    print("\n" + "=" * 80 + "\n")

def call_api(endpoint, data=None, method="POST"):
    url = f"{BASE_URL}/{endpoint}"
    
    try:
        if method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            response = requests.get(url, params=data, timeout=10)
        
        try:
            return response.json()
        except:
            return {"error": response.text}
    except Exception as e:
        return {"error": str(e)}

def test_file_operations():
    print("Testing file operations...")
    
    # Create a test file
    test_content = f"""# Test File
Created: {time.strftime('%Y-%m-%d %H:%M:%S')}

This is a test file created by the system test suite.
It demonstrates the ability to write files to the filesystem.

The system should be able to:
1. Create this file
2. Read it back
3. List it in directory contents
"""
    
    # Write the file
    write_result = call_api("write_file", {
        "filepath": "test_file.md",
        "content": test_content
    })
    
    print(f"Write file result: {write_result.get('success', False)}")
    
    # Read the file back
    read_result = call_api("read_file", {"filepath": "test_file.md"})
    
    if "content" in read_result and read_result["content"] == test_content:
        print("File read operation successful ✓")
    else:
        print("File read operation failed ✗")
        
    # List directory contents
    list_result = call_api("list_files", {"path": "."})
    
    if "files" in list_result and "./test_file.md" in list_result["files"]:
        print("Directory listing operation successful ✓")
    else:
        print("Directory listing operation failed ✗")
    
    return write_result.get("success", False) and "content" in read_result

def test_web_search():
    print("Testing web search capabilities...")
    
    # Test web search
    search_term = "renewable energy technology"
    search_results = call_api("web_search", {"query": search_term, "max_results": 3})
    
    if "results" in search_results and len(search_results["results"]) > 0:
        print(f"Web search returned {len(search_results['results'])} results ✓")
        # Show first result title
        if len(search_results["results"]) > 0:
            print(f"First result: {search_results['results'][0].get('title', 'No title')}")
    else:
        print("Web search operation failed ✗")
    
    return "results" in search_results and len(search_results["results"]) > 0

def test_wikipedia_integration():
    print("Testing Wikipedia integration...")
    
    # Test Wikipedia search
    wiki_result = call_api("wikipedia", {"topic": "Artificial intelligence", "sentences": 3})
    
    if "content" in wiki_result and len(wiki_result["content"]) > 0:
        print("Wikipedia integration successful ✓")
        # Show first 100 characters
        print(f"Content preview: {wiki_result['content'][:100]}...")
    else:
        print("Wikipedia integration failed ✗")
    
    return "content" in wiki_result and len(wiki_result["content"]) > 0

def test_text_analysis():
    print("Testing text analysis capabilities...")
    
    # Test sentiment analysis
    test_text = """
    The rapid advancement of artificial intelligence has tremendous potential 
    to transform industries and improve human lives. While there are challenges 
    to address, the benefits of responsible AI development are substantial.
    """
    
    sentiment_result = call_api("sentiment", {"text": test_text})
    
    if "sentiment" in sentiment_result:
        print(f"Sentiment analysis successful ✓")
        print(f"Detected sentiment: {sentiment_result['sentiment']}")
        print(f"Polarity: {sentiment_result.get('polarity', 0)}")
        print(f"Subjectivity: {sentiment_result.get('subjectivity', 0)}")
    else:
        print("Sentiment analysis failed ✗")
    
    # Test keyword extraction
    keywords_result = call_api("keywords", {"text": test_text, "num_keywords": 5})
    
    if "keywords" in keywords_result:
        print(f"Keyword extraction successful ✓")
        print(f"Extracted keywords: {', '.join(keywords_result['keywords'])}")
    else:
        print("Keyword extraction failed ✗")
    
    return "sentiment" in sentiment_result and "keywords" in keywords_result

def main():
    print("INTEGRATED SYSTEM TEST")
    print("Testing core functionality without relying on Gemini API")
    print_separator()
    
    # Test file operations
    print("TEST 1: FILE OPERATIONS")
    file_ops_success = test_file_operations()
    print_separator()
    
    # Test web search capabilities
    print("TEST 2: WEB SEARCH")
    web_search_success = test_web_search()
    print_separator()
    
    # Test Wikipedia integration
    print("TEST 3: WIKIPEDIA INTEGRATION")
    wiki_success = test_wikipedia_integration()
    print_separator()
    
    # Test text analysis
    print("TEST 4: TEXT ANALYSIS")
    text_analysis_success = test_text_analysis()
    print_separator()
    
    # Print test summary
    print("TEST SUMMARY")
    print(f"File Operations: {'✓' if file_ops_success else '✗'}")
    print(f"Web Search: {'✓' if web_search_success else '✗'}")
    print(f"Wikipedia Integration: {'✓' if wiki_success else '✗'}")
    print(f"Text Analysis: {'✓' if text_analysis_success else '✗'}")
    
    # Calculate overall success
    total_tests = 4
    passed_tests = sum([
        1 if file_ops_success else 0,
        1 if web_search_success else 0,
        1 if wiki_success else 0,
        1 if text_analysis_success else 0
    ])
    
    success_rate = (passed_tests / total_tests) * 100
    
    print(f"\nPassed {passed_tests} out of {total_tests} tests ({success_rate:.1f}%)")
    print_separator()

if __name__ == "__main__":
    main()
