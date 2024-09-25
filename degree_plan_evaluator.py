import json
import re

class DegreePlanEvaluator:
    def __init__(self, degree_plan, transcript):
        self.completed_courses = set()

        # collect all completed courses from transcript from each section
        if 'courses' in transcript:
            if 'transfer_credits' in transcript['courses']:
                self.completed_courses.update(course['course_code'] for course in transcript['courses']['transfer_credits'])

            if 'test_credits' in transcript['courses']:
                self.completed_courses.update(course['course_code'] for course in transcript['courses']['test_credits'])

            if 'utd_classes' in transcript['courses']:
                for semester, courses in transcript['courses']['utd_classes'].items():
                    self.completed_courses.update(course['course_code'] for course in courses)

        self.degree_plan = degree_plan
        self.course_graph = self.build_course_graph(degree_plan)

    def build_course_graph(self, degree_plan):
        """Build a graph where nodes are courses, and edges represent prerequisites and corequisites."""
        course_graph = {}

        for section in ['core_requirements', 'major_requirements']:
            requirements = degree_plan.get(section, {})

            if isinstance(requirements, dict):
                requirements = list(requirements.values())

            for category in requirements:
                if isinstance(category, list):
                    for course in category:
                        if isinstance(course, dict):
                            course_code = course.get('course_info', '')
                            prereqs = course.get('prerequisites', [])
                            coreqs = course.get('corequisites', [])
                            course_graph[course_code] = {
                                'prerequisites': prereqs,
                                'corequisites': coreqs
                            }
        return course_graph

    def calculate_category_completion(self):
        category_completion = {}

        for section in ['core_requirements', 'major_requirements']:
            for category_name, courses in self.degree_plan.get(section, {}).items():
                if isinstance(courses, list):
                    total_required = self.get_category_credit_hours(category_name, courses)
                    completed_credits, completed_courses = self.get_completed_credit_hours_and_courses(courses)
                    remaining = max(0, total_required - completed_credits) # Ensure remaining credits are non-negative

                    category_completion[category_name] = {
                        'total_required': total_required,
                        'completed': completed_credits,
                        'remaining': remaining,
                        'completed_courses': completed_courses
                    }

        return category_completion

    def get_completed_credit_hours_and_courses(self, courses):
        """Calculates the completed credit hours and returns a list of completed courses."""
        completed_credits = 0
        completed_courses = []

        for course in courses:
            if isinstance(course, dict) and course['course_info'] in self.completed_courses:
                completed_credits += self.get_course_credit_hours(course['course_info'])
                completed_courses.append(course['course_info'])

        return completed_credits, completed_courses

    def get_category_credit_hours(self, category_name, courses):
        """Extract the total required credit hours from the category name."""
        match = re.search(r'(\d+)\s*semester credit hours', category_name)
        if match:
            return int(match.group(1))
        return 0

    def get_completed_credit_hours(self, courses):
        """Calculates the completed credit hours in a given category."""
        return sum(self.get_course_credit_hours(course['course_info']) for course in courses if isinstance(course, dict) and course['course_info'] in self.completed_courses)

    def get_course_credit_hours(self, course_code):
        """Extract credit hours from the course code based on the second digit in the course number."""
        match = re.search(r'[A-Za-z]+\s*\d(\d)', course_code)
        if match:
            return int(match.group(1))
        return 0

    def recommend_courses(self):
        recommended_courses = []

        for section in ['core_requirements', 'major_requirements']:
            for category, courses in self.degree_plan.get(section, {}).items():
                category_data = self.calculate_category_completion().get(category, {})
                if category_data.get('remaining', 0) > 0:  # Only recommend if there are remaining credits
                    for course in courses:
                        if isinstance(course, dict):
                            course_code = course.get('course_info')

                            if course_code not in self.completed_courses and self.prerequisites_satisfied(course_code):
                                recommended_courses.append(course_code)

        # can add extra requirements here to refine the selection
        # i.e. can prioritize core requirements, for major requirements prioritize the major prefix (i.e. CS vs SE)
        # also can limit the number of credit hrs and pick random courses if there are multiple options
        return recommended_courses

    def prerequisites_satisfied(self, course_code):
        """Check if all prerequisites of the course are satisfied."""
        if course_code not in self.course_graph:
            return True  # if the course has no prerequisites, it's considered satisfied.

        course_data = self.course_graph[course_code]
        prereqs = course_data.get('prerequisites', [])
        for group in prereqs:
            # if any group of prerequisites (i.e. (X OR Y)) has at least one course that is completed, we are good
            if any(prereq in self.completed_courses for prereq in group):
                continue
            else:
                return False
        return True


# can be used to test the DegreePlanEvaluator class, just run this file in isolation with the degree plan and transcript json already populated
degree_plan_data = json.load(open("degree_plan_data.json"))
transcript_data = json.load(open("transcript_data.json"))

# Debugging: Check the data types and structure
print("Degree Plan Data:", type(degree_plan_data))
print("Transcript Data:", type(transcript_data))

evaluator = DegreePlanEvaluator(degree_plan_data, transcript_data)

# Calculate category completion
category_completion = evaluator.calculate_category_completion()
print("Category Completion:", category_completion)

# Recommend courses for next semester
recommended_courses = evaluator.recommend_courses()
print("Recommended Courses:", recommended_courses)
file = open("recommended_courses.json", "w")
json.dump(recommended_courses, file, indent=4)
file.close()

file = open("category_completion.json", "w")
json.dump(category_completion, file, indent=4)
file.close()