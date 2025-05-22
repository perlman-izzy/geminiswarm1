#!/usr/bin/env python3
"""
Simple test script for testing escalating complexity prompts with the Gemini API directly,
without relying on the swarm controller or extended proxy.
"""
import sys
import json
import time
import requests
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("escalation_test")

# Test prompts in order of increasing complexity
TEST_PROMPTS = [
    {
        "name": "simple_weather",
        "prompt": "What's the weather like today?",
        "description": "Basic question about today's weather - tests simple factual lookup"
    },
    {
        "name": "capital_cities",
        "prompt": "List the capital cities of 5 European countries and their populations.",
        "description": "Medium complexity factual query - tests knowledge retrieval"
    },
    {
        "name": "explain_concept",
        "prompt": "Explain how quantum computing works in simple terms.",
        "description": "Concept explanation - tests ability to simplify complex topics"
    },
    {
        "name": "creative_writing",
        "prompt": "Write a short poem about artificial intelligence in the style of Shakespeare.",
        "description": "Creative task - tests language generation and stylistic mimicry"
    },
    {
        "name": "market_analysis",
        "prompt": "Analyze the current trends in renewable energy markets and predict future developments.",
        "description": "Analysis task - tests complex reasoning and synthesis of information"
    },
    {
        "name": "coding_task",
        "prompt": "Write a Python function that implements the Fibonacci sequence using recursion with memoization.",
        "description": "Coding task - tests ability to generate functional code"
    },
    {
        "name": "multi_step_search",
        "prompt": "Find popular music venues in San Francisco that have a piano. For the top 3 results, provide their address, rating, and a brief description.",
        "description": "Complex search - tests web search, filtering, and result synthesis"
    },
    {
        "name": "package_install",
        "prompt": "I need to analyze the sentiment of customer reviews. First install the necessary library (like NLTK or TextBlob), then write code to perform sentiment analysis on the following reviews: 'The service was excellent!', 'I would never come back to this place.', 'Average experience, nothing special.'",
        "description": "Resource acquisition + task - tests package installation and use"
    }
]

def test_prompt(prompt, url="http://localhost:5000/gemini", verbose=True):
    """Test a single prompt."""
    if verbose:
        print(f"\nTesting prompt: '{prompt[:100]}...'")
    
    start_time = time.time()
    try:
        response = requests.post(
            url,
            json={"prompt": prompt},
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        elapsed_time = time.time() - start_time
        
        if verbose:
            print(f"Response time: {elapsed_time:.2f} seconds")
            print("\nResponse:")
            print(result.get("response", "No response"))
        
        return {
            "success": True,
            "elapsed_time": elapsed_time,
            "response": result.get("response", "")
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        if verbose:
            print(f"Error: {str(e)}")
        
        return {
            "success": False,
            "elapsed_time": elapsed_time,
            "error": str(e)
        }

def run_test_suite(prompts, verbose=True):
    """Run the full test suite."""
    results = []
    
    for i, prompt_data in enumerate(prompts):
        name = prompt_data["name"]
        prompt = prompt_data["prompt"]
        description = prompt_data.get("description", "")
        
        if verbose:
            print("\n" + "="*80)
            print(f"TEST {i+1}/{len(prompts)}: {name}")
            print(f"DESCRIPTION: {description}")
            print("="*80)
        
        result = test_prompt(prompt, verbose=verbose)
        result["name"] = name
        results.append(result)
        
        # Short pause between tests to avoid rate limiting
        if i < len(prompts) - 1:
            time.sleep(1)
    
    return results

def display_summary(results):
    """Display a summary of the test results."""
    success_count = sum(1 for r in results if r.get("success", False))
    print("\n" + "="*80)
    print(f"TEST SUMMARY: {success_count}/{len(results)} tests passed")
    print("="*80)
    
    for result in results:
        name = result.get("name", "unknown")
        success = result.get("success", False)
        elapsed = result.get("elapsed_time", 0)
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {name} ({elapsed:.2f}s)")
    
    print("="*80)

def main():
    """Run escalating complexity tests."""
    import argparse
    parser = argparse.ArgumentParser(description="Test the Gemini API with escalating complexity prompts")
    parser.add_argument("--url", default="http://localhost:5000/gemini", help="URL of the Gemini API endpoint")
    parser.add_argument("--test", help="Run only the specified test by name")
    
    args = parser.parse_args()
    
    if args.test:
        matching_prompts = [p for p in TEST_PROMPTS if p["name"] == args.test]
        if not matching_prompts:
            print(f"No test found with name '{args.test}'")
            print(f"Available tests: {', '.join(p['name'] for p in TEST_PROMPTS)}")
            return 1
        prompts = matching_prompts
    else:
        prompts = TEST_PROMPTS
    
    results = run_test_suite(prompts)
    display_summary(results)
    
    # Return 0 if all tests passed, 1 otherwise
    return 0 if all(r.get("success", False) for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())