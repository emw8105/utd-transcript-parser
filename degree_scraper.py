import requests
from bs4 import BeautifulSoup
import re
import json

# function to construct the degree plan URL
def construct_degree_plan_url(major, school, program_start_date):
    formatted_major = major.lower().replace(" ", "-")
    year = program_start_date.split("-")[0]
    url = f"https://catalog.utdallas.edu/{year}/undergraduate/programs/{school}/{formatted_major}"
    return url

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
def scrape_core_curriculum_section(soup, section_id):
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
                    })
    return core_courses

# function to scrape the degree plan page
def scrape_degree_plan(url):
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
                            core_courses = scrape_core_curriculum_section(core_curriculum_soup, section_id)

                            # add the core courses if they werent already added from the degree plan page
                            for course in core_courses:
                                if course not in core_requirements[current_category]:
                                    core_requirements[current_category].append(course)
                    else:
                        # direct course, append the parsed course, prevent duplicates
                        # WILL NEED TO WEBSCRAPE FOR THAT COURSE TO FIND THE PREREQS
                        course_code_match = re.match(r"([A-Z]+\s+\d+)", course_info)
                        if course_code_match:
                            course_entry = {
                                "course_info": course_code_match.group(1),
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
                    if course_code_match:
                        course_entry = {
                            "course_info": course_code_match.group(1),
                            "course_url": course_url
                        }
                        if course_entry not in major_requirements[current_category]:
                            major_requirements[current_category].append(course_entry)
                elif sibling.name == "p" and "cat-reqa" in sibling.get("class", []):
                    break

        return core_requirements, major_requirements

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the degree plan: {e}")
        return None, None

# function to build and fetch the degree plan based on the transcript data
def build_and_fetch_degree_plan(transcript_data):
    major = transcript_data['major']
    school = transcript_data['school']
    program_start_date = transcript_data['program_start_date']

    url = construct_degree_plan_url(major, school, program_start_date)

    # scrape and print the degree plan contents
    core_requirements, major_requirements = scrape_degree_plan(url)

    if core_requirements and major_requirements:
        # POSSIBLY TEMP (may get saved to Student's dynamo table info) - save the degree plan to a JSON file
        degree_plan_data = {
            "core_requirements": core_requirements,
            "major_requirements": major_requirements
        }

        with open("degree_plan_data.json", "w") as outfile:
            json.dump(degree_plan_data, outfile, indent=4)

        print("\nDegree plan data saved to degree_plan_data.json")

