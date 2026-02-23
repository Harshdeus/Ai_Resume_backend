import re, json


def parse_resume_with_llm(clean_text: str, llm, json_schema) -> dict:
    prompt = f"""
    You are an expert resume parser. Your task is to extract information from ANY resume format accurately.

    Return ONLY a valid JSON matching this schema:
    {json.dumps(json_schema, indent=4)}

    ===== CRITICAL EXTRACTION RULES =====
    1. EXTRACT EVERY DETAIL — Do not miss any information, especially work experience responsibilities
    2. NAME: Extract the FULL name from the very top of the resume
    3. SUMMARY SECTION: Extract ALL summary paragraphs/sentences - do not truncate or miss any
    4. YEARS OF EXPERIENCE: Always extract and include the years in professional_summary.years_of_experience field
    5. WORK EXPERIENCE: Extract ALL jobs mentioned with their COMPLETE bullet points as structured objects
    6. SKILLS_SET: Populate this array with ALL skills (same as skills array)
    7. PRESERVE ALL BULLET POINTS under each job role exactly as they appear
    8. SKILLS: Extract ALL skills mentioned, including from "Tools & Technologies" section
    9. CERTIFICATIONS: Extract the COMPLETE certification text, do not truncate

    ===== SECTION DETECTION =====
    - **NAME**: Usually at the very top of the resume - extract the full name
    - **SUMMARY**: ALL paragraphs under summary/profile sections - extract EVERY SINGLE sentence/paragraph
    - **YEARS OF EXPERIENCE**: Look for patterns like "X+ years", "X years", etc. and include in professional_summary.years_of_experience
    - **WORK EXPERIENCE**: 
        * Extract EACH JOB AS A STRUCTURED OBJECT with job_role, company, duration, and roles_and_responsibilities array
        * Look for patterns like "Job Role:" or "Role:" or job titles followed by dates
        * Include ALL bullet points under each role in the roles_and_responsibilities array
        * DO NOT SKIP ANY JOB - extract every work experience entry
        * DO NOT extract jobs as plain strings - they MUST be objects with the specified fields
    - **SKILLS**: Extract ALL skills from Skills section AND Tools & Technologies section
    - **SKILLS_SET**: Copy the same skills from the skills array into skills_set
    - **CERTIFICATIONS**: All certifications/training mentioned - include the FULL description
    - **EDUCATION**: All degrees with institutions and years - extract as structured objects

    ===== WORK EXPERIENCE FORMATTING =====
    For each job found in the resume, extract it as an object with this structure:
    {{
        "job_role": "The job title/role",
        "company": "Company name if available, otherwise empty string",
        "duration": "Date range (e.g., Jan 2020 - Present)",
        "roles_and_responsibilities": [
            "First responsibility bullet point",
            "Second responsibility bullet point",
            "etc."
        ],
        "project_description": ""  // If project description exists, otherwise empty string
    }}

    ===== SKILLS EXTRACTION =====
    Extract ALL skills mentioned in the resume:
    - From any "Skills" section
    - From any "Tools & Technologies" section (extract each tool individually)
    - From any other sections where skills are mentioned

    ===== RESUME TEXT =====
    {clean_text}

    ===== OUTPUT REQUIREMENTS =====
    Return ONLY a valid JSON object matching the schema.
    - Include the FULL name
    - Include EVERY summary paragraph
    - Include ALL jobs as OBJECTS with ALL their bullet points in roles_and_responsibilities arrays
    - Include ALL skills and tools in skills array
    - Copy ALL skills to skills_set array (skills_set should be identical to skills)
    - Include COMPLETE certification text, not truncated
    - Include years of experience in professional_summary.years_of_experience
    - Use empty strings "" for missing text fields and empty arrays [] for missing list fields
    - Education should be extracted as structured objects with degree, institution, and year fields
    """

    raw_response = llm.invoke(prompt).strip()
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