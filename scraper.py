import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}
BASE_URL = "https://catalog.unt.edu"

def get_catalog_and_nav_ids():
    """Finds the active Undergraduate Catalog ID (catoid) and Course Descriptions ID (navoid)."""
    print("Fetching UNT catalog IDs...")
    try:
        resp = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. Extract Undergraduate Catalog ID
        catoid = None
        catalog_dropdown = soup.find('select', {'name': 'catalog'})
        if catalog_dropdown:
            for option in catalog_dropdown.find_all('option'):
                if "Undergraduate" in option.text:
                    catoid = option['value']
                    break
        
        if not catoid:
            return None, None

        # 2. Extract "Course Descriptions" navoid link from main menu
        navoid = None
        catalog_url = f"{BASE_URL}/index.php?catoid={catoid}"
        nav_resp = requests.get(catalog_url, headers=HEADERS, timeout=15)
        nav_soup = BeautifulSoup(nav_resp.text, 'html.parser')
        
        for link in nav_soup.find_all('a', href=True):
            if "Course Descriptions" in link.text:
                match = re.search(r'navoid=(\d+)', link['href'])
                if match:
                    navoid = match.group(1)
                    break

        return catoid, navoid

    except Exception as e:
        print(f"Error fetching IDs: {e}")
        return None, None

def parse_prereqs(prereq_string):
    """Extracts course codes and flags complex prerequisite logic."""
    if not prereq_string:
        return [], 0, False
        
    complex_flag = bool(re.search(r'\b(or|consent|equivalent|permission)\b', prereq_string.lower()))
    parsed_courses = re.findall(r'[A-Z]{3,4}\s\d{4}', prereq_string)
    
    return list(set(parsed_courses)), len(set(parsed_courses)), complex_flag

def fetch_all_courses(catoid, navoid):
    """Paginates directly through Acalog Course Descriptions content pages."""
    base_url = f"{BASE_URL}/content.php?catoid={catoid}&navoid={navoid}&cpage="
    all_courses = []
    page = 1

    print(f"Starting scrape for Catoid: {catoid}, Navoid: {navoid}...")

    while True:
        print(f"Scanning Course Descriptions page {page}...")
        url = f"{base_url}{page}"
        
        try:
            time.sleep(2)  # Rate limiting pause
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract course preview links
            course_links = soup.find_all('a', href=re.compile(r'preview_course'))
            
            if not course_links:
                print("No more course links found. Scrape complete.")
                break

            processed_on_page = 0
            for link in course_links:
                course_title_raw = link.text.strip()
                course_href = link['href']
                course_url = f"{BASE_URL}/{course_href}" if not course_href.startswith('http') else course_href
                
                # Split "CSCE 1030 - Computer Science I" into code and title
                match = re.match(r'^([A-Z]{3,4}\s\d{4})\s*-\s*(.+)', course_title_raw)
                if not match:
                    continue
                    
                code = match.group(1).strip()
                title = match.group(2).strip()
                processed_on_page += 1

                time.sleep(1.2)  # Deep-scrape pause
                
                try:
                    c_resp = requests.get(course_url, headers=HEADERS, timeout=10)
                    c_soup = BeautifulSoup(c_resp.text, 'html.parser')
                    
                    body_text = c_soup.text
                    prereq_raw = ""
                    prereq_match = re.search(r'Prerequisite\(s\):(.*?)(\n|<|$)', body_text)
                    if prereq_match:
                        prereq_raw = prereq_match.group(1).strip()
                        
                    parsed, count, is_complex = parse_prereqs(prereq_raw)
                    
                    all_courses.append({
                        "code": code,
                        "title": title,
                        "prereqs_parsed": parsed,
                        "prereq_count": count,
                        "complex_prereq": is_complex,
                        "offered_terms": ["Check Catalog"], 
                        "catalog_url": course_url
                    })
                except Exception as inner_e:
                    print(f"Failed to deep-scrape {code}: {inner_e}")
                    continue

            if processed_on_page == 0:
                print("No valid courses matching criteria on page. Stopping.")
                break

            page += 1

        except requests.exceptions.RequestException as e:
            print(f"Network error on page {page}: {e}. Retrying in 10s...")
            time.sleep(10)

    return all_courses

if __name__ == "__main__":
    catoid, navoid = get_catalog_and_nav_ids()
    if not catoid or not navoid:
        print("Fatal Error: Could not resolve Catalog ID or Course Descriptions Navoid.")
        sys.exit(1)
        
    final_data = fetch_all_courses(catoid, navoid)
    
    print(f"\n--- Scrape Complete! ---")
    print(f"Total courses processed: {len(final_data)}")
    
    with open('electives.json', 'w') as f:
        json.dump(final_data, f, indent=4)
    print("electives.json saved to disk.")
