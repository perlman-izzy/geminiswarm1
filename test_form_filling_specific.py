#!/usr/bin/env python3
"""
Test script specifically for testing the form-filling capabilities with William White's resume.
This script tests against the API endpoint in our Flask application.
"""
import requests
import json
import time

# Define API endpoint
API_URL = "http://localhost:5000/api/auto-fill-form"

def test_auto_fill_form(job_title=None):
    """
    Test the form auto-filling endpoint with an optional specific job title.
    
    Args:
        job_title: Optional specific job title to fill out (will default to most recent)
        
    Returns:
        Response from the API
    """
    print(f"Testing form auto-fill for{' job: ' + job_title if job_title else ' most recent job'}")
    
    start_time = time.time()
    
    try:
        # Create request payload
        payload = {}
        if job_title:
            payload["jobTitle"] = job_title
        
        # Call the API
        response = requests.post(
            API_URL,
            json=payload,
            timeout=60  # 60 second timeout
        )
        
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\nSuccess! Response received in {elapsed_time:.2f} seconds.")
            print(f"Model used: {data.get('_model_used', 'Unknown')}")
            
            # Remove internal metadata for cleaner display
            clean_data = {k: v for k, v in data.items() if not k.startswith('_')}
            
            print("\nFilled Form Data:")
            print(json.dumps(clean_data, indent=2))
            
            return data
        else:
            print(f"\nError! API returned status code {response.status_code} in {elapsed_time:.2f} seconds.")
            print(f"Error message: {response.text}")
            return {"error": response.text}
    
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\nException after {elapsed_time:.2f} seconds: {e}")
        return {"error": str(e)}

def run_multiple_tests():
    """
    Run tests for different job positions from William White's resume.
    """
    job_titles = [
        None,  # Test most recent job (should be Piano Teacher)
        "Studio Piano Teacher",
        "Music Director",
        "Classroom Music Teacher"
    ]
    
    results = {}
    
    for job_title in job_titles:
        print("\n" + "="*60)
        result = test_auto_fill_form(job_title)
        results[job_title or "most_recent"] = result
        time.sleep(3)  # Wait a bit between tests to avoid rate limiting
    
    return results

def main():
    """Main entry point for the test script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the form-filling capabilities with William White's resume")
    parser.add_argument("--job", type=str, help="Specific job title to fill out form for")
    parser.add_argument("--all", action="store_true", help="Run tests for all job positions")
    
    args = parser.parse_args()
    
    if args.all:
        run_multiple_tests()
    else:
        test_auto_fill_form(args.job)

if __name__ == "__main__":
    main()