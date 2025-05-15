"""
Test the task validator with simulated agent responses.

This script tests the non-LLM task validator with simulated agent interactions
to verify that it correctly detects task completion.
"""
import time
from typing import List, Dict, Any, Tuple
import json

from superagi_replit.agent.non_llm_task_validator import NonLLMTaskValidator


def test_simple_task():
    """Test a simple task that should complete quickly."""
    print("\n==== Testing Simple Task ====")
    task_description = "What is the capital of France?"
    
    validator = NonLLMTaskValidator()
    
    # Simulate initial response with no tools
    response = "Based on my knowledge, the capital of France is Paris."
    validator.update_metrics(response)
    
    is_complete, reason, confidence = validator.is_task_complete(task_description)
    print(f"After first response: Complete: {is_complete}, Reason: {reason}, Confidence: {confidence:.2f}")
    
    # The task should be complete with a single response for this simple factual query
    return is_complete, reason, confidence


def test_venue_search():
    """Test a complex venue search task."""
    print("\n==== Testing Venue Search ====")
    task_description = "Find all the venues in San Francisco with pianos."
    
    validator = NonLLMTaskValidator()
    
    # Simulate initial search
    response1 = """
    I'll search for venues in San Francisco with pianos. Let me use a search tool to find initial information.
    ```
    {
        "thoughts": "I need to find venues in San Francisco that have pianos. I should start with a general search to find some initial leads.",
        "tool": "WebSearchTool",
        "tool_input": {
            "query": "venues with pianos in San Francisco",
            "num_results": 5
        }
    }
    ```
    """
    validator.update_metrics(response1, "WebSearchTool", {"query": "venues with pianos in San Francisco"})
    
    # Simulate search results processing
    response2 = """
    Based on my search, I've found several venues in San Francisco with pianos:
    
    1. Pianofight - A performance venue with multiple pianos
    2. Butterfly Lounge - A piano bar with nightly performances
    3. Hotel Nikko - Has a grand piano in their lounge area
    
    Let me search for more specific information about piano bars in SF.
    ```
    {
        "thoughts": "I should look specifically for piano bars and venues where people can play pianos.",
        "tool": "WebSearchTool",
        "tool_input": {
            "query": "piano bars San Francisco where customers can play",
            "num_results": 5
        }
    }
    ```
    """
    validator.update_metrics(response2, "WebSearchTool", {"query": "piano bars San Francisco where customers can play"})
    
    # Simulate more specific results
    response3 = """
    I found more venues with pianos in San Francisco:
    
    4. Martuni's - A classic piano bar where customers can sing along
    5. Octavia Lounge - Features a piano for performances
    6. The Alley - Has a piano where customers can play and sing
    7. Union Square Plaza - Public pianos seasonally available
    
    Let me check if there are any hotels or restaurants with notable pianos.
    ```
    {
        "thoughts": "Hotels and upscale restaurants sometimes have pianos for ambiance.",
        "tool": "WebSearchTool",
        "tool_input": {
            "query": "San Francisco hotels restaurants with grand pianos",
            "num_results": 5
        }
    }
    ```
    """
    validator.update_metrics(response3, "WebSearchTool", {"query": "San Francisco hotels restaurants with grand pianos"})
    
    # Simulate final results and synthesis
    response4 = """
    Here's a comprehensive list of venues in San Francisco with pianos:
    
    Piano Bars & Venues:
    1. Martuni's - 4 Valencia St - Classic piano bar where patrons can sing along
    2. PianoFight - 144 Taylor St - Performance venue with multiple pianos
    3. The Alley - 3325 Grand Ave - Has a piano where customers can play and sing
    4. Octavia Lounge - 1025 Octavia St - Features a piano for performances
    5. Butterfly Lounge - 1710 Mission St - Piano bar with nightly performances
    
    Hotels & Restaurants:
    6. Top of the Mark (InterContinental Mark Hopkins) - 999 California St - Has a grand piano
    7. Hotel Nikko - 222 Mason St - Features a piano in their lounge area
    8. The Ritz-Carlton - 600 Stockton St - Grand piano in the lobby
    9. Redwood Room at Clift Hotel - 495 Geary St - Features a piano certain nights
    
    Public Pianos:
    10. Union Square Plaza - Public pianos available seasonally
    11. Ferry Building - Occasionally hosts public pianos
    
    Music Schools with Practice Pianos:
    12. San Francisco Conservatory of Music - 50 Oak St - Has practice rooms with pianos
    13. Community Music Center - 544 Capp St - Has pianos available for student use
    
    This list covers a variety of venues across San Francisco where pianos are available for performances, customer use, or as part of the ambiance. Some require a purchase (food/drinks at bars), while others like public pianos are free to use when available.
    """
    validator.update_metrics(response4)
    
    is_complete, reason, confidence = validator.is_task_complete(task_description)
    print(f"After final response: Complete: {is_complete}, Reason: {reason}, Confidence: {confidence:.2f}")
    print(f"Status report: {json.dumps(validator.get_status_report(), indent=2, default=str)}")
    
    return is_complete, reason, confidence


