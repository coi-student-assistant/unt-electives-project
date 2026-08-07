import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime

HEADERS = {"User-Agent": "UNT-Electives-Project-Bot/1.0"}
BASE_URL = "https://catalog.unt.edu"

def get_latest_catoid():
    """Dynamically finds the most recent UNT Undergraduate Catalog ID."""
    print("Fetching latest catalog ID...")
    response = requests.get(BASE_URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    catalog_dropdown = soup.find('select', {'name': 'catalog'})
    for option in catalog_dropdown.find_all('option'):
        if "Undergraduate" in option.text:
            return option['value']
    return None

def parse_prereqs(prereq_string):
    """Extracts standard course codes and flags complex logic."""
    if not prereq_string:
        return [], 0, False
        
    complex_flag = bool(re.search(r'\b(or|consent|equivalent|permission)\b', prereq_string.lower()))
    parsed_courses = re.findall(r'[A-Z]{3,4}\s\d{4}', prereq_string)
    
    return list(set(parsed_courses)), len(set(parsed_courses)), complex_flag

def fetch_course_data(catoid, prefix="CSCE"):
    """Scrapes courses for a specific prefix using the active catoid."""
    # Note: In production, you will route through Acalog's search/portfolio endpoints
    # This is the structural logic for hitting the catalog search results
    search_url = f"{BASE_URL}/content.php?catoid={catoid}&navoid=search&search={prefix}"
    
    print(f"Scraping {prefix} courses...")
    # time.sleep(1) # Protect against rate limiting
    
    # Mocking the parsed response for demonstration
    courses = [
        {
            "code": "CSCE 3550",
            "title": "Introduction to Computer Security",
            "prereq_raw": "CSCE 2100 or CSCE 2110 with a C or better.",
            "description": "Basic concepts of computer security...",
            "catalog_url": f"{BASE_URL}/preview_course.php?catoid={catoid}&coid=12345"
        },
        {
            "code": "CSCE 4010",
            "title": "Social Issues in Computing",
            "prereq_raw": "CSCE 3110.",
            "description": "Impact of computers on society...",
            "catalog_url": f"{BASE_URL}/preview_course.php?catoid={catoid}&coid=12346"
        }
    ]
    
    processed_courses = []
    for c in courses:
        parsed, count, is_complex = parse_prereqs(c["prereq_raw"])
        
        # Here you would integrate the FacultyInfo scraping logic 
        # using datetime lookback to check occurrences over the last 30 months.
        # Stubbed here for the pipeline:
        typical_terms = ["Fall", "Spring"] if c["code"] == "CSCE 3550" else ["Fall Only"]
        
        processed_courses.append({
            "code": c["code"],
            "title": c["title"],
            "prereqs_parsed": parsed,
            "prereq_count": count,
            "complex_prereq": is_complex,
            "offered_terms": typical_terms,
            "catalog_url": c["catalog_url"]
        })
    return processed_courses

if __name__ == "__main__":
    catoid = get_latest_catoid()
    if not catoid:
        raise Exception("Could not locate catalog ID.")
        
    final_data = fetch_course_data(catoid, "CSCE")
    
    with open('electives.json', 'w') as f:
        json.dump(final_data, f, indent=4)
    print("electives.json updated successfully.")
