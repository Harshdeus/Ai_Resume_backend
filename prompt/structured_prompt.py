import re,json
def parse_resume_with_llm(clean_text: str, llm, json_schema) -> dict:
    prompt = f"""
    You are a professional resume parser.
    Extract the resume into EXACT JSON format matching this schema:
    {json.dumps(json_schema, indent=2)}

    ==================== RULES ====================
    - Use only exact words from resume.
    - Do not invent data.
    - Each job experience must have company, job_role, department, duration, project_description (bullet list), roles_and_responsibilities (bullet list)
    - Skills_set and skills should be lists.
    - Education should be "Degree | College/University | Year".
    - Output JSON only.

    ==================== RESUME TEXT ====================
    {clean_text}
    ==================== OUTPUT ====================
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
    ps = data.get("professional_summary", {})
    ps.setdefault("years_of_experience", "")
    ps.setdefault("experience", [])

    return data