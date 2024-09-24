import requests
from bs4 import BeautifulSoup
import re

# scrapes the prerequisites and corequisites for a given course
def scrape_course_prerequisites(code, year):
    url_code = code.replace(" ", "").lower()
    course_url = f"https://catalog.utdallas.edu/{year}/undergraduate/courses/{url_code}"
    
    try:
        print(f"Fetching course prerequisites for course {url_code} from URL: {course_url}")
        response = requests.get(course_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # extract the section of text from the HTML that contains the course description
        description_section = soup.find("div", id="bukku-page").find("p")
        if not description_section:
            return {"prerequisites": [], "corequisites": []}

        description_text = description_section.get_text(" ", strip=True)

        prereq_text = extract_prerequisite_text(description_text)
        coreq_text = extract_corequisite_text(description_text)

        prerequisites = parse_courses_from_text(prereq_text) if prereq_text else []
        corequisites = parse_courses_from_text(coreq_text) if coreq_text else []

        return {"prerequisites": prerequisites, "corequisites": corequisites}

    except requests.exceptions.RequestException as e:
        print(f"Error fetching course prerequisites from {course_url}: {e}")
        return {"prerequisites": [], "corequisites": []}

# function to extract prerequisite text from "Prerequisite:" up to "Corequisite:" or the end of text
def extract_prerequisite_text(text):
    match = re.search(r"(Prerequisites?:\s*)([^\.]+)", text, re.IGNORECASE)
    if match:
        return match.group(2).strip()
    return None

# function to extract corequisite text from "Corequisite:" up to the first period
def extract_corequisite_text(text):
    match = re.search(r"(Corequisites?:\s*)([^\.]+)", text, re.IGNORECASE)
    if match:
        return match.group(2).strip()
    return None

# function to parse courses from the extracted req text
def parse_courses_from_text(text):
    course_groups = []
    current_group = []

    # match course codes with regex i.e. "MATH 2413" or "PHYS 2125"
    course_pattern = re.compile(r"([A-Z]+\s+\d+)")

    # split the text by "or" or "and" to separate the groups and parse the courses
    # note that "or" indicates the same group as the courses have equivalency in determining requisite satisfaction
    # "and" indicates a new group functioning and additional requisites
    tokens = re.split(r'(\s+or\s+|\s+and\s+)', text)

    for token in tokens:
        token = token.strip()
        
        course_match = course_pattern.findall(token)
        if course_match:
            current_group.extend(course_match)

        # if "and" is found, it indicates the end of a group
        if 'and' in token.lower():
            if current_group:
                course_groups.append(current_group)
                current_group = []

        # if "or" is found, continue adding to the same group
        elif 'or' in token.lower():
            continue

    # add any remaining group leftover
    if current_group:
        course_groups.append(current_group)

    # clean up course_groups by removing periods and trailing characters
    cleaned_course_groups = [[course.replace(".", "") for course in group] for group in course_groups]

    return cleaned_course_groups


# function to scrape the degree plan page
def scrape_degree_plan(url, year):
    print(f"Fetching degree plan from URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        core_curriculum_section = soup.find("p", id="degree-requirements")
        core_requirements = {}
        major_requirements = {}
        elective_requirements = {}

        core_curriculum_soup = None

        # this list will be used to store the courses that are part of the 090 Component Area Option
        # the courses listed under the category on the site are not all that apply, any course with an asterisk next to it
        # and the link to this section also should be counted as part of the 090 Component Area Option
        component_area_courses = []

        if core_curriculum_section:
            current_category = ""
            for sibling in core_curriculum_section.find_next_siblings():
                # Category title
                if sibling.name == "p" and "cat-reqg" in sibling.get("class", []):
                    current_category = sibling.get_text(strip=True)
                    core_requirements[current_category] = []

                # Course information or link to core curriculum page
                elif sibling.name == "p" and "cat-reqi" in sibling.get("class", []):
                    course_info = sibling.get_text(strip=True)
                    course_url = sibling.find("a", href=True)['href'] if sibling.find("a", href=True) else None

                    # If the URL links to the core curriculum page, fetch courses from there
                    if course_url and "/undergraduate/curriculum/core-curriculum" in course_url:
                        section_id = course_url.split("#")[1]

                        # Fetch the core curriculum page if it hasn't been fetched yet
                        if core_curriculum_soup is None:
                            core_curriculum_soup = fetch_core_curriculum_page(course_url)

                        # Scrape the specific section of the core curriculum page
                        if core_curriculum_soup:
                            core_courses = scrape_core_curriculum_section(core_curriculum_soup, section_id, year, component_area_courses)

                            # Add the core courses to the current category and handle the 090 Component Area Option
                            for course in core_courses:
                                if course not in core_requirements[current_category]:
                                    core_requirements[current_category].append(course)

                    else:
                        # Direct course info, append the parsed course
                        course_code_match = re.match(r"([A-Z]+\s+\d+)", course_info)
                        code = course_code_match.group(1) if course_code_match else None
                        if code:
                            course_entry = {
                                "course_info": code,
                                **scrape_course_prerequisites(code, year)
                            }
                            if course_entry not in core_requirements[current_category]:
                                core_requirements[current_category].append(course_entry)

                # Break on reaching the next section
                elif sibling.name == "p" and "cat-reqa" in sibling.get("class", []):
                    break
        
        # append collected courses to the Component Area Option aka Core 090
        component_area_key = next((key for key in core_requirements if "Component Area Option" in key), None)
        if component_area_key:
            core_requirements[component_area_key].extend(component_area_courses)

        # extract the major specific requirements, no external fetching needed for this section
        major_requirements_section = soup.find("p", text="II. Major Requirements: 72 semester credit hours")

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

        # parse elective section to find required credit hours
        elective_requirements_section = soup.find("p", text=re.compile(r"Elective Requirements"))
        if elective_requirements_section:
            match = re.search(r"(\d+) semester credit hours", elective_requirements_section.get_text())
            if match:
                elective_credits_required = int(match.group(1))
                elective_requirements = {"required_credit_hours": elective_credits_required}

        # combine into one dictionary to represent the whole degree plan to return
        return {
            "core_requirements": core_requirements,
            "major_requirements": major_requirements,
            "elective_requirements": elective_requirements
        }
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the degree plan: {e}")
        return None, None



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
def scrape_core_curriculum_section(soup, section_id, year, component_area_courses):
    core_courses = []
    core_section = soup.find(id=section_id)

    if core_section:
        for sibling in core_section.find_next_siblings():
            if sibling.name == "h3":
                break

            if sibling.name == "p" and "cat-reqi" in sibling.get("class", []):
                course_url = sibling.find('a', href=True)['href'] if sibling.find('a', href=True) else None

                if course_url:
                    course_code = course_url.split('/')[-1]
                    course_code_formatted = re.sub(r'([A-Z]+)(\d+)', r'\1 \2', course_code.upper())

                    # Detect asterisk for Component Area Option (090)
                    asterisk = sibling.find('a', href=True, text="*")
                    if asterisk and "090-component-area" in asterisk.get("href"):
                        component_area_courses.append({
                            "course_info": course_code_formatted,
                            **scrape_course_prerequisites(course_code_formatted, year)
                        })
                    
                    core_courses.append({
                        "course_info": course_code_formatted,
                        **scrape_course_prerequisites(course_code_formatted, year)
                    })

    return core_courses