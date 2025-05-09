#!/usr/bin/env python3
"""
Test script for benchmarking our Gemini API proxy with escalating complexity prompts
"""
import requests
import time
import json
import sys
from typing import Dict, Any, List

# Set the API endpoint
API_URL = "http://localhost:5000/gemini"

# Define a series of prompts with escalating complexity
TEST_PROMPTS = [
    # Simple prompts
    {
        "name": "Simple Math",
        "prompt": "What is 245 + 372?",
        "priority": "low"
    },
    {
        "name": "Basic Definition",
        "prompt": "What is artificial intelligence?",
        "priority": "low"
    },
    
    # Medium complexity prompts
    {
        "name": "Scientific Explanation",
        "prompt": "Explain how photosynthesis works in plants.",
        "priority": "medium"
    },
    {
        "name": "Historical Analysis",
        "prompt": "Analyze the major causes and effects of World War I.",
        "priority": "medium" 
    },
    
    # High complexity prompts
    {
        "name": "Complex Problem",
        "prompt": "Explain quantum entanglement and its implications for quantum computing.",
        "priority": "high"
    },
    {
        "name": "Research Summary",
        "prompt": "Summarize the current state of research on using CRISPR for treating genetic diseases.",
        "priority": "high"
    },
    
    # Extremely complex prompts (may require multiple model attempts)
    {
        "name": "Multidisciplinary Analysis",
        "prompt": "Analyze the intersection of blockchain technology, artificial intelligence, and sustainable energy development. How might these technologies work together to address climate change?",
        "priority": "high"
    }
]

def test_prompt(prompt_data: Dict[str, str], verbose: bool = True) -> Dict[str, Any]:
    """
    Test a single prompt against the API and return the results.
    
    Args:
        prompt_data: Dict containing the prompt and priority
        verbose: Whether to print detailed results
        
    Returns:
        Dict with test results
    """
    start_time = time.time()
    
    try:
        response = requests.post(
            API_URL,
            json={
                "prompt": prompt_data["prompt"],
                "priority": prompt_data.get("priority", "low"),
                "verbose": True
            },
            timeout=60  # 60 second timeout
        )
        
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            result = {
                "name": prompt_data["name"],
                "status": "success",
                "model_used": data.get("model_used", "unknown"),
                "time": elapsed_time,
                "response_length": len(data.get("response", "")),
                "response_snippet": data.get("response", "")[:100] + "..." if len(data.get("response", "")) > 100 else data.get("response", "")
            }
        else:
            result = {
                "name": prompt_data["name"],
                "status": "error",
                "error_code": response.status_code,
                "error_msg": response.text,
                "time": elapsed_time
            }
    
    except Exception as e:
        elapsed_time = time.time() - start_time
        result = {
            "name": prompt_data["name"],
            "status": "exception",
            "error_msg": str(e),
            "time": elapsed_time
        }
    
    if verbose:
        print(f"\nTest: {result['name']}")
        print(f"Status: {result['status']}")
        if result['status'] == 'success':
            print(f"Model used: {result['model_used']}")
            print(f"Time: {result['time']:.2f} seconds")
            print(f"Response length: {result['response_length']} chars")
            print(f"Response snippet: {result['response_snippet']}")
        else:
            print(f"Error: {result.get('error_msg', 'Unknown error')}")
    
    return result

def run_benchmark(prompts: List[Dict[str, str]] = None, verbose: bool = True) -> List[Dict[str, Any]]:
    """
    Run a benchmark test on all prompts.
    
    Args:
        prompts: List of prompt dictionaries
        verbose: Whether to print detailed results
        
    Returns:
        List of test results
    """
    if prompts is None:
        prompts = TEST_PROMPTS
    
    results = []
    
    print(f"Starting benchmark with {len(prompts)} prompts...")
    
    for i, prompt_data in enumerate(prompts):
        print(f"\nRunning test {i+1}/{len(prompts)}: {prompt_data['name']}")
        result = test_prompt(prompt_data, verbose)
        results.append(result)
        
        # Add a short delay between requests to avoid overwhelming the API
        if i < len(prompts) - 1:
            time.sleep(2)
    
    return results

def display_summary(results: List[Dict[str, Any]]) -> None:
    """
    Display a summary of the benchmark results.
    
    Args:
        results: List of test results
    """
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = len(results) - success_count
    
    print("\n" + "="*50)
    print("BENCHMARK SUMMARY")
    print("="*50)
    print(f"Total tests: {len(results)}")
    print(f"Successful: {success_count} ({success_count/len(results)*100:.1f}%)")
    print(f"Failed: {error_count} ({error_count/len(results)*100:.1f}%)")
    
    if success_count > 0:
        avg_time = sum(r["time"] for r in results if r["status"] == "success") / success_count
        print(f"Average response time: {avg_time:.2f} seconds")
        
        models_used = {}
        for r in results:
            if r["status"] == "success":
                model = r.get("model_used", "unknown")
                models_used[model] = models_used.get(model, 0) + 1
        
        print("\nModels used:")
        for model, count in models_used.items():
            print(f"  - {model}: {count} times ({count/success_count*100:.1f}%)")
    
    print("\nResults by complexity:")
    
    complexity_levels = ["low", "medium", "high"]
    for level in complexity_levels:
        level_results = [r for i, r in enumerate(results) if i < len(TEST_PROMPTS) and TEST_PROMPTS[i].get("priority") == level]
        if level_results:
            success_level = sum(1 for r in level_results if r["status"] == "success")
            print(f"  - {level.capitalize()} priority: {success_level}/{len(level_results)} successful ({success_level/len(level_results)*100:.1f}%)")
    
    print("="*50)

def run_single_test(test_index: int, verbose: bool = True) -> None:
    """
    Run a single test by index.
    
    Args:
        test_index: Index of the test to run
        verbose: Whether to print detailed results
    """
    if 0 <= test_index < len(TEST_PROMPTS):
        prompt_data = TEST_PROMPTS[test_index]
        print(f"Running single test: {prompt_data['name']}")
        test_prompt(prompt_data, verbose)
    else:
        print(f"Invalid test index. Please choose 0-{len(TEST_PROMPTS)-1}.")

def main():
    """Main entry point for the test script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the Gemini API proxy with escalating complexity prompts")
    parser.add_argument("--test", type=int, help="Run a specific test by index (0-based)")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed output")
    
    args = parser.parse_args()
    
    if args.test is not None:
        run_single_test(args.test, not args.quiet)
    else:
        results = run_benchmark(verbose=not args.quiet)
        display_summary(results)

if __name__ == "__main__":
    main()