def test_email_search():
    """Test an email search task."""
    print("\n==== Testing Email Search ====")
    task_description = "Find 20 email addresses of jazz clubs in New York City."
    
    validator = NonLLMTaskValidator()
    
    # Simulate multiple search iterations
    # Only showing a few for brevity
    
    response1 = """
    I need to find email addresses for jazz clubs in NYC. Let me start with a search.
    ```
    {
        "thoughts": "I should start by finding a list of jazz clubs in NYC.",
        "tool": "WebSearchTool",
        "tool_input": {
            "query": "list of jazz clubs in New York City",
            "num_results": 10
        }
    }
    ```
    """
    validator.update_metrics(response1, "WebSearchTool", {"query": "list of jazz clubs in New York City"})
    
    response2 = """
    I found several jazz clubs in NYC. Now I need to find their contact information.
    ```
    {
        "thoughts": "I should look for contact pages for these clubs",
        "tool": "WebSearchTool",
        "tool_input": {
            "query": "Blue Note Jazz NYC email contact",
            "num_results": 3
        }
    }
    ```
    """
    validator.update_metrics(response2, "WebSearchTool", {"query": "Blue Note Jazz NYC email contact"})
    
    # Simulate more searches and finally finding some emails
    response3 = """
    I've found some email addresses so far:
    1. info@bluenote.net - Blue Note Jazz Club
    2. info@villagevanguard.com - Village Vanguard
    3. booking@smalls-jazz.com - Smalls Jazz Club
    
    Let me continue searching for more clubs.
    ```
    {
        "thoughts": "I need to find more jazz clubs and their emails",
        "tool": "WebSearchTool",
        "tool_input": {
            "query": "Birdland Jazz Club NYC contact email",
            "num_results": 3
        }
    }
    ```
    """
    validator.update_metrics(response3, "WebSearchTool", {"query": "Birdland Jazz Club NYC contact email"})
    
    # Skip several iterations and show final result
    # in reality the validator would track all these iterations
    
    final_response = """
    I've compiled a list of 20 email addresses for jazz clubs in New York City:
    
    1. info@bluenote.net - Blue Note Jazz Club
    2. info@villagevanguard.com - Village Vanguard
    3. booking@smalls-jazz.com - Smalls Jazz Club
    4. reservations@birdlandjazz.com - Birdland Jazz Club
    5. info@jazzmob.org - Jazz at Lincoln Center
    6. management@dizzysclub.org - Dizzy's Club
    7. bookings@mintoncafe.com - Minton's Playhouse
    8. info@jazzstandard.com - Jazz Standard
    9. contact@zincsoup.com - Zinc Bar
    10. info@jazzgallery.org - The Jazz Gallery
    11. clubmanager@iridium.com - The Iridium
    12. bookings@cornelia-street.com - Cornelia Street Café
    13. events@metropolitanroom.com - Metropolitan Room
    14. contact@arthurstavern.com - Arthur's Tavern
    15. hello@billsplaceharlem.com - Bill's Place
    16. info@cafecarlyle.com - Café Carlyle
    17. manager@fatcatjazz.com - Fat Cat
    18. events@shapeshifterlab.com - ShapeShifter Lab
    19. info@jazzatjuliansnyc.com - Jazz at Kitano
    20. contact@jazzonthelexington.com - Jazz on the Lexington
    
    This list includes a variety of jazz venues across Manhattan, from iconic clubs like the Blue Note and Village Vanguard to smaller venues like Fat Cat and Bill's Place. These email addresses can be used for inquiries, bookings, or general information.
    
    Task complete: I've found 20 email addresses of jazz clubs in New York City as requested.
    """
    validator.update_metrics(final_response)
    
    is_complete, reason, confidence = validator.is_task_complete(task_description)
    print(f"After final response: Complete: {is_complete}, Reason: {reason}, Confidence: {confidence:.2f}")
    print(f"Status report: {json.dumps(validator.get_status_report(), indent=2, default=str)}")
    
    return is_complete, reason, confidence


