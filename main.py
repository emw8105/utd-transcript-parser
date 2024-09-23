import json
import time
from transcript_parser import extract_transcript_data
from degree_scraper import scrape_degree_plan

# Main function to load and process transcript, then fetch degree plan
def main():
    pdf_path = "SSR_TSRPT.pdf"

    # extract transcript data
    start_time = time.time()
    transcript_data = extract_transcript_data(pdf_path)
    end_time = time.time()
    print(f"Transcript parsing took {round(end_time - start_time, 2)} seconds")

    # TEMP: save transcript data to a JSON file for reference
    with open("transcript_data.json", "w") as transcript_file:
        json.dump(transcript_data, transcript_file, indent=4)

    # build the degree plan URL for the student's corresponding major
    major = transcript_data['major']
    school = transcript_data['school']
    program_start_date = transcript_data['program_start_date']

    # function to construct the degree plan URL
    formatted_major = major.lower().replace(" ", "-")
    year = program_start_date.split("-")[0]
    url = f"https://catalog.utdallas.edu/{year}/undergraduate/programs/{school}/{formatted_major}"

    ########################################################
    # scrape the degree plan from the URL
    start_time = time.time()
    degree_plan_data = scrape_degree_plan(url, year)
    end_time = time.time()
    print(f"Degree plan retrieval took {round(end_time - start_time, 2)} seconds")

    if degree_plan_data:

        # TEMP: save the degree plan to a JSON file, in the future will probably be saved to dyanmo table entry for the student
        with open("degree_plan_data.json", "w") as degree_plan_file:
            json.dump(degree_plan_data, degree_plan_file, indent=4)
        print("\nDegree plan data has been saved to 'degree_plan_data.json'.")
    else:
        print("Failed to fetch the degree plan. Please check the URL or internet connection.")

    ########################################################

    # TEMP: loading the degree plan from the previously saved JSON file to avoid doing the web scraping every time
    try:
        with open("degree_plan_data.json", "r") as degree_plan_file:
            degree_plan_data = json.load(degree_plan_file)
        print("Degree plan data successfully loaded from JSON.")
    except FileNotFoundError:
        print(f"File not found. Please make sure the file exists.")
    
    
    # compare the transcript data with the degree plan



if __name__ == "__main__":
    main()
