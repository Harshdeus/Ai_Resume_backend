import re, json


def wrap_kpmg_template_clean(json_data: dict) -> str:
    lines = []

    # Get skills - combine skills_set and skills
    skills_set = json_data.get('skills_set', [])
    skills = json_data.get('skills', [])
    all_skills = list(set(skills_set + skills))  # Remove duplicates

    # Right-aligned KPMG logo
    lines.append(" " * 60 + "[KPMG Logo]\n")

    # Name + primary skills
    name = json_data.get('name', '')
    skills_text = ', '.join(all_skills[:5]) if all_skills else ''  # Show top 5 skills
    lines.append(f"{name} - {skills_text}\n")

    # Summary section - Show ALL summary points
    lines.append("Summary:")
    summary_list = json_data.get("summary", [])
    if isinstance(summary_list, str):
        summary_list = [summary_list] if summary_list.strip() else []
    elif not isinstance(summary_list, list):
        summary_list = []

    for s in summary_list:
        if s and isinstance(s, str) and s.strip():
            lines.append(f"• {s}")
    lines.append("")

    # Professional Summary with Years
    prof_summary = json_data.get("professional_summary", {})
    if not isinstance(prof_summary, dict):
        prof_summary = {}

    years_exp = prof_summary.get("years_of_experience", "")
    if years_exp:
        lines.append(f"Professional Summary ({years_exp}):\n")
    else:
        lines.append("Professional Summary:\n")

    # Work Experience - Handle ALL jobs in the experience array with type checking
    experiences = prof_summary.get("experience", [])
    if not isinstance(experiences, list):
        experiences = [experiences] if experiences else []

    for exp in experiences:
        # Skip if exp is None or empty
        if not exp:
            continue

        if isinstance(exp, dict):
            # Extract job details with safe .get() calls
            job_role = exp.get("job_role", "")
            company = exp.get("company", "")
            duration = exp.get("duration", "")

            # Format the job header
            job_header = job_role
            if company and isinstance(company, str):
                job_header += f" at {company}"
            if duration and isinstance(duration, str):
                job_header += f", {duration}"

            if job_header.strip():
                lines.append(job_header)

            # Add project description if exists (handle both string and list)
            project_desc = exp.get("project_description", "")
            if project_desc:
                lines.append("Project Description:")
                if isinstance(project_desc, str):
                    if project_desc.strip():
                        lines.append(f"• {project_desc}")
                elif isinstance(project_desc, list):
                    for pd in project_desc:
                        if pd and isinstance(pd, str) and pd.strip():
                            lines.append(f"• {pd}")

            # Add roles and responsibilities
            responsibilities = exp.get("roles_and_responsibilities", [])
            if responsibilities:
                lines.append("Role & Responsibilities:")
                if isinstance(responsibilities, str):
                    if responsibilities.strip():
                        lines.append(f"• {responsibilities}")
                elif isinstance(responsibilities, list):
                    for r in responsibilities:
                        if r and isinstance(r, str) and r.strip():
                            lines.append(f"• {r}")
            lines.append("")

        elif isinstance(exp, str):
            # Simple string format - try to parse it
            if exp.strip():
                lines.append(exp)
                lines.append("Role & Responsibilities:")
                lines.append("• Details not available in structured format")
                lines.append("")

    # Skills section - Show ALL skills
    if all_skills:
        lines.append("Skills:")
        for skill in all_skills:
            if skill and isinstance(skill, str) and skill.strip():
                # Handle skills that might contain commas
                if ',' in skill:
                    # Split comma-separated skills
                    sub_skills = [s.strip() for s in skill.split(',') if s.strip()]
                    for sub_skill in sub_skills:
                        if sub_skill:
                            lines.append(f"• {sub_skill}")
                else:
                    lines.append(f"• {skill}")
        lines.append("")

    # Certifications - Show COMPLETE certification text
    certs = json_data.get("certifications", [])
    if certs:
        lines.append("Certifications:")
        if isinstance(certs, str):
            certs = [certs] if certs.strip() else []
        elif not isinstance(certs, list):
            certs = []

        for c in certs:
            if c and isinstance(c, str) and c.strip():
                lines.append(f"• {c}")
        lines.append("")

    # Education - Handle with type checking
    lines.append("Education:")
    education_list = json_data.get("education", [])
    if not isinstance(education_list, list):
        education_list = [education_list] if education_list else []

    for e in education_list:
        if not e:
            continue

        if isinstance(e, dict):
            degree = e.get("degree", "")
            institution = e.get("institution", "")

            # Handle both 'year' and 'passout_year' field names
            year = e.get("year", "") or e.get("passout_year", "")

            # Try auto-extract year if empty
            if not year and isinstance(degree, str) and isinstance(institution, str):
                match = re.search(r"(20\d{2}|19\d{2})", f"{degree} {institution}")
                year = match.group(0) if match else ""

            # Ensure all values are strings
            degree = str(degree) if degree else ""
            institution = str(institution) if institution else ""
            year = str(year) if year else ""

            lines.append(f"• {degree} | {institution} | {year}")
        elif isinstance(e, str):
            # Handle string format education
            lines.append(f"• {e}")
    lines.append("")

    return "\n".join(lines).strip()