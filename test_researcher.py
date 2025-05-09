#!/usr/bin/env python3
"""
Simple test script for the autonomous researcher with the model fallback feature
"""

import json
import os
from autonomous_researcher import AutonomousResearcher

def main():
    """Run a quick test of the autonomous researcher with model fallback"""
    # Create the researcher
    researcher = AutonomousResearcher()
    
    # Use a simpler query for faster results
    query = "Find the top three coffee shops in Seattle"
    
    print(f"Testing autonomous researcher with query: '{query}'")
    print("This will test the model fallback feature and result saving")
    
    # Run the research with a limited number of iterations (to make it faster)
    researcher.max_iterations = 2  # Limit to just 2 iterations for the test
    
    # Limit to just 1 URL per search to make it run faster
    original_select_urls = researcher._select_urls_to_visit
    def faster_url_selection(search_results):
        urls = original_select_urls(search_results)
        return urls[:1] if urls else []
    researcher._select_urls_to_visit = faster_url_selection
    
    # Run the research and save results
    results = researcher.research(query, save_results_to_file=True)
    
    # Print the paths to the saved files
    if "result_files" in results:
        print("\nResults saved to:")
        print(f"JSON: {results['result_files']['json']}")
        print(f"Text: {results['result_files']['text']}")
        
        # Print the contents of the text file
        if os.path.exists(results['result_files']['text']):
            print("\nContents of the text file:")
            print("-" * 80)
            with open(results['result_files']['text'], 'r') as f:
                print(f.read())
            print("-" * 80)
    
    # Print the models used in the process
    print("\nModels used during the research:")
    model_usage = {}
    
    # Count model usage
    for finding in results.get("research_trace", []):
        if "model_used" in finding:
            model = finding["model_used"]
            model_usage[model] = model_usage.get(model, 0) + 1
    
    # Add the final synthesis model
    if "model_used_for_synthesis" in results:
        model = results["model_used_for_synthesis"]
        model_usage[model] = model_usage.get(model, 0) + 1
    
    # Print model usage summary
    for model, count in model_usage.items():
        print(f"- {model}: {count} times")
    
    print("\nResearch completed successfully!")

if __name__ == "__main__":
    main()