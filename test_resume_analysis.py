#!/usr/bin/env python3
"""
Direct test for the resume analysis capability.
This script directly uses the call_gemini_with_model_selection function
to analyze William White's resume and extract job information.
"""
import json
import sys
import time
from typing import Dict, Any

# Import the function directly from main
from main import call_gemini_with_model_selection

# William White's resume content
RESUME_CONTENT = """
William White

50 5th Ave
San Francisco, CA
(310) 867-5603
billywhitemusic@gmail.com

EXPERIENCE

California Conservatory of Music, Redwood City, CA  — Studio Piano Teacher  (Sep. 2023 - Jun 2024)
• Created and implemented individual piano curricula for students aged 6-17
Supervisor: Chris Mallettinfo@thecaliforniaconservatory.com

R.E.S.P.E.C.T : The Aretha Franklin Musical, National Tour Music Director (November 2023 - March 2023)
Conducted 9 musicians, coordinated rehearsals, handled personnel and logistics issues, played keyboard 1, and created musical score for successful touring musical
Supervisor: Jim Lanahan
https://www.jimlanahan.com/contact

Hooper Avenue Elementary, Los Angeles, CA — Classroom Music Teacher (Sep-Jan 2018)
• Designed and implemented culturally-relevant curriculum focused primarily on Latin/Latin-American music for grades 3-5.  Received extremely positive feedback from students, teachers and parents
Special Ed Teacher: Dorene Scala, dorene64@gmail.com; 5th Grade Teacher: Jose Perdomo, jap1474@lausd.net

EDUCATION
University of California, Los Angeles –  B.A., Ethnomusicology(2000-2005)
San Francisco State University, San Francisco, CA - M.A. Composition(Jan 2020-ongoing)

LANGUAGES
English, French (fluent), Spanish (intermediate), Hebrew (intermediate), Japanese (beginner)

SKILLS
Music (piano, percussion, trombone, drums, voice, orchestration, arrangement, theory, production, composition)
Lesson planning/curriculum design
Technology (audio, signal processing, python, ML, AI)
Soft skills: listening, making others feel heard and empowered

AWARDS
- Education Through Music Fellowship (2009)
- UCLA Gluck Fellowship (2005)
- Martin Feldman Award (2000-2005)
- David A. Abell Jazz Award (2000-2005)
- Duke Ellington Jazz Award (2000-2005)
- CMEA Command Performance (1996-2000)
- Honorarium – New Journey Baptist Church (2009) (as Music Minister)
- Mensa Member, Los Angeles Chapter (2018)
*Music credits listed separately
"""

def analyze_resume(resume_content: str, job_title: str = None) -> Dict[str, Any]:
    """
    Analyze a resume and extract job information using Gemini directly.
    
    Args:
        resume_content: Resume text content
        job_title: Optional specific job title to extract information for
        
    Returns:
        Dictionary with extracted job information
    """
    # Define form fields
    form_fields = {
        "jobTitle": {
            "label": "Job Title",
            "type": "text",
            "id": "jobTitle",
            "required": True
        },
        "company": {
            "label": "Company",
            "type": "text",
            "id": "company",
            "required": True
        },
        "location": {
            "label": "Location",
            "type": "text",
            "id": "location",
            "required": False
        },
        "startDate": {
            "label": "Start Date",
            "type": "date",
            "id": "startDate",
            "required": True
        },
        "endDate": {
            "label": "End Date",
            "type": "date",
            "id": "endDate",
            "required": False
        },
        "currentlyWork": {
            "label": "I currently work here",
            "type": "checkbox",
            "id": "currentlyWork",
            "required": False
        },
        "description": {
            "label": "Description",
            "type": "textarea",
            "id": "description",
            "required": True
        },
        "skills": {
            "label": "Skills used",
            "type": "multi-select",
            "id": "skills",
            "required": False,
            "options": ["Teaching", "Curriculum Development", "Piano", "Music Theory", 
                        "Orchestration", "Conducting", "Management", "Leadership"]
        },
        "referenceContact": {
            "label": "Reference Contact Information",
            "type": "text",
            "id": "referenceContact",
            "required": False
        }
    }

    # Create example JSON
    example_json = '''{
      "jobTitle": "Studio Piano Teacher",
      "company": "California Conservatory of Music",
      "location": "Redwood City, CA",
      "startDate": "2023-09-01",
      "endDate": "2024-06-30",
      "currentlyWork": false,
      "description": "Created and implemented individual piano curricula for students aged 6-17.",
      "skills": ["Teaching", "Piano", "Curriculum Development", "Music Theory"],
      "referenceContact": "Chris Mallett, info@thecaliforniaconservatory.com"
    }'''
    
    # Create job instruction
    job_instruction = f"Please fill out the form for the job titled '{job_title}'." if job_title else "Please fill out the form for the most recent job experience."
    
    # Create the prompt
    prompt = f"""
    Task: Analyze the resume below and extract the most appropriate information to fill out a job application form.
    
    RESUME:
    {resume_content}
    
    FORM FIELDS TO FILL:
    {json.dumps(form_fields, indent=2)}
    
    {job_instruction}
    
    Important instructions:
    1. For date fields, use the format YYYY-MM-DD (e.g., 2023-09-01).
    2. For currentlyWork, if the job has an end date that is the current month and year or doesn't have an end date, set it to true.
    3. For description, include key responsibilities and achievements from the resume.
    4. For skills, select all applicable skills from the provided options that match the person's experience.
    5. For referenceContact, use supervisor information if available.
    
    Return your answer in valid JSON format with field names matching the form field IDs. Example:
    {example_json}
    """
    
    print(f"Analyzing resume for {job_title or 'most recent job'}...")
    
    # Call the Gemini API directly
    start_time = time.time()
    result = call_gemini_with_model_selection(prompt, "high", True)
    elapsed_time = time.time() - start_time
    
    print(f"Analysis completed in {elapsed_time:.2f} seconds.")
    print(f"Model used: {result.get('model_used', 'unknown')}")
    
    # Extract JSON from response
    if result["status"] == "success":
        try:
            # First, try to find JSON within the response
            import re
            response_text = result.get("response", "")
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            
            if json_match:
                form_data = json.loads(json_match.group(0))
                return form_data
            else:
                # If we can't find JSON pattern, try parsing the whole response
                form_data = json.loads(response_text)
                return form_data
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from response: {e}")
            print(f"Response text: {result.get('response', '')}")
            return {"error": "Failed to parse JSON from AI response"}
    else:
        print(f"Error from Gemini API: {result.get('response', '')}")
        return {"error": result.get("response", "Unknown error")}

def main():
    """Main function to test resume analysis."""
    if len(sys.argv) > 1:
        job_title = sys.argv[1]
        result = analyze_resume(RESUME_CONTENT, job_title)
    else:
        result = analyze_resume(RESUME_CONTENT)
    
    print("\nExtracted Job Information:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()