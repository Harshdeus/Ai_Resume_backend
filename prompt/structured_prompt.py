import json
import re

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
    1. NAME & PRIMARY SKILLS
    =====================
    - Name: Extract the full name exactly as written in the resume (first occurrence at top).
    - Primary Skills: Extract top skills exactly as written from sections titled:
      "Key Skills", "Skills", "Technical Skills", "Skill Set", "Core Competencies" or similar.


    =====================
    2. PROFESSIONAL SUMMARY
    =====================
    - Look for headings:
      "OBJECTIVE", "Profile Summary", "Summary", "Career Objective", "Professional Summary" (case-insensitive).

    - If no heading exists, use the first descriptive paragraph before "Experience" or "Skills".
    - Extract sentences as individual bullet points.
    - Split by ".", "?", "!".
    - Preserve wording exactly.
    - Return as array of sentences.
    - Also extract total years of experience if mentioned (example: "15+ years of experience").


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

    raw_response = llm.invoke(prompt).strip()

    print("===== RAW LLM RESPONSE =====")
    print(raw_response)

    # ---- Extract JSON only ----
    json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)

    if not json_match:
        print("❌ No JSON found in LLM response")
        return json_schema

    json_str = json_match.group(0)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print("❌ JSON Decode Error:", e)
        return json_schema

    # ---- Normalize Education ----
    edu_list = data.get("education", [])

    # Include 12th / 10th if present in text
    extra_edu_matches = re.findall(r"(\d{2}\s*th|\d{2})(?:\s*\|\s*)(\d{4})", clean_text, re.I)
    for deg, year in extra_edu_matches:
        edu_list.append({
            "degree": deg.strip(),
            "institution": "Not Provided",
            "passout_year": str(year.strip())
        })

    if not edu_list:
        data["education"] = [{
            "passout_year": "Not Provided",
            "degree": "Not Provided",
            "institution": "Not Provided"
        }]
    else:
        new_edu = []
        for edu in edu_list:
            new_edu.append({
                "passout_year": str(edu.get("passout_year", edu.get("year", "Not Provided"))),
                "degree": edu.get("degree", "Not Provided"),
                "institution": edu.get("institution", "Not Provided")
            })
        data["education"] = new_edu

    # ---- Extract Tools & Technologies ----
    tools_pattern = r"\b(SAP CLM|SAP MM|SAP ECC|Coupa|Microsoft Excel|PowerPoint|Word|MDM|BOM|MRP)\b"
    tools = list(set(re.findall(tools_pattern, clean_text, re.I)))
    data["tools_and_technologies"] = tools if tools else []

    # ---- Extract Languages ----
    lang_match = re.search(r"Languages?:\s*(.+)", clean_text, re.I)
    if lang_match:
        data["languages"] = [l.strip() for l in lang_match.group(1).split(",")]
    else:
        data["languages"] = []

    # ---- Ensure Professional Experience bullets are not truncated ----
    for job in data.get("professional_experience", []):
        # Ensure project_description includes bullets before R&R heading
        if not job.get("project_description"):
            job["project_description"] = []  # LLM should populate, fallback empty
        if not job.get("roles_and_responsibilities"):
            job["roles_and_responsibilities"] = []  # LLM should populate, fallback empty

    return data