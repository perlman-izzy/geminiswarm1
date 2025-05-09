#!/usr/bin/env python3
"""
Quick test for the autonomous researcher's model fallback and tracking features
"""

import json
import os
import sys
from autonomous_researcher import AutonomousResearcher

def main():
    """Run a quick test of the autonomous researcher with model tracking"""
    # Create the researcher
    researcher = AutonomousResearcher()
    
    print("Testing model tracking and result saving...")
    
    # Quick test of _call_gemini function
    print("\nTesting model usage tracking:")
    
    # High priority call
    high_result = researcher._call_gemini("What is the capital of France?", "high")
    print(f"High priority model used: {high_result.get('model_used', 'unknown')}")
    
    # Low priority call
    low_result = researcher._call_gemini("What is the capital of Italy?", "low")
    print(f"Low priority model used: {low_result.get('model_used', 'unknown')}")
    
    # Test content analysis with model tracking
    print("\nTesting content analysis with model tracking:")
    analysis = researcher._analyze_content(
        "Seattle is known for its coffee culture. Some popular coffee shops include Espresso Vivace, Victrola, and Stumptown.",
        "Find coffee shops in Seattle"
    )
    print(f"Content analysis model used: {analysis.get('model_used', 'unknown')}")
    
    # Test result saving
    print("\nTesting result saving:")
    
    # Create a simple mock result
    mock_result = {
        "answer": "This is a test answer about Seattle coffee shops",
        "categories": {
            "Popular Chains": ["Starbucks", "Seattle's Best"],
            "Independent Shops": ["Espresso Vivace", "Victrola"]
        },
        "limitations": ["Limited to well-known shops"],
        "sources": ["Test source 1", "Test source 2"],
        "model_used_for_synthesis": "Gemini 1.5 Pro"
    }
    
    # Save to file
    json_path, text_path = researcher.save_results(
        mock_result,
        "Find coffee shops in Seattle",
        "test_results"
    )
    
    print(f"Results saved to:")
    print(f"JSON: {json_path}")
    print(f"Text: {text_path}")
    
    # Print text file contents
    if os.path.exists(text_path):
        print("\nContents of the text file:")
        print("-" * 80)
        with open(text_path, 'r') as f:
            print(f.read())
        print("-" * 80)
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()