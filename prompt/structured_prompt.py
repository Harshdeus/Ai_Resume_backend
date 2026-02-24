import re, json


def parse_resume_with_llm(clean_text: str, llm, json_schema) -> dict:
    prompt = f"""
            you are an export resume parser. your task is to extract every single piece of information from any resume format accurately
            Return ONLY a valid JSON matching this schema:
            {json.dumps(json_schema, indent=4)}
            Extract everything - do not miss any text
            your goal is to capture 100% of the content from the resume. No summarization, no skipping, no truncation, NO Hallucination.
            =====complete resume parsing instructions==========
        1. NAME / HEADER SECTION:
            - Extract the Full name from the resume as it is 
            - Dont use antoher name what mentioned in the resume take it only.
            - Extract the skillset title
        2. Summary / Professional Summary/ Profile/ Career Objective/ About Me/ Overview SECTION:
            - Extract Every Sentence and bullet point under this section
            - Preserve the exact wording, including all punctuation and formatting
        3. Work Experience/ Employment/ Professional Experience SECTION:
            - Identify every job role/title, department, duration range, company name mentioned
            - Extract ALL job entries in DESCENDING ORDER (current job first)
            
            For EACH job, populate the "experience" array with objects containing:
            - "job_role": The position title (e.g., "Senior Engineer")
            - "company": Company name (e.g., "Caterpillar Inc.")
            - "department": Department if mentioned
            - "duration": Date range (e.g., "March 2020 – December 2025")
            - "project_description": ARRAY containing ALL project descriptions, features, and technologies
            - "roles_and_responsibilities": ARRAY containing EVERY bullet point and responsibility
            
            IMPORTANT: 
            - If a job has 20 bullet points, put ALL 20 in "roles_and_responsibilities"
            - If a job has multiple projects, put ALL project details in "project_description"
            - NEVER leave these arrays empty if content exists in the resume
        4. Education, Academic Background, Qualifications, Degrees, Educational History SECTION:
                - Extract Every thing mention in the resume 
                - Include institute names
                - Include name of the degree, university\collage name,passout year
                - Preserve the exact wording
                - In this section add only this section information only dont add extra information     
                - Include ALL education entries (degrees, diplomas, 10th, 12th if mentioned)

        5. Skills, Technical Skills, Core Competencies, Expertise, Technologies, Tools, Skills & Expertise SECTION:
                - Extract every skills mentioned in the resume
                - Dont skip any lines/sentence/paragraph.
                - If skills are listed with commas, extract each one same as it is
                - EXTRACT FROM ALL SKILLS SECTIONS: Look for "Technical Set", "Front End", "Tools", "Technologies" sections
                - EXTRACT EVERY SINGLE SKILL: Including but not limited to Python, FastAPI, Langchain, GenAI, ML, Django, Matplotlib, Scikit, Numpy, Mongo DB, Elasticsearch, MySQL, NO SQL, Docker, Git, Bitbucket, CI/CD pipeline AWS, HTML, CSS, Bootstrap
                - DO NOT MISS ANY SKILL - if a skill is mentioned anywhere in the resume, add it to the skills array

        6. Certifications, Certificates, Training, Courses, Professional Development:
                - Extract every certificate mentioned in the resume
                - Dont add extra information in this section, only extract same as it is mentioned in the resume
                - Dont skip any lines/sentence/paragraph.

        7. PROJECTS SECTION (if separate from work experience):
                - Look for headings like "Projects", "Responsibilities and Project", "Recent Portfolio", "Key Projects"
                - Extract EVERY project mentioned with COMPLETE details:
                    * Project name/title
                    * Description
                    * Key Features (ALL of them)
                    * Technologies Used (ALL of them)
                    * Role/Responsibilities in the project
                - Associate each project with the correct job/company if possible

        8. ADDITIONAL SECTIONS:
                - Extract information from any other sections like "Personal Data", "Languages", "Strengths", "Declaration"
                - Include languages known, nationality, etc.

            ===== HOW TO HANDLE DIFFERENT FORMATS =====

            FORMAT 1: BULLET POINTS
            ✓ "• Led supplier enablement"
            ✓ "- Developed backend services"
            ✓ "* Created automation framework"
            → Extract each bullet point as separate item

            FORMAT 2: TABLES
            ✓ Tables with company names and durations
            ✓ Tables with skills categories
            → Extract ALL cells, rows, and columns

            FORMAT 3: CATEGORIZED LISTS
            "Programming Languages: Python, Java, JavaScript"
            → Extract each skill individually: "Python", "Java", "JavaScript"

            FORMAT 4: PROJECT DESCRIPTIONS
            "Project: Chat Microservice
            - Developed using Python
            - Integrated with OpenAI"
            → Extract project name AND ALL bullet points

            FORMAT 5: INLINE TEXT
            "Experienced in Python, Flask, and Azure"
            → Extract ALL mentioned skills

            FORMAT 6: MIXED FORMAT (TABLES + BULLETS + TEXT)
            → Extract EVERYTHING from all formats

            ===== CRITICAL REMINDERS =====
            - EXTRACT EVERYTHING: Contact info, ALL summary paragraphs, ALL jobs, ALL projects under each job, ALL skills from ALL sections
            - DO NOT SKIP: If a job has 4 projects, capture all 4. If skills section has 20 skills, capture all 20.
            - PRESERVE EXACT WORDING: Copy text exactly as it appears
            - NO HALLUCINATION: Only extract what is explicitly written

            ===== RESUME TEXT =====
            {clean_text}
            """
    raw_response = llm.invoke(prompt)
    print("===== RAW LLM RESPONSE =====")
    print(raw_response)

    json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
    if not json_match:
        return json_schema

    try:
        data = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return json_schema

    # Normalize empty fields
    data.setdefault("skills_set", [])
    data.setdefault("summary", [])
    data.setdefault("skills", [])
    data.setdefault("certifications", [])
    data.setdefault("education", [])

    # If skills_set is empty but skills has values, copy skills to skills_set
    if not data["skills_set"] and data["skills"]:
        data["skills_set"] = data["skills"].copy()

    ps = data.get("professional_summary", {})
    ps.setdefault("years_of_experience", "")
    ps.setdefault("experience", [])

    return data