import re
import json


def parse_resume_with_llm(clean_text: str, llm, json_schema) -> dict:
    prompt = f"""
       You are a professional resume parser.

       Extract information from the resume text below and return ONLY a valid JSON object
       that strictly matches this schema:

       {json.dumps(json_schema, indent=4)}

       IMPORTANT:
       - If no explicit summary heading exists, extract the first descriptive paragraph before Skills or Experience as summary.
       - Do not return empty summary if descriptive text exists at the top.

       IMPORTANT GLOBAL RULES:
       - Extract ONLY information that exists in the resume text.
       - NEVER create or assume data.
       - NEVER use placeholder values like "John Doe".
       - Preserve original wording exactly as in resume.
       - If a section is missing, return an empty array [].
       - Output ONLY valid JSON. No explanations. No markdown. No comments.


       =====================
       1. NAME & POSITION
       =====================
       - Name: Extract the full name exactly as written in the resume (first occurrence at top).

      - Primary Skill Set (Title):
     Extract ONLY the short headline skill set that appears next to or immediately below the candidate name.

     Examples:
     - "IT Procurement and Vendor Management"
     - "Staffing Solutions, Vendor Development & Management, Team Management"

     Rules:
     - Must be a short phrase (1 line only).
     - Do NOT extract long comma-separated skill lists.
     - Do NOT extract bullet-point skill sections.
     - Do NOT extract Skills section content.
     - Prefer the line near the candidate name/header.
     - Preserve wording exactly as in the resume.
     - If not found, return empty string "".

       =====================
       3. PROFESSIONAL EXPERIENCE
       =====================
       - Detect job roles from "Experience" or "Professional Experience" section.
       - FORCE: 1 job role = 1 object.
       - DO NOT merge multiple job roles into a single object.
       - Order experiences in descending order (current job first).

       For each job:
       - job_role
       - department (if present)
       - duration
       - project_description → bullet points
       - roles_and_responsibilities → bullet points


       =====================
       4. SKILLS
       =====================
       - Look for headings:
         "Skills", "Key Skills", "Technical Skills", "Skill Set", "Core Skills"

       - Extract ALL lines after the heading until one of these headings appears:
         "Certifications"
         "Education"
         "Personal Information"
         "Projects"
         "Work Experience"
         "Professional Experience"

       Rules:
       - Each bullet or full line = ONE array item.
       - Keep category labels.
       - Do NOT split comma-separated values.
       - Preserve punctuation and case.
       - Flatten into single array.
       - If missing, return [].


       =====================
       5. TOOLS & TECHNOLOGIES
       =====================
       - Extract any tools, platforms, software, or technologies mentioned under:
         "Tools", "Technologies", "Technical Skills", "Environment", "Platforms".
       - Return as array.
       - If missing, return [].


       =====================
       6. CERTIFICATIONS
       =====================
       - Look for headings:
         "Certifications", "Certs"

       - Extract all lines until next section heading:
         "Education"
         "Skills"
         "Work Experience"
         "Professional Experience"
         "Projects"


       =====================
       7. EDUCATION
       =====================
       - Detect headings: "Education", "Professional Qualification"
       - Extract all sentences or paragraphs exactly as written.
       - Do NOT swap degree and institution.
       - Do NOT invent any data.
       - Preserve order and wording.
       - Return as array of dictionaries with keys: degree, institution, passout_year
       - If any field is missing, fill with "Not Provided"


       =====================
       RESUME TEXT
       =====================
       \"\"\"{clean_text}\"\"\"


       =====================
       OUTPUT FORMAT
       =====================
       Return ONLY a valid JSON object following the schema.
       Do not add explanations.
       Do not add markdown.
       Do not add comments.
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

    if not isinstance(data, dict):
        return json_schema

    # Top-level safe defaults
    data.setdefault("name", "")
    data.setdefault("position", "")
    data.setdefault("summary", [])
    data.setdefault("skills", [])
    data.setdefault("certifications", [])
    data.setdefault("education", [])
    data.setdefault("professional_summary", {})

    # Normalize summary
    if isinstance(data["summary"], str):
        data["summary"] = [data["summary"]] if data["summary"].strip() else []
    elif not isinstance(data["summary"], list):
        data["summary"] = []

    # Normalize skills
    if isinstance(data["skills"], str):
        data["skills"] = [data["skills"]] if data["skills"].strip() else []
    elif not isinstance(data["skills"], list):
        data["skills"] = []

    # Normalize certifications
    if isinstance(data["certifications"], str):
        data["certifications"] = [data["certifications"]] if data["certifications"].strip() else []
    elif not isinstance(data["certifications"], list):
        data["certifications"] = []

    # Normalize education
    if isinstance(data["education"], dict):
        data["education"] = [data["education"]]
    elif not isinstance(data["education"], list):
        data["education"] = []

    normalized_education = []
    for edu in data["education"]:
        if isinstance(edu, dict):
            normalized_education.append({
                "degree_name": edu.get("degree_name") or edu.get("degree") or "Not Provided",
                "institute_name": edu.get("institute_name") or edu.get("institution") or "Not Provided",
                "university_name": edu.get("university_name") or "Not Provided",
                "passout_year": edu.get("passout_year") or "Not Provided",
            })
        elif isinstance(edu, str) and edu.strip():
            normalized_education.append({
                "degree_name": edu.strip(),
                "institute_name": "Not Provided",
                "university_name": "Not Provided",
                "passout_year": "Not Provided",
            })
    data["education"] = normalized_education

    # Normalize professional_summary
    ps = data.get("professional_summary", {})

    # If LLM returns professional_summary as list, take first dict
    if isinstance(ps, list):
        if ps and isinstance(ps[0], dict):
            ps = ps[0]
        else:
            ps = {}

    if not isinstance(ps, dict):
        ps = {}

    ps.setdefault("years_of_experience", "")
    ps.setdefault("experience", [])

    if not isinstance(ps["experience"], list):
        if isinstance(ps["experience"], dict):
            ps["experience"] = [ps["experience"]]
        else:
            ps["experience"] = []

    normalized_experience = []
    for exp in ps["experience"]:
        if not isinstance(exp, dict):
            continue

        project_description = exp.get("project_description", [])
        if isinstance(project_description, str):
            project_description = [project_description] if project_description.strip() else []
        elif not isinstance(project_description, list):
            project_description = []

        roles_and_responsibilities = exp.get("roles_and_responsibilities", [])
        if isinstance(roles_and_responsibilities, str):
            roles_and_responsibilities = [roles_and_responsibilities] if roles_and_responsibilities.strip() else []
        elif not isinstance(roles_and_responsibilities, list):
            roles_and_responsibilities = []

        normalized_experience.append({
            "company": exp.get("company", ""),
            "job_role": exp.get("job_role", ""),
            "department": exp.get("department", ""),
            "duration": exp.get("duration", ""),
            "project_description": project_description,
            "roles_and_responsibilities": roles_and_responsibilities,
        })

    ps["experience"] = normalized_experience
    data["professional_summary"] = ps

    return data