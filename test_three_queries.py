#!/usr/bin/env python3
"""
Test script for evaluating the stealth proxy with three different queries
"""

import logging
import time
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_queries")

# Import our fallback stealth client
try:
    from fallback_stealth_proxy import generate_content
    HAS_STEALTH_PROXY = True
    logger.info("Using fallback stealth proxy for tests")
except ImportError:
    try:
        from gemini_stealth_client import generate_content
        HAS_STEALTH_PROXY = True
        logger.info("Using original stealth proxy for tests")
    except ImportError:
        HAS_STEALTH_PROXY = False
        logger.warning("No stealth proxy available, using standard API only")
    
    # Provide alternative implementation
    import requests
    def generate_content(prompt, model="gemini-1.5-pro", temperature=0.7, max_output_tokens=4096):
        """Fallback to standard API if stealth proxy not available"""
        try:
            response = requests.post(
                "http://localhost:5000/gemini",
                json={
                    "prompt": prompt,
                    "model": f"models/{model}",
                    "priority": "high"
                },
                headers={"Content-Type": "application/json"}
            )
            result = response.json()
            return {
                "text": result.get("response", "Error: No response"),
                "model_used": model,
                "status": "success" if "error" not in result.get("response", "").lower() else "error"
            }
        except Exception as e:
            logger.error(f"Error calling standard API: {e}")
            return {
                "text": f"Error: {str(e)}",
                "model_used": model,
                "status": "error"
            }

# Test queries with a mix of complexity and types
QUERIES = [
    {
        "name": "Query 1: Simple Factual",
        "text": "What is quantum computing and how does it differ from classical computing?"
    },
    {
        "name": "Query 2: More Complex Research",
        "text": "Research the latest developments in renewable energy storage technologies in 2024-2025 and how they impact grid stability."
    },
    {
        "name": "Query 3: Creative/Speculative",
        "text": "Imagine and describe what personal computing devices might look like in 2040, considering trends in AR/VR, neural interfaces, and miniaturization."
    }
]

def run_query_test(query_info: Dict[str, str]) -> Dict[str, Any]:
    """Run a test with a specific query"""
    query_name = query_info["name"]
    query_text = query_info["text"]
    
    logger.info(f"==== TESTING: {query_name} ====")
    print(f"\n\n==== TESTING: {query_name} ====")
    print(f"Query: {query_text}\n")
    
    # Record start time
    start_time = time.time()
    
    # Try with stealth proxy
    result = generate_content(
        prompt=query_text,
        model="gemini-1.5-pro",
        temperature=0.7,
        max_output_tokens=4096
    )
    
    # Record end time
    elapsed = time.time() - start_time
    
    # Log results
    logger.info(f"Status: {result.get('status', 'unknown')}")
    logger.info(f"Model: {result.get('model_used', 'unknown')}")
    logger.info(f"Time: {elapsed:.2f} seconds")
    logger.info(f"Response length: {len(result.get('text', ''))}")
    
    # Print results
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Model: {result.get('model_used', 'unknown')}")
    print(f"Time: {elapsed:.2f} seconds")
    print(f"Response: {result.get('text', '')[:500]}...")
    if len(result.get('text', '')) > 500:
        print("... (response truncated)")
    
    # Return result for analysis
    return {
        "query": query_name,
        "status": result.get("status", "unknown"),
        "model": result.get("model_used", "unknown"),
        "elapsed": elapsed,
        "text": result.get("text", ""),
        "success": result.get("status") == "success"
    }

def run_all_tests():
    """Run tests on all queries and summarize results"""
    print("\n====== TESTING STEALTH PROXY WITH THREE QUERIES ======")
    
    results = []
    start_time = time.time()
    
    # Run each query test
    for query in QUERIES:
        results.append(run_query_test(query))
        # Add some delay between tests to avoid rate limits
        if query != QUERIES[-1]:  # No delay after last query
            delay = 5
            print(f"\nWaiting {delay} seconds before next query...\n")
            time.sleep(delay)
    
    total_time = time.time() - start_time
    
    # Summarize results
    print("\n====== TEST SUMMARY ======")
    successful = [r for r in results if r["success"]]
    print(f"Total queries: {len(results)}")
    print(f"Successful: {len(successful)}/{len(results)}")
    print(f"Total time: {total_time:.2f} seconds")
    
    # Show success/failure for each query
    print("\nResults by query:")
    for result in results:
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
        model = result["model"]
        print(f"{result['query']}: {status} (using {model})")
    
    return results

if __name__ == "__main__":
    run_all_tests()