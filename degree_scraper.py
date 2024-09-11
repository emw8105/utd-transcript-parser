import requests
from bs4 import BeautifulSoup

# Function to construct the degree plan URL
def construct_degree_plan_url(major, school, program_start_date):
    formatted_major = major.lower().replace(" ", "-")
    year = program_start_date.split("-")[0]

    url = f"https://catalog.utdallas.edu/{year}/undergraduate/programs/{school}/{formatted_major}"
    return url

# Function to scrape the degree plan page
def scrape_degree_plan(url):
    print(f"Fetching degree plan from URL: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract Core Curriculum Requirements
        core_curriculum_section = soup.find("p", id="degree-requirements")
        core_requirements = []

        if core_curriculum_section:
            current_category = ""
            for sibling in core_curriculum_section.find_next_siblings():
                if sibling.name == "p" and "cat-reqg" in sibling.get("class", []):
                    current_category = sibling.get_text(strip=True)
                elif sibling.name == "p" and "cat-reqi" in sibling.get("class", []):
                    course_info = sibling.get_text(strip=True)
                    course_url = sibling.find("a", href=True)['href'] if sibling.find("a", href=True) else None
                    core_requirements.append({
                        "category": current_category,
                        "course_info": course_info,
                        "course_url": course_url
                    })
                elif sibling.name == "p" and "cat-reqa" in sibling.get("class", []):
                    break  # Stop after Core Curriculum Requirements section is over

        # Extract Major Requirements
        major_requirements_section = soup.find("p", text="II. Major Requirements: 72 semester credit hours")
        major_requirements = []

        if major_requirements_section:
            for sibling in major_requirements_section.find_next_siblings():
                if sibling.name == "p" and "cat-reqg" in sibling.get("class", []):
                    current_category = sibling.get_text(strip=True)
                elif sibling.name == "p" and "cat-reqi" in sibling.get("class", []):
                    course_info = sibling.get_text(strip=True)
                    course_url = sibling.find("a", href=True)['href'] if sibling.find("a", href=True) else None
                    major_requirements.append({
                        "category": current_category,
                        "course_info": course_info,
                        "course_url": course_url
                    })
                elif sibling.name == "p" and "cat-reqa" in sibling.get("class", []):
                    break  # Stop after Major Requirements section is over

        return core_requirements, major_requirements

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the degree plan: {e}")
        return None, None
