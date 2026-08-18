import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys

# 1. Standard Chrome User-Agent to pass through firewall filters
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}
BASE_URL = "https://catalog.unt.edu"

def get_latest_catoid():
    """Dynamically finds the most recent UNT Undergraduate Catalog ID."""
    print("Fetching latest catalog ID...")
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        catalog_dropdown = soup.find('select', {'name': 'catalog'})
        if catalog_dropdown:
            for option in catalog_dropdown.find_all('option'):
                if "Undergraduate" in option.text:
                    return option['value']
    except Exception as e:
        print(f"Error fetching catalog ID: {e}")
    return None

def parse_prereqs(prereq_string):
    """Extracts standard course codes and flags complex logic."""
    if not prereq_string:
        return [], 0, False
        
    complex_flag = bool(re.search(r'\b(or|consent|equivalent|permission)\b', prereq_string.lower()))
    parsed_courses = re.findall(r'[A-Z]{3,4}\s\d{4}', prereq_string)
    
    return list(set(parsed_courses)), len(set(parsed_courses)), complex_flag

def fetch_all_courses(catoid):
    """Scrapes courses using Acalog wildcard search pagination."""
    
    # search_keyword=%20 acts as a wildcard search to display all course listings
    base_search_url = f"{BASE_URL}/search_advanced.php?cur_cat_oid={catoid}&search_database=Search&search_db=Search&filter%5Bitem_type%5D=3&filter%5Bonly_active%5D=1&search_keyword=%20&cpage="
    
    all_courses = []
    page = 1
    has_more_pages = True

    print(f"Starting production scrape for catalog ID: {catoid}...")

    while has_more_pages:
        print(f"Scanning search results page {page}...")
        url = f"{base_search_url}{page}"
        
        try:
            time.sleep(2)  # Rate limiting pause
            
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Match course preview links inside search results
            course_links = soup.find_all('a', href=re.compile(r'preview_course'))
            
            if not course_links:
                print("No more courses found. Pagination complete.")
                has_more_pages = False
                break

            found_on_page = 0
            for link in course_links:
                course_title_raw = link.text.strip()
                course_url = f"{BASE_URL}/{link['href']}" if not link['href'].startswith('http') else link['href']
                
                # Split "CSCE 1030 - Computer Science I" into code and title
                match = re.match(r'^([A-Z]{3,4}\s\d{4})\s*-\s*(.+)', course_title_raw)
                if not match:
                    continue 
                    
                code = match.group(1).strip()
                title = match.group(2).strip()
                found_on_page += 1

                time.sleep(1.2)  # Rate limiting pause for deep scraping
                
                try:
                    course_resp = requests.get(course_url, headers=HEADERS, timeout=10)
                    course_soup = BeautifulSoup(course_resp.text, 'html.parser')
                    
                    body_text = course_soup.text
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

            if found_on_page == 0:
                print("No valid course links on this page. Stopping.")
                break

            page += 1
            
        except requests.exceptions.RequestException as e:
            print(f"Network error on page {page}: {e}. Retrying in 10 seconds...")
            time.sleep(10)

    return all_courses

if __name__ == "__main__":
    catoid = get_latest_catoid()
    if not catoid:
        print("Fatal Error: Could not locate catalog ID.")
        sys.exit(1)
        
    final_data = fetch_all_courses(catoid)
    
    print(f"\n--- Scrape Complete! ---")
    print(f"Total courses successfully processed: {len(final_data)}")
    
    with open('electives.json', 'w') as f:
        json.dump(final_data, f, indent=4)
    print("electives.json saved to disk.")
