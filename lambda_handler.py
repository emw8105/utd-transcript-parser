import pdfplumber
import re
import json
import time

# hardcoded mapping of majors to their associated schools
school_mapping = {
    "Computer Science": "ecs",
    "Software Engineering": "ecs",
    "Computer Engineering": "ecs",
    "Electrical Engineering": "ecs",
    "Mechanical Engineering": "ecs",
    "Biomedical Engineering": "ecs",
    "Finance": "jsom",
    "Accounting": "jsom",
    "Information Systems": "jsom",
    "Marketing": "jsom"
}

def extract_transcript_data(pdf_path):

    # open the PDF and read its content
    with pdfplumber.open(pdf_path) as pdf:
        transcript_text = ""

        # extract text from each page and remove headers/footers
        for page in pdf.pages:
            page_text = page.extract_text()
            lines = page_text.split('\n')
            lines = [line for line in lines if not re.match(r"^\d+\s+\d+.*$", line)
                     and not line.startswith("Unofficial Transcript - UT-Dallas")
                     and not line.startswith("Name:")]
            transcript_text += '\n'.join(lines) + '\n'

    # json object to store the extracted data
    transcript_data = {}

    # extract student name
    name_match = re.search(r"Name:\s+([\w\s]+)", transcript_text)
    if name_match:
        transcript_data['name'] = name_match.group(1).strip()

    # extract UTD ID
    id_match = re.search(r"Student ID:\s+(\d+)", transcript_text)
    if id_match:
        transcript_data['utd_id'] = id_match.group(1)

    # extract major, will need to be modified for assigning major to school (i.e. CS --> ECS)
    major_match = re.search(r":\s+(.*) Major", transcript_text)
    if major_match:
        transcript_data['major'] = major_match.group(1).strip()
        transcript_data['school'] = school_mapping.get(transcript_data['major'], "Unknown")

    # extract GPA
    gpa_match = re.search(r"Cum GPA:\s+([\d\.]+)", transcript_text)
    if gpa_match:
        transcript_data['gpa'] = float(gpa_match.group(1))

    # extract the program start date, i.e. when the student started pursuing their degree
    start_date_match = re.search(r"(\d{4}-\d{2}-\d{2}): Active in Program", transcript_text)
    if start_date_match:
        transcript_data['program_start_date'] = start_date_match.group(1)


    # course storage structure, divided into transfer credits, test credits, and UTD classes based on transcript format
    transcript_data['courses'] = {
        'transfer_credits': [],
        'test_credits': [],
        'utd_classes': {}
    }

    lines = transcript_text.split('\n')
    current_section = None
    current_semester = None

    # parse line-by-line to extract course data
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # check for section changes and 
        if line == "Transfer Credits":
            current_section = "transfer_credits"
            i += 1
            continue
        elif line == "Test Credits":
            current_section = "test_credits"
            i += 1
            continue
        elif line == "Beginning of Undergraduate Record":
            current_section = "utd_classes"
            i += 1
            continue
        elif re.match(r"^\d{4} (Fall|Spring|Summer)$", line):
            current_semester = line
            if current_section == "utd_classes":
                if current_semester not in transcript_data['courses']['utd_classes']:
                    transcript_data['courses']['utd_classes'][current_semester] = []
            i += 1
            if i < len(lines) and "Course Description" in lines[i]:
                i += 1
            continue
        elif line.startswith("Course Description"):
            i += 1
            continue

        # grab the course data using regex
        course_line_pattern = r"^([A-Z]+\s+[\w\-]+)\s+(.+?)\s+([\d\.]+)\s+([\d\.]+)(?:\s+([A-Z\+\-]+))?(?:\s+([\d\.]+))?$"
        course_match = re.match(course_line_pattern, line)
        if course_match:
            course_code = course_match.group(1)
            course_name = course_match.group(2).strip()
            credits_attempted = float(course_match.group(3))
            credits_earned = float(course_match.group(4))
            grade = course_match.group(5) if course_match.group(5) else "In Progress"
            # in-progress courses don't have points/grades
            # points = float(course_match.group(6)) if course_match.group(6) else None

            course = {
                'course_code': course_code,
                'course_name': course_name,
                'credits_attempted': credits_attempted,
                'credits_earned': credits_earned,
                'grade': grade
            }

            if current_section == "transfer_credits":
                transcript_data['courses']['transfer_credits'].append(course)
            elif current_section == "test_credits":
                transcript_data['courses']['test_credits'].append(course)
            elif current_section == "utd_classes":
                if current_semester:
                    transcript_data['courses']['utd_classes'][current_semester].append(course)
        i +=1

    return transcript_data

# load transcript and extract data, hardcoded to this directory for now but will be passed in eventually
pdf_path = "SSR_TSRPT - Michael.pdf"

start_time = time.time() # benchmarking for the time taken to parse the transcript
transcript_data = extract_transcript_data(pdf_path)
end_time = time.time()  # end the timer, currently saving to the json to workaround function return values

# Print data as JSON
print(json.dumps(transcript_data, indent=4))
transcript_file = open("transcript_data.json", "w")
transcript_file.write(json.dumps(transcript_data, indent=4))
transcript_file.close()

print(f"Transcript parsing took {round(end_time - start_time, 2)} seconds")
