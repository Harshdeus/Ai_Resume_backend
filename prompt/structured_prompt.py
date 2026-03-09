import re, json


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
       1. NAME &  POSITION
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

    # Normalize empty fields
    data.setdefault("position", "")
    data.setdefault("summary", [])
    data.setdefault("skills", [])
    data.setdefault("certifications", [])
    data.setdefault("education", [])



    ps = data.get("professional_summary", {})
    ps.setdefault("years_of_experience", "")
    ps.setdefault("experience", [])

    return data