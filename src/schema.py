def json_structure():
    return {
        "name": "",
        "position": "",
        "summary": [],
        "professional_summary": {
            "years_of_experience": "",
            "experience": [
                {
                    "company": "",
                    "job_role": "",
                    "department": "",
                    "duration": "",
                    "project_description": [],
                    "roles_and_responsibilities": []
                }
            ]
        },
        "skills": [],
        "certifications": [],
        "education": [
            {
                "degree_name": "",  # Changed from "degree"
                "institute_name": "",  # Changed from "institute"
                "university_name": "",  # Changed from "university"
                "passout_year": ""  # Keep as is (matches)
            }
        ]
    }