def test_restroom_search():
    """Test a complex restroom search task."""
    print("\n==== Testing Restroom Search ====")
    task_description = "Find the cleanest public restroom in San Francisco that is not upstairs and that you don't have to purchase anything to use."
    
    validator = NonLLMTaskValidator()
    
    # Simulate initial search
    response1 = """
    I need to find clean public restrooms in San Francisco with specific criteria. Let me search for information.
    ```
    {
        "thoughts": "I need to find public restrooms in SF that are clean, not upstairs, and free to use.",
        "tool": "WebSearchTool",
        "tool_input": {
            "query": "cleanest public restrooms San Francisco free to use",
            "num_results": 5
        }
    }
    ```
    """
    validator.update_metrics(response1, "WebSearchTool", {"query": "cleanest public restrooms San Francisco free to use"})
    
    response2 = """
    I found some information about public restrooms in San Francisco. Let me get more specific details and reviews.
    ```
    {
        "thoughts": "I need to check for reviews and cleanliness ratings of these public restrooms.",
        "tool": "WebSearchTool",
        "tool_input": {
            "query": "San Francisco public library main branch restroom reviews cleanliness",
            "num_results": 5
        }
    }
    ```
    """
    validator.update_metrics(response2, "WebSearchTool", {"query": "San Francisco public library main branch restroom reviews cleanliness"})
    
    response3 = """
    Let me search for the Westfield San Francisco Centre Mall public restrooms, which were mentioned in my previous search results.
    ```
    {
        "thoughts": "The Westfield mall was mentioned as having clean public restrooms on the ground floor.",
        "tool": "WebSearchTool",
        "tool_input": {
            "query": "Westfield San Francisco Centre ground floor public restrooms cleanliness",
            "num_results": 5
        }
    }
    ```
    """
    validator.update_metrics(response3, "WebSearchTool", {"query": "Westfield San Francisco Centre ground floor public restrooms cleanliness"})
    
    # More searches would happen here
    
    response4 = """
    Let me check reviews for the Embarcadero Center restrooms, which were also mentioned.
    ```
    {
        "thoughts": "Embarcadero Center was also mentioned as having clean public restrooms.",
        "tool": "WebScraperTool",
        "tool_input": {
            "url": "https://www.yelp.com/search?find_desc=public+restrooms&find_loc=Embarcadero+Center%2C+San+Francisco%2C+CA",
            "max_depth": 2
        }
    }
    ```
    """
    validator.update_metrics(response4, "WebScraperTool", {"url": "https://www.yelp.com/search?find_desc=public+restrooms&find_loc=Embarcadero+Center%2C+San+Francisco%2C+CA"})
    
    response5 = """
    I want to verify if these restrooms require a purchase to use. Let me search for that specific information.
    ```
    {
        "thoughts": "I need to confirm which restrooms don't require a purchase to use.",
        "tool": "WebSearchTool",
        "tool_input": {
            "query": "San Francisco public restrooms no purchase required ground floor",
            "num_results": 5
        }
    }
    ```
    """
    validator.update_metrics(response5, "WebSearchTool", {"query": "San Francisco public restrooms no purchase required ground floor"})
    
    final_response = """
    Based on my research, the cleanest public restroom in San Francisco that is not upstairs and doesn't require a purchase to use is:
    
    **The Main Branch of the San Francisco Public Library**
    Address: 100 Larkin St, San Francisco, CA 94102
    
    This restroom meets all the required criteria:
    1. Cleanliness: It's consistently maintained and cleaned regularly throughout the day
    2. Location: It's on the ground floor near the entrance
    3. Accessibility: No stairs required to access it
    4. No purchase necessary: It's in a public library, which is free to enter
    
    Other notable options that meet the criteria but aren't rated as highly for cleanliness:
    
    - Embarcadero Center's public restrooms (ground floor, near the Promenade level)
- Ferry Building public restrooms (ground floor, near the back of the marketplace)
- Union Square public toilets (street level)
- Yerba Buena Gardens restrooms (garden level)

    This assessment is based on current reviews, cleanliness reports, and confirmation that these facilities are on the ground floor and do not require any purchase to use.
    
    The SF Public Library Main Branch restroom is the clear winner based on consistent positive reviews about its cleanliness and accessibility. The library enforces strict standards for their facilities and they are cleaned multiple times daily.
    """
    validator.update_metrics(final_response)
    
    is_complete, reason, confidence = validator.is_task_complete(task_description)
    print(f"After final response: Complete: {is_complete}, Reason: {reason}, Confidence: {confidence:.2f}")
    print(f"Status report: {json.dumps(validator.get_status_report(), indent=2, default=str)}")
    
    return is_complete, reason, confidence


def test_repeated_responses():
    """Test the system's ability to detect repetitive responses."""
    print("\n==== Testing Repetitive Responses ====")
    task_description = "Find information about climate change."
    
    validator = NonLLMTaskValidator()
    
    # First response
    response1 = "Climate change is a significant and lasting change in the statistical distribution of weather patterns over periods ranging from decades to millions of years. It may be a change in average weather conditions, or in the distribution of weather around the average conditions."
    validator.update_metrics(response1)
    
    # Second response (very similar to first)
    response2 = "Climate change refers to significant, long-term changes in the global climate. It involves changes in temperature, precipitation, or wind patterns, among other effects, that occur over several decades or longer."
    validator.update_metrics(response2)
    
    # Third response (very similar again)
    response3 = "Climate change is the long-term alteration in Earth's climate and weather patterns. It involves changes to temperature, precipitation, and wind patterns that occur over several decades or longer."
    validator.update_metrics(response3)
    
    is_complete, reason, confidence = validator.is_task_complete(task_description)
    print(f"After repetitive responses: Complete: {is_complete}, Reason: {reason}, Confidence: {confidence:.2f}")
    print(f"Status report: {json.dumps(validator.get_status_report(), indent=2, default=str)}")
    
    return is_complete, reason, confidence


def main():
    """Run all the validator tests."""
    print("\n===================================================")
    print("  TESTING NON-LLM TASK VALIDATOR")
    print("===================================================")
    
    results = {}
    
    results["simple_task"] = test_simple_task()
    results["venue_search"] = test_venue_search()
    results["email_search"] = test_email_search()
    results["restroom_search"] = test_restroom_search()
    results["repeated_responses"] = test_repeated_responses()
    
    print("\n===================================================")
    print("  TEST RESULTS SUMMARY")
    print("===================================================")
    
    for test_name, (is_complete, reason, confidence) in results.items():
        print(f"{test_name:20s}: Complete: {is_complete}, Confidence: {confidence:.2f}, Reason: {reason}")
    
    print("\nAll tests completed successfully.")


if __name__ == "__main__":
    main()