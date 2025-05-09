#!/usr/bin/env python3
"""
Test script for evaluating the form-filling capabilities of our multi-agent system.
This script tests the ability to extract relevant information from a resume and
correctly populate job application forms.
"""
import requests
import json
import os
import time
from typing import Dict, Any, List

# Define endpoints
BASE_URL = "http://localhost:5000"
GEMINI_URL = f"{BASE_URL}/gemini"

# Sample job application form fields
JOB_APPLICATION_FORM = {
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
        "options": ["Teaching", "Curriculum Development", "Piano", "Music Theory", "Orchestration", "Conducting", "Management", "Leadership"]
    },
    "referenceContact": {
        "label": "Reference Contact Information",
        "type": "text",
        "id": "referenceContact",
        "required": False
    }
}

# Resume content for William White
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

# HTML form elements for the job application
JOB_APPLICATION_HTML = """
<form class="job-application-form">
    <div class="form-group">
        <label for="jobTitle">Job Title *</label>
        <input aria-invalid="false" id="jobTitle" name="jobTitle" data-testid="jobTitle" type="text" autocomplete="organization-title" aria-autocomplete="both" class="css-lwkpjt e1jgz0i3" value="">
    </div>
    
    <div class="form-group">
        <label for="company">Company *</label>
        <input aria-invalid="false" id="company" name="company" data-testid="company" type="text" autocomplete="organization" aria-autocomplete="both" class="css-lwkpjt e1jgz0i3" value="">
    </div>
    
    <div class="form-group">
        <label for="startDate">Start Date *</label>
        <input aria-invalid="false" id="startDate" name="startDate" data-testid="startDate" type="date" class="css-lwkpjt e1jgz0i3" value="">
    </div>
    
    <div class="form-group">
        <label for="endDate">End Date</label>
        <input aria-invalid="false" id="endDate" name="endDate" data-testid="endDate" type="date" class="css-lwkpjt e1jgz0i3" value="">
    </div>
    
    <div class="form-group checkbox">
        <input type="checkbox" id="currentlyWork" name="currentlyWork" value="true">
        <label for="currentlyWork">I currently work here</label>
    </div>
    
    <div class="form-group">
        <label for="description">Description *</label>
        <textarea aria-invalid="false" id="description" name="description" data-testid="description" rows="4" class="css-lwkpjt e1jgz0i3"></textarea>
    </div>
    
    <div class="form-group">
        <label for="skills">Skills used</label>
        <select multiple id="skills" name="skills" data-testid="skills" class="css-lwkpjt e1jgz0i3">
            <option value="Teaching">Teaching</option>
            <option value="Curriculum Development">Curriculum Development</option>
            <option value="Piano">Piano</option>
            <option value="Music Theory">Music Theory</option>
            <option value="Orchestration">Orchestration</option>
            <option value="Conducting">Conducting</option>
            <option value="Management">Management</option>
            <option value="Leadership">Leadership</option>
        </select>
    </div>
    
    <div class="form-group">
        <label for="referenceContact">Reference Contact Information</label>
        <input aria-invalid="false" id="referenceContact" name="referenceContact" data-testid="referenceContact" type="text" class="css-lwkpjt e1jgz0i3" value="">
    </div>
</form>
"""

def analyze_resume_and_fill_form(resume_content: str, form_fields: Dict[str, Any], job_title_to_fill: str = None) -> Dict[str, Any]:
    """
    Use the AI system to analyze a resume and determine the appropriate values for job application form fields.
    
    Args:
        resume_content: The text content of the resume
        form_fields: Dictionary describing the form fields
        job_title_to_fill: Optional specific job title to fill out (will use most recent if None)
        
    Returns:
        Dictionary of filled form fields
    """
    # Create a prompt for the AI system
    prompt = f"""
    Task: Analyze the resume below and extract the most appropriate information to fill out the job application form fields.
    
    RESUME:
    {resume_content}
    
    FORM FIELDS TO FILL (in JSON format):
    {json.dumps(form_fields, indent=2)}
    
    HTML FORM:
    {JOB_APPLICATION_HTML}
    
    {"Please fill out the form for the job titled '" + job_title_to_fill + "'." if job_title_to_fill else "Please fill out the form for the most recent job experience."}
    
    Important instructions:
    1. For date fields, use the format YYYY-MM-DD (e.g., 2023-09-01).
    2. For currentlyWork, if the job has an end date that is the current month and year or doesn't have an end date, set it to true.
    3. For description, include key responsibilities and achievements from the resume.
    4. For skills, select all applicable skills from the options that match the person's experience.
    5. For referenceContact, use supervisor information if available.
    
    Return your answer in valid JSON format with field names matching the form field IDs. Example:
    {
      "jobTitle": "Studio Piano Teacher",
      "company": "California Conservatory of Music",
      "startDate": "2023-09-01",
      "endDate": "2024-06-30",
      "currentlyWork": false,
      "description": "Created and implemented individual piano curricula for students aged 6-17.",
      "skills": ["Teaching", "Piano", "Curriculum Development", "Music Theory"],
      "referenceContact": "Chris Mallett, info@thecaliforniaconservatory.com"
    }
    """
    
    try:
        # Call the Gemini API to analyze the resume and fill the form
        print("Sending request to Gemini API...")
        response = requests.post(
            GEMINI_URL,
            json={"prompt": prompt, "priority": "high", "verbose": True},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Successfully received response from model: {data.get('model_used', 'unknown')}")
            
            # Extract the JSON from the response text
            response_text = data.get("response", "")
            
            # Try to extract JSON from the response text
            try:
                # First, try to find JSON within the response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    form_data = json.loads(json_match.group(0))
                else:
                    # If we can't find JSON pattern, try parsing the whole response
                    form_data = json.loads(response_text)
                
                return form_data
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON from response: {e}")
                print(f"Response text: {response_text}")
                return {"error": "Failed to parse JSON from AI response", "raw_response": response_text}
        else:
            print(f"Error from Gemini API: {response.status_code} - {response.text}")
            return {"error": f"API error: {response.status_code}", "details": response.text}
    
    except Exception as e:
        print(f"Exception calling Gemini API: {e}")
        return {"error": f"Exception: {str(e)}"}

def validate_form_data(form_data: Dict[str, Any], form_fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the form data returned by the AI against the expected form fields.
    
    Args:
        form_data: The form data returned by the AI
        form_fields: The expected form fields
        
    Returns:
        Dictionary with validation results
    """
    validation_results = {
        "valid": True,
        "missing_required": [],
        "incorrect_format": [],
        "overall_score": 0,
        "fields_checked": 0
    }
    
    # Check for missing required fields
    for field_id, field_info in form_fields.items():
        validation_results["fields_checked"] += 1
        
        if field_info.get("required", False) and (field_id not in form_data or not form_data[field_id]):
            validation_results["valid"] = False
            validation_results["missing_required"].append(field_id)
    
    # Check date formats
    date_fields = ["startDate", "endDate"]
    for field in date_fields:
        if field in form_data and form_data[field]:
            import re
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(form_data[field])):
                validation_results["valid"] = False
                validation_results["incorrect_format"].append(f"{field} (should be YYYY-MM-DD)")
    
    # Check if skills are from the available options
    if "skills" in form_data and form_data["skills"]:
        available_skills = form_fields["skills"]["options"]
        for skill in form_data["skills"]:
            if skill not in available_skills:
                validation_results["valid"] = False
                validation_results["incorrect_format"].append(f"skill '{skill}' not in available options")
    
    # Calculate an overall score
    if validation_results["fields_checked"] > 0:
        errors = len(validation_results["missing_required"]) + len(validation_results["incorrect_format"])
        validation_results["overall_score"] = 100 * (1 - errors / validation_results["fields_checked"])
    
    return validation_results

def run_form_filling_test(job_title: str = None, output_file: str = None) -> Dict[str, Any]:
    """
    Run a test of the form-filling capability.
    
    Args:
        job_title: Specific job title to fill out form for (will use most recent if None)
        output_file: Optional file to save the results to
        
    Returns:
        Dictionary with test results
    """
    print(f"\nStarting form-filling test{' for ' + job_title if job_title else ''}")
    
    start_time = time.time()
    
    # Analyze resume and fill form
    filled_form = analyze_resume_and_fill_form(RESUME_CONTENT, JOB_APPLICATION_FORM, job_title)
    
    # Validate the filled form
    validation_results = validate_form_data(filled_form, JOB_APPLICATION_FORM)
    
    elapsed_time = time.time() - start_time
    
    # Format test results
    test_results = {
        "job_title_requested": job_title,
        "filled_form": filled_form,
        "validation": validation_results,
        "elapsed_time": elapsed_time
    }
    
    # Output results
    print("\nForm Filling Results:")
    print(f"  Time taken: {elapsed_time:.2f} seconds")
    print(f"  Valid: {validation_results['valid']}")
    print(f"  Score: {validation_results['overall_score']:.1f}%")
    
    if validation_results["missing_required"]:
        print(f"  Missing required fields: {', '.join(validation_results['missing_required'])}")
    
    if validation_results["incorrect_format"]:
        print(f"  Incorrect format: {', '.join(validation_results['incorrect_format'])}")
    
    print("\nFilled Form Data:")
    print(json.dumps(filled_form, indent=2))
    
    # Save to file if requested
    if output_file:
        try:
            with open(output_file, "w") as f:
                json.dump(test_results, f, indent=2)
            print(f"\nResults saved to {output_file}")
        except Exception as e:
            print(f"Error saving results to file: {e}")
    
    return test_results

def main():
    """Main entry point for the test script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the form-filling capabilities of the multi-agent system")
    parser.add_argument("--job", type=str, help="Specific job title to fill out form for")
    parser.add_argument("--output", "-o", type=str, help="Output file for test results")
    
    args = parser.parse_args()
    
    # Create output directory if needed
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    
    # Run the test
    run_form_filling_test(args.job, args.output)

if __name__ == "__main__":
    main()