import requests
from bs4 import BeautifulSoup
import re
import json

# Function to scrape the prerequisite and corequisite information from a course page
def scrape_course_prerequisites(code, year):
    url_code = code.replace(" ", "").lower()
    course_url = f"https://catalog.utdallas.edu/{year}/undergraduate/courses/{url_code}"
    
    try:
        print(f"Fetching course prerequisites for course {url_code} from URL: {course_url}")
        response = requests.get(course_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # The prerequisites and corequisites will be inside a paragraph that contains the word "Prerequisite"
        description_section = soup.find("div", id="bukku-page").find("p")
        prerequisites = []
        corequisites = []

        if description_section:
            description_text = description_section.get_text(strip=True)

            # Extract prerequisites after "Prerequisite:"
            prereq_start = description_text.lower().find("prerequisite")
            if prereq_start != -1:
                prereq_text = description_text[prereq_start + len("prerequisite:"):].strip()
                prerequisites = extract_course_groups(prereq_text)

            # Extract corequisites after "Corequisite:"
            coreq_start = description_text.lower().find("corequisite")
            if coreq_start != -1:
                coreq_text = description_text[coreq_start + len("corequisite:"):].strip()
                corequisites = extract_course_groups(coreq_text)

        return {"prerequisites": prerequisites, "corequisites": corequisites}

    except requests.exceptions.RequestException as e:
        print(f"Error fetching course prerequisites from {course_url}: {e}")
        return {"prerequisites": [], "corequisites": []}


# Helper function to extract grouped course codes for prerequisites/corequisites
def extract_course_groups(text):
    course_groups = []
    course_group = []

    # Regex pattern to match course codes like "MATH 2413", "PHYS 2125", etc.
    course_pattern = re.compile(r"([A-Z]+\s+\d+)")
    
    # Split text into tokens by 'and' or 'or'
    tokens = re.split(r'(\s+or\s+|\s+and\s+)', text)

    for token in tokens:
        token = token.strip()
        course_match = course_pattern.findall(token)
        
        if course_match:
            # If "or" is present, group alternatives together in the same list
            if "or" in token.lower():
                course_group.extend(course_match)
            else:
                course_group.append(course_match[0])  # If "and", treat separately

        # If we encounter "and", close the group and append
        if "and" in token.lower() or '.' in token:
            if course_group:
                course_groups.append(course_group)
                course_group = []

    # Append any leftover group
    if course_group:
        course_groups.append(course_group)

    return course_groups


# function to fetch and store the HTML for the core curriculum page
def fetch_core_curriculum_page(url):
    full_url = "https://catalog.utdallas.edu" + url
    try:
        response = requests.get(full_url)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')  # Return the soup object
    except requests.exceptions.RequestException as e:
        print(f"Error scraping the core curriculum page: {e}")
        return None

# function to scrape a specific section from the core curriculum page
def scrape_core_curriculum_section(soup, section_id, year):
    core_courses = []
    core_section = soup.find(id=section_id)  # section of the page to scrape can be found by using the ID found in the url fragment

    if core_section:
        # iterate until reaching the next core section (h3)
        for sibling in core_section.find_next_siblings():
            if sibling.name == "h3":
                break

            if sibling.name == "p" and "cat-reqi" in sibling.get("class", []):
                # course_info = sibling.get_text(strip=True)
                course_url = sibling.find('a', href=True)['href'] if sibling.find('a', href=True) else None

                if course_url:
                    course_code = course_url.split('/')[-1]  # extract course code from the URL
                    course_code_formatted = re.sub(r'([A-Z]+)(\d+)', r'\1 \2', course_code.upper())  # add a space between the dpmt and num to match the transcript format
                    core_courses.append({
                        "course_info": course_code_formatted,
                        **scrape_course_prerequisites(course_code_formatted, year)
                    })
    return core_courses

# function to scrape the degree plan page
def scrape_degree_plan(url, year):
    print(f"Fetching degree plan from URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # start with the core curriculum section
        core_curriculum_section = soup.find("p", id="degree-requirements")
        core_requirements = {}

        core_curriculum_soup = None  # stores the fetched html for the core curriculum page, fetched only once

        if core_curriculum_section:
            current_category = ""
            for sibling in core_curriculum_section.find_next_siblings():
                if sibling.name == "p" and "cat-reqg" in sibling.get("class", []):
                    current_category = sibling.get_text(strip=True)
                    core_requirements[current_category] = []
                elif sibling.name == "p" and "cat-reqi" in sibling.get("class", []):
                    course_info = sibling.get_text(strip=True)
                    course_url = sibling.find("a", href=True)['href'] if sibling.find("a", href=True) else None

                    # if the url links to the core curriculum page, fetch the courses from there instead of adding it as a course
                    if course_url and "/undergraduate/curriculum/core-curriculum" in course_url:
                        section_id = course_url.split("#")[1]  # determine the section of the page to scrape using the fragment in the URL

                        # reuse the html if already fetched
                        if core_curriculum_soup is None:
                            core_curriculum_soup = fetch_core_curriculum_page(course_url)

                        # add courses from the core curriculum page if available
                        if core_curriculum_soup:
                            core_courses = scrape_core_curriculum_section(core_curriculum_soup, section_id, year)

                            # add the core courses if they werent already added from the degree plan page
                            for course in core_courses:
                                if course not in core_requirements[current_category]:
                                    core_requirements[current_category].append(course)
                    else:
                        # direct course, append the parsed course, prevent duplicates
                        course_code_match = re.match(r"([A-Z]+\s+\d+)", course_info)
                        code = course_code_match.group(1) if course_code_match else None
                        if course_code_match:
                            course_entry = {
                                "course_info": code,
                                **scrape_course_prerequisites(code, year)
                            }
                            if course_entry not in core_requirements[current_category]:
                                core_requirements[current_category].append(course_entry)
                elif sibling.name == "p" and "cat-reqa" in sibling.get("class", []):
                    break

        # extract the major specific requirements, no external fetching needed for this section
        major_requirements_section = soup.find("p", text="II. Major Requirements: 72 semester credit hours")
        major_requirements = {}

        if major_requirements_section:
            for sibling in major_requirements_section.find_next_siblings():
                if sibling.name == "p" and "cat-reqg" in sibling.get("class", []):
                    current_category = sibling.get_text(strip=True)
                    major_requirements[current_category] = []
                elif sibling.name == "p" and "cat-reqi" in sibling.get("class", []):
                    course_info = sibling.get_text(strip=True)
                    course_url = sibling.find("a", href=True)['href'] if sibling.find("a", href=True) else None
                    course_code_match = re.match(r"([A-Z]+\s+\d+)", course_info)
                    code = course_code_match.group(1) if course_code_match else None
                    if course_code_match:
                        course_entry = {
                            "course_info": code,
                            **scrape_course_prerequisites(code, year)
                        }
                        if course_entry not in major_requirements[current_category]:
                            major_requirements[current_category].append(course_entry)
                elif sibling.name == "p" and "cat-reqa" in sibling.get("class", []):
                    break

        return core_requirements, major_requirements

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the degree plan: {e}")
        return None, None

