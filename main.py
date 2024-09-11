import json
import time
from transcript_parser import extract_transcript_data
from degree_scraper import construct_degree_plan_url, scrape_degree_plan

# Main function to load and process transcript, then fetch degree plan
def main():
    pdf_path = "SSR_TSRPT.pdf"

    # Extract transcript data
    start_time = time.time()
    transcript_data = extract_transcript_data(pdf_path)
    end_time = time.time()
    print(f"Transcript parsing took {round(end_time - start_time, 2)} seconds")

    # Save transcript data to a JSON file for reference
    with open("transcript_data.json", "w") as transcript_file:
        json.dump(transcript_data, transcript_file, indent=4)

    # Build the degree plan URL and scrape the degree plan
    major = transcript_data['major']
    school = transcript_data['school']
    program_start_date = transcript_data['program_start_date']

    # Construct degree plan URL
    url = construct_degree_plan_url(major, school, program_start_date)

    # Scrape the degree plan
    core_requirements, major_requirements = scrape_degree_plan(url)

    # Output the scraped degree plan data to console
    if core_requirements and major_requirements:
        print("\nCore Curriculum Requirements:")
        for core in core_requirements:
            print(f"Category: {core['category']}, Course Info: {core['course_info']}, URL: {core['course_url']}")

        print("\nMajor Requirements:")
        for major in major_requirements:
            print(f"Category: {major['category']}, Course Info: {major['course_info']}, URL: {major['course_url']}")

        # Save the degree plan to a JSON file
        degree_plan_data = {
            "core_requirements": core_requirements,
            "major_requirements": major_requirements
        }
        with open("degree_plan_data.json", "w") as degree_plan_file:
            json.dump(degree_plan_data, degree_plan_file, indent=4)
        print("\nDegree plan data has been saved to 'degree_plan_data.json'.")
    else:
        print("Failed to fetch the degree plan. Please check the URL or internet connection.")

# Run the main function when the script is executed
if __name__ == "__main__":
    main()
