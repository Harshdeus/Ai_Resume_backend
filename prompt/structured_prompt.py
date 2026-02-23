import json
import re

def parse_resume_with_llm(clean_text: str, llm, json_schema) -> dict:
    prompt = f"""
    You are an expert ATS-grade resume parsing engine.

    Your task is STRICT structured extraction.
    You are NOT allowed to summarize.
    You are NOT allowed to explain.
    You are NOT allowed to guess.

    Return ONLY valid JSON matching this schema EXACTLY:
    {json.dumps(json_schema, indent=2)}

    ==================== GLOBAL RULES ====================

    1. ZERO hallucination. If information is not present → return "" or [].
    2. Use EXACT text from resume. No rephrasing.
    3. NEVER output explanations.
    4. NEVER invent dates.
    5. NEVER combine multiple jobs into one.
    6. NEVER assume duration.
    7. If a job does NOT contain a YEAR → it is NOT a valid job.
    8. Missing fields must be "" or [] only.
    9. Output must be valid JSON only.

    ==================== PRE-PROCESSING LOGIC ====================

    Before extraction:
    - Identify clear SECTION HEADINGS.
    - Identify TABLE STRUCTURES.
    - Identify DATE PATTERNS (YYYY, MMM YYYY, Month YYYY, Present, Till Date).
    - Identify bullet patterns (•, -, ➢, →, *, ✓, ▪, ▫, »).

    Then extract section-by-section.

    ==================== NAME EXTRACTION ====================

    Rules:
    - Name is usually top-most large text.
    - Ignore company names like:
      KPMG, Deloitte, EY, PwC, Accenture, Cognizant, TCS, Infosys, IBM, Microsoft, Google
    - Ignore addresses.
    - Ignore emails.
    - Extract only the person's name.

    If unsure → return "".

    ==================== PROFESSIONAL SUMMARY ====================

    Look for headings:
    SUMMARY, PROFESSIONAL SUMMARY, PROFILE, OBJECTIVE,
    CAREER SUMMARY, EXECUTIVE SUMMARY, ABOUT ME

    If heading exists:
    → Extract text until next section heading.

    If no heading:
    → Extract first 2 descriptive paragraphs before work experience.

    Split into individual sentences.

    If none → [].

    ==================== YEARS OF EXPERIENCE ====================

    Extract phrases like:
    - "11+ years"
    - "5 years"
    - "7+ years of experience"
    - "Total Experience: 11 Years"

    Must contain number + "year".

    If not found → "".

    ==================== PROFESSIONAL EXPERIENCE ====================

    STEP 1 — Identify Experience Sections:

    Look for headings:
    EXPERIENCE, WORK EXPERIENCE, EMPLOYMENT,
    PROFESSIONAL EXPERIENCE, CAREER HISTORY,
    PROJECT EXPERIENCE, ASSIGNMENTS

    STEP 2 — TABLE HANDLING (VERY IMPORTANT)

    If you detect table headers like:
    Company Name | Joining Date | Relieving Date

    Then:
    - Each row = ONE JOB
    - Combine joining + relieving date as duration
    - Company name = value from company column
    - job_role = "" (unless role column present)

    STEP 3 — JOB ROLE FORMAT

    If lines start with:
    Job Role:

    Each occurrence = separate job.

    Extract:
    - job_role
    - duration (if present)
    - responsibilities under it

    STEP 4 — STANDARD JOB FORMAT

    For each job:

    VALID JOB CONDITIONS:
    - Must contain a YEAR (2020, 2019–2022, Jan 2020 – Present)
    - If no year → DO NOT treat as job

    Extract:
    - job_role
    - company_name
    - duration
    - roles_and_responsibilities (all bullet points under that job)

    DO NOT merge jobs.
    DO NOT guess missing dates.

    ==================== SKILLS ====================

    Look under headings:
    SKILLS, TECHNICAL SKILLS, CORE SKILLS,
    COMPETENCIES, EXPERTISE

    Rules:
    - Split comma-separated skills.
    - Each bullet = separate item.
    - Do NOT include tools here.
    - Do NOT duplicate.

    If none → [].

    ==================== TOOLS & TECHNOLOGIES ====================

    Look under:
    TOOLS, TECHNOLOGIES, SOFTWARE,
    PLATFORMS, PROGRAMMING LANGUAGES,
    DATABASES, FRAMEWORKS

    Also scan full resume for common tools like:
    SAP, SQL, Python, Java, AWS, Azure,
    Docker, Kubernetes, Jenkins, Selenium,
    Power BI, Tableau, Excel, Git, REST, API

    Remove duplicates.

    If none → [].

    ==================== CERTIFICATIONS ====================

    Look under:
    CERTIFICATIONS, LICENSES & CERTIFICATIONS,
    ACCREDITATIONS

    Only extract listed certifications.
    Do NOT include degrees.

    If none → [].

    ==================== EDUCATION ====================

    Look under:
    EDUCATION, ACADEMIC QUALIFICATIONS,
    DEGREES, FORMAL EDUCATION

    Extract ALL levels:
    10th
    12th
    Bachelor’s
    Master’s
    PhD

    Handle formats:
    "B.Tech, SRM University, 2014"
    "12th 2011"
    "10th Standard, 2008"

    If institution missing → "".
    If year missing → "".

    ==================== LANGUAGES ====================

    Look under:
    LANGUAGES, LANGUAGES KNOWN,
    LANGUAGE SKILLS

    Extract language names only.
    Ignore proficiency level.

    If none → [].

    ==================== STRICT VALIDATION ====================

    Before final output:
    - Check every job has a YEAR in duration.
    - Check no company name appears in name field.
    - Check no tools inside skills.
    - Check no degree inside certifications.
    - Check JSON is valid.
    - Check missing fields use "" or [] only.

    ==================== RESUME TEXT ====================

    {clean_text}

    ==================== OUTPUT ====================

    Return ONLY valid JSON.
    No markdown.
    No commentary.
    No explanations.
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

    # ---- Extract Certifications ----
    lines = clean_text.split("\n")
    certifications = []
    cert_active = False
    for line in lines:
        line = line.strip()
        # Start when Certification heading found
        if re.search(r"certifications?|certs?", line, re.I):
            cert_active = True
            continue
        # Stop at next section heading
        if cert_active and re.match(
                r"^(Skills|Education|Professional Qualification|Personal Information|Projects|Work Experience|Professional Experience)",
                line, re.I):
            cert_active = False
        # Collect certification lines
        if cert_active and line:
            clean_line = line.lstrip("•- ").strip()
            if clean_line:
                certifications.append(clean_line)

    data["certifications"] = certifications if certifications else []

    return data