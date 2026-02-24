def wrap_kpmg_template_from_json(json_data: dict) -> str:
    lines = []

    # Name and skills
    name = json_data.get("name", "")
    skills = json_data.get("skills", [])
    # Ensure skills is a list and handle empty case
    if isinstance(skills, list) and skills:
        skills_text = ", ".join(skills[:5])
    else:
        skills_text = ""
    lines.append(f"{name} – {skills_text}\n")

    # ---------------- Summary ----------------
    lines.append("Summary:")
    summary = json_data.get("summary", [])
    if isinstance(summary, str):
        summary = [summary] if summary.strip() else []
    elif not isinstance(summary, list):
        summary = []

    for s in summary:
        if s and isinstance(s, str) and s.strip():
            lines.append(f"• {s}")
    lines.append("")

    # ---------------- Professional Summary ----------------
    ps = json_data.get("professional_summary", {})
    if not isinstance(ps, dict):
        ps = {}

    years = ps.get("years_of_experience", "")
    if years:
        lines.append(f"Professional Summary ({years} Years):")
    else:
        lines.append("Professional Summary:")

    experiences = ps.get("experience", [])
    if isinstance(experiences, str):
        experiences = [experiences] if experiences.strip() else []
    elif not isinstance(experiences, list):
        experiences = []

    for exp in experiences:
        if exp and isinstance(exp, str) and exp.strip():
            lines.append(f"• {exp}")
    lines.append("")

    # ---------------- Skills ----------------
    lines.append("Skills:")
    skills_list = json_data.get("skills", [])
    if isinstance(skills_list, str):
        skills_list = [skills_list] if skills_list.strip() else []
    elif not isinstance(skills_list, list):
        skills_list = []

    for skill in skills_list:
        if skill and isinstance(skill, str) and skill.strip():
            lines.append(f"• {skill}")
    lines.append("")

    # ---------------- Certifications ----------------
    lines.append("Certifications:")
    certs = json_data.get("certifications", [])
    if isinstance(certs, str):
        certs = [certs] if certs.strip() else []
    elif not isinstance(certs, list):
        certs = []

    for c in certs:
        if not c:
            continue

        if isinstance(c, dict):
            # Try different possible field names for certification title
            title = c.get("title") or c.get("name") or c.get("certification") or ""
            if title:
                lines.append(f"• {title}")
            else:
                # If no title field, convert dict to string representation
                lines.append(f"• {str(c)}")
        elif isinstance(c, str) and c.strip():
            lines.append(f"• {c}")
    lines.append("")

    # ---------------- Education ----------------
    lines.append("Education:")
    education = json_data.get("education", [])
    if isinstance(education, str):
        education = [education] if education.strip() else []
    elif not isinstance(education, list):
        education = []

    for e in education:
        if not e:
            continue

        if isinstance(e, dict):
            # Try different possible field names
            degree = e.get("degree") or e.get("degree_name") or ""
            institute = e.get("institute") or e.get("institution") or e.get("college") or e.get("university") or ""
            year = e.get("passout_year") or e.get("year") or e.get("graduation_year") or ""

            # Build education line with available information
            edu_parts = []
            if degree:
                edu_parts.append(degree)
            if institute:
                edu_parts.append(institute)
            if year:
                edu_parts.append(year)

            if edu_parts:
                lines.append(f"• {', '.join(edu_parts)}")
            else:
                # If no specific fields found, add the dict as string
                lines.append(f"• {str(e)}")
        elif isinstance(e, str) and e.strip():
            lines.append(f"• {e}")

    return "\n".join(lines).strip()