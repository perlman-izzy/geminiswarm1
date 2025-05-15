"""
Mock LLM interface for the agent to use when the API is not available.
This enables direct testing of task completion validation without external dependencies.
"""
import logging
import re
from typing import Dict, Any, List, Optional

from superagi_replit.lib.logger import logger


class MockLLM:
    """A mock LLM class that simulates responses for testing."""
    
    def __init__(self):
        """Initialize the mock LLM."""
        self.logger = logger
        self.response_templates = {
            "search_venues": self._generate_venue_response,
            "search_emails": self._generate_email_response,
            "search_facilities": self._generate_facility_response,
            "default": self._generate_default_response
        }
    
    def generate(self, prompt: str) -> str:
        """
        Generate a response based on the prompt.
        
        Args:
            prompt: The prompt to respond to
            
        Returns:
            A mock response
        """
        self.logger.info(f"Generating mock response for prompt: {prompt[:50]}...")
        
        # Direct task detection from the prompt
        if "email" in prompt.lower() and "jazz" in prompt.lower():
            return self._generate_email_response(prompt)
        elif "restroom" in prompt.lower() or "bathroom" in prompt.lower():
            return self._generate_facility_response(prompt)
        elif "venue" in prompt.lower() or "piano" in prompt.lower():
            return self._generate_venue_response(prompt)
        
        # Fallback to more general detection
        task_type = self._detect_task_type(prompt)
        
        # Get the appropriate template function
        template_func = self.response_templates.get(task_type, self.response_templates["default"])
        
        # Generate response based on the prompt
        return template_func(prompt)
    
    def _detect_task_type(self, prompt: str) -> str:
        """Detect the type of task from the prompt."""
        prompt_lower = prompt.lower()
        
        if re.search(r"venue|piano|club|bar|restaurant", prompt_lower):
            return "search_venues"
        elif re.search(r"email|contact|jazz club", prompt_lower):
            return "search_emails"
        elif re.search(r"restroom|bathroom|toilet|facility", prompt_lower):
            return "search_facilities"
        else:
            return "default"
    
    def _generate_venue_response(self, prompt: str) -> str:
        """Generate a venue search response."""
        # Extract the city from the prompt
        city_match = re.search(r"in\s+([A-Za-z\s]+)(?:,|\s+with|\s+that)", prompt, re.IGNORECASE)
        city = city_match.group(1) if city_match else "San Francisco"
        
        # Extract what we're looking for
        feature_match = re.search(r"with\s+([A-Za-z\s]+)(?:\.|\s+focus)", prompt, re.IGNORECASE)
        feature = feature_match.group(1) if feature_match else "pianos"
        
        response = f"""
I'll help you find venues in {city} with {feature}. I'll search for this information and provide a comprehensive list.

First, let me search for venues in {city} with {feature}.

```
{{
    "thoughts": "I need to find venues in {city} that have {feature}. I'll start with a general search.",
    "tool": "WebSearchTool",
    "tool_input": {{
        "query": "venues with {feature} in {city}",
        "num_results": 5
    }}
}}
```

Based on my search, I've found several venues in {city} with {feature}:

1. Music Hub - A performance venue with multiple {feature}
2. Harmony Lounge - A {feature} bar with nightly performances
3. Grand Hotel - Has a grand piano in their lounge area

Let me search for more specific information.

```
{{
    "thoughts": "I should look specifically for {feature} bars and venues where people can play {feature}.",
    "tool": "WebSearchTool",
    "tool_input": {{
        "query": "{feature} bars {city} where customers can play",
        "num_results": 5
    }}
}}
```

I found more venues with {feature} in {city}:

4. Melody's - A classic {feature} bar where customers can sing along
5. Rhythm Lounge - Features a {feature} for performances
6. The Music Box - Has a {feature} where customers can play and sing
7. City Plaza - Public {feature} seasonally available

Let me check if there are any hotels or restaurants with notable {feature}.

```
{{
    "thoughts": "Hotels and upscale restaurants sometimes have {feature} for ambiance.",
    "tool": "WebSearchTool",
    "tool_input": {{
        "query": "{city} hotels restaurants with grand {feature}",
        "num_results": 5
    }}
}}
```

Here's a comprehensive list of venues in {city} with {feature}:

{feature.title()} Bars & Venues:
1. Melody's - 123 Main St - Classic {feature} bar where patrons can sing along
2. Music Hub - 456 Broadway - Performance venue with multiple {feature}
3. The Music Box - 789 Oak Ave - Has a {feature} where customers can play and sing
4. Rhythm Lounge - 321 Pine St - Features a {feature} for performances
5. Harmony Lounge - 654 Maple St - {feature} bar with nightly performances

Hotels & Restaurants:
6. The Grand Hotel - 987 Market St - Has a grand piano
7. Luxury Inn - 222 Union St - Features a {feature} in their lounge area
8. The Ritz - 600 California St - Grand {feature} in the lobby
9. Gourmet Dining - 495 Mission St - Features a {feature} certain nights

Public {feature.title()}:
10. City Plaza - Public {feature} available seasonally
11. Central Station - Occasionally hosts public {feature}

Music Schools with Practice {feature.title()}:
12. City Conservatory of Music - 50 First St - Has practice rooms with {feature}
13. Community Music Center - 544 Fourth St - Has {feature} available for student use

This list covers a variety of venues across {city} where {feature} are available for performances, customer use, or as part of the ambiance. Some require a purchase (food/drinks at bars), while others like public {feature} are free to use when available.
"""
        return response
    
    def _generate_email_response(self, prompt: str) -> str:
        """Generate an email search response."""
        # Extract the number of emails requested
        num_match = re.search(r"(\d+)\s+email", prompt, re.IGNORECASE)
        num_emails = int(num_match.group(1)) if num_match else 20
        
        # Extract the location from the prompt
        location_match = re.search(r"in\s+([A-Za-z\s]+)(?:\.|\s+make)", prompt, re.IGNORECASE)
        location = location_match.group(1) if location_match else "New York City"
        
        # Extract what type of businesses
        business_match = re.search(r"of\s+([A-Za-z\s]+)\s+in", prompt, re.IGNORECASE)
        business_type = business_match.group(1) if business_match else "jazz clubs"
        
        response = f"""
I'll help you find {num_emails} email addresses of {business_type} in {location}. Let me search for this information.

```
{{
    "thoughts": "I should start by finding a list of {business_type} in {location}.",
    "tool": "WebSearchTool",
    "tool_input": {{
        "query": "list of {business_type} in {location}",
        "num_results": 10
    }}
}}
```

I found several {business_type} in {location}. Now I need to find their contact information.

```
{{
    "thoughts": "I should look for contact pages for these clubs",
    "tool": "WebSearchTool",
    "tool_input": {{
        "query": "Blue Note Jazz NYC email contact",
        "num_results": 3
    }}
}}
```

I've found some email addresses so far:
1. info@bluenote.net - Blue Note Jazz Club
2. info@villagevanguard.com - Village Vanguard
3. booking@smalls-jazz.com - Smalls Jazz Club

Let me continue searching for more clubs.

```
{{
    "thoughts": "I need to find more jazz clubs and their emails",
    "tool": "WebSearchTool",
    "tool_input": {{
        "query": "Birdland Jazz Club NYC contact email",
        "num_results": 3
    }}
}}
```

I've compiled a list of {num_emails} email addresses for {business_type} in {location}:

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

This list includes a variety of jazz venues across {location}, from iconic clubs like the Blue Note and Village Vanguard to smaller venues like Fat Cat and Bill's Place. These email addresses can be used for inquiries, bookings, or general information.

Task complete: I've found {num_emails} email addresses of {business_type} in {location} as requested.
"""
        return response

    def _generate_facility_response(self, prompt: str) -> str:
        """Generate a facility search response."""
        # Extract the location from the prompt
        location_match = re.search(r"in\s+([A-Za-z\s]+)(?:\.|\s+that)", prompt, re.IGNORECASE)
        location = location_match.group(1) if location_match else "San Francisco"
        
        # Extract the type of facility
        facility_match = re.search(r"(?:the\s+)?([A-Za-z\s]+)(?:\s+in\s+|\s+that\s+is)", prompt, re.IGNORECASE)
        facility_type = facility_match.group(1) if facility_match else "public restroom"
        
        response = f"""
I need to find {facility_type} in {location} with specific criteria. Let me search for information.

```
{{
    "thoughts": "I need to find {facility_type} in {location} that are clean, not upstairs, and free to use.",
    "tool": "WebSearchTool",
    "tool_input": {{
        "query": "cleanest {facility_type} {location} free to use",
        "num_results": 5
    }}
}}
```

I found some information about {facility_type} in {location}. Let me get more specific details and reviews.

```
{{
    "thoughts": "I need to check for reviews and cleanliness ratings of these {facility_type}.",
    "tool": "WebSearchTool",
    "tool_input": {{
        "query": "{location} public library main branch {facility_type} reviews cleanliness",
        "num_results": 5
    }}
}}
```

Let me search for the Central Plaza Mall {facility_type}, which were mentioned in my previous search results.

```
{{
    "thoughts": "The Central Plaza mall was mentioned as having clean {facility_type} on the ground floor.",
    "tool": "WebSearchTool",
    "tool_input": {{
        "query": "Central Plaza {location} ground floor {facility_type} cleanliness",
        "num_results": 5
    }}
}}
```

Let me check reviews for the City Center {facility_type}, which were also mentioned.

```
{{
    "thoughts": "City Center was also mentioned as having clean {facility_type}.",
    "tool": "WebScraperTool",
    "tool_input": {{
        "url": "https://www.yelp.com/search?find_desc={facility_type}&find_loc=City+Center%2C+{location}",
        "max_depth": 2
    }}
}}
```

I want to verify if these {facility_type} require a purchase to use. Let me search for that specific information.

```
{{
    "thoughts": "I need to confirm which {facility_type} don't require a purchase to use.",
    "tool": "WebSearchTool",
    "tool_input": {{
        "query": "{location} {facility_type} no purchase required ground floor",
        "num_results": 5
    }}
}}
```

Based on my research, the cleanest {facility_type} in {location} that is not upstairs and doesn't require a purchase to use is:

**The Main Branch of the {location} Public Library**
Address: 100 Library St, {location}

This {facility_type} meets all the required criteria:
1. Cleanliness: It's consistently maintained and cleaned regularly throughout the day
2. Location: It's on the ground floor near the entrance
3. Accessibility: No stairs required to access it
4. No purchase necessary: It's in a public library, which is free to enter

Other notable options that meet the criteria but aren't rated as highly for cleanliness:

- Central Plaza's {facility_type} (ground floor, near the Promenade level)
- City Hall {facility_type} (ground floor, near the back of the marketplace)
- Downtown Square public toilets (street level)
- Central Park {facility_type} (garden level)

This assessment is based on current reviews, cleanliness reports, and confirmation that these facilities are on the ground floor and do not require any purchase to use.

The {location} Public Library Main Branch {facility_type} is the clear winner based on consistent positive reviews about its cleanliness and accessibility. The library enforces strict standards for their facilities and they are cleaned multiple times daily.
"""
        return response
    
    def _generate_default_response(self, prompt: str) -> str:
        """Generate a default response for unknown task types."""
        return f"""
I'm not sure how to specifically handle this task, but I'll try my best to help you.

Based on your request: "{prompt[:100]}..."

I would need to:
1. Understand your specific question
2. Search for relevant information online
3. Compile the results in a useful format

Would you like me to attempt a web search for this query?
"""