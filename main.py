import json
import time
from transcript_parser import extract_transcript_data
from degree_scraper import scrape_degree_plan
from degree_plan_evaluator import DegreePlanEvaluator

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

    # commented to test the degree plan completion without the need to scrape the website, results are saved in degree_plan_data.json
    # scrape the degree plan from the URL
    start_time = time.time()
    degree_plan_data = scrape_degree_plan(url, year)
    end_time = time.time()
    print(f"Degree plan retrieval took {round(end_time - start_time, 2)} seconds")

    if degree_plan_data:
        with open("degree_plan_data.json", "w") as degree_plan_file:
            json.dump(degree_plan_data, degree_plan_file, indent=4)
        print("Degree plan data saved to 'degree_plan_data.json'.")
    else:
        print("Failed to fetch degree plan. Loading from existing JSON file.")
        try:
            with open("degree_plan_data.json", "r") as degree_plan_file:
                degree_plan_data = json.load(degree_plan_file)
            print("Degree plan data successfully loaded from 'degree_plan_data.json'.")
        except FileNotFoundError:
            print("Error: No degree plan data found. Please ensure scraping works.")
            return

    # initialize DegreePlanEvaluator with transcript and degree plan data
    print("Initializing DegreePlanEvaluator...")
    evaluator = DegreePlanEvaluator(degree_plan_data, transcript_data)

    # calculate category completion
    print("Calculating category completion...")
    category_completion = evaluator.calculate_category_completion()
    print("Category Completion:", category_completion)

    # save category completion data to JSON
    with open("category_completion.json", "w") as category_file:
        json.dump(category_completion, category_file, indent=4)
    print("Category completion data saved to 'category_completion.json'.")

    # recommend courses for the next semester
    print("Recommending courses for next semester...")
    recommended_courses = evaluator.recommend_courses()
    print("Recommended Courses:", recommended_courses)

    # Save recommended courses to JSON for reference
    with open("recommended_courses.json", "w") as recommended_file:
        json.dump(recommended_courses, recommended_file, indent=4)
    print("Recommended courses data saved to 'recommended_courses.json'.")
    


if __name__ == "__main__":
    main()
