import pdfplumber
import re

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
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            lines = page_text.split('\n')
            
            # For the first page, don't filter out the "Name" header line
            if i == 0:
                lines = [line for line in lines if not re.match(r"^\d+\s+\d+.*$", line)
                         and not line.startswith("Unofficial Transcript - UT-Dallas")]
            else:
                # For subsequent pages, filter out the repeated headers/footers
                lines = [line for line in lines if not re.match(r"^\d+\s+\d+.*$", line)
                         and not line.startswith("Unofficial Transcript - UT-Dallas")
                         and not line.startswith("Name:")]

            transcript_text += '\n'.join(lines) + '\n'

    # json object to store the extracted data
    transcript_data = {}

    # extract student name
    name_match = re.search(r"Name:\s+(.+)", transcript_text)
    if name_match:
        transcript_data['name'] = name_match.group(1).strip()

    # extract UTD ID
    id_match = re.search(r"Student ID:\s+(\d+)", transcript_text)
    if id_match:
        transcript_data['utd_id'] = id_match.group(1)

    # extract major and assign school
    major_match = re.search(r":\s+(.*) Major", transcript_text)
    if major_match:
        transcript_data['major'] = major_match.group(1).strip()
        transcript_data['school'] = school_mapping.get(transcript_data['major'], "Unknown")

    # extract GPA
    gpa_match = re.search(r"Cum GPA:\s+([\d\.]+)", transcript_text)
    if gpa_match:
        transcript_data['gpa'] = float(gpa_match.group(1))

    # extract the program start date
    start_date_match = re.search(r"(\d{4}-\d{2}-\d{2}): Active in Program", transcript_text)
    if start_date_match:
        transcript_data['program_start_date'] = start_date_match.group(1)

    # course storage structure
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
        if line == "Transfer Credits":
            current_section = "transfer_credits"
        elif line == "Test Credits":
            current_section = "test_credits"
        elif line == "Beginning of Undergraduate Record":
            current_section = "utd_classes"
        elif re.match(r"^\d{4} (Fall|Spring|Summer)$", line):
            current_semester = line
            if current_section == "utd_classes":
                transcript_data['courses']['utd_classes'].setdefault(current_semester, [])
            i += 1
            if i < len(lines) and "Course Description" in lines[i]:
                i += 1
            continue

        course_line_pattern = r"^([A-Z]+\s+[\w\-]+)\s+(.+?)\s+([\d\.]+)\s+([\d\.]+)(?:\s+([A-Z\+\-]+))?"
        course_match = re.match(course_line_pattern, line)
        if course_match:
            course_code = course_match.group(1)
            course_name = course_match.group(2).strip()
            credits_attempted = float(course_match.group(3))
            credits_earned = float(course_match.group(4))
            grade = course_match.group(5) if course_match.group(5) else "In Progress"

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
                transcript_data['courses']['utd_classes'][current_semester].append(course)

        i += 1

    return transcript_data
