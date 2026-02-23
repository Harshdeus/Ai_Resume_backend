def wrap_kpmg_template_clean(json_data: dict) -> str:
    lines = []

    # ---- Right-aligned KPMG logo ----
    lines.append(" " * 60 + "[KPMG Logo]\n")

    # ---- Name - Skills ----
    skills_list = json_data.get("skills", [])
    primary_skills = ", ".join(skills_list) if skills_list else ""
    lines.append(f"{json_data.get('name', '')} - {primary_skills}\n")

    # ---- Summary ----
    lines.append("Summary:")
    prof_summary = json_data.get("professional_summary", [])

    # Handle both list and dict format
    if isinstance(prof_summary, dict):
        summary_points = prof_summary.get("summary_points", [])
    elif isinstance(prof_summary, list):
        summary_points = prof_summary
    else:
        summary_points = []

    for s in summary_points:
        lines.append(f"- {s}")
    lines.append("")  # blank line

    # ---- Professional Summary with Years of Experience ----
    years_exp = str(json_data.get("total_years_experience", ""))
    lines.append(f"Professional Summary ({years_exp} years):\n")

    # Work Experience in descending order
    for exp in json_data.get("professional_experience", []):
        job_role = exp.get("job_role", "")
        department = exp.get("department", "")
        duration = exp.get("duration", "")
        lines.append(f"{job_role} - {department if department else ''}, {duration}")

        # Project Description
        project_desc = exp.get("project_description", [])
        if project_desc:
            lines.append("Project Description:")
            for pd in project_desc:
                lines.append(f"- {pd}")

        # Roles & Responsibilities
        roles_resp = exp.get("roles_and_responsibilities", [])
        if roles_resp:
            lines.append("Roles & Responsibilities:")
            for r in roles_resp:
                lines.append(f"- {r}")

        lines.append("")  # blank line between jobs

    # ---- Skills ----
    if skills_list:
        lines.append("Skills:")
        for skill in skills_list:
            lines.append(f"- {skill}")
        lines.append("")

    # ---- Certifications ----
    certs = json_data.get("certifications", [])
    if certs:
        lines.append("Certifications:")
        for cert in certs:
            # Handle dict or string
            if isinstance(cert, dict):
                cert_name = cert.get("name", "")
                cert_levels = cert.get("levels", [])
                lines.append(f"- {cert_name}")
                for level in cert_levels:
                    lines.append(f"  • {level}")
            else:
                lines.append(f"- {cert}")
        lines.append("")

    # ---- Education ----
    edu_list = json_data.get("education", [])
    if edu_list:
        lines.append("Education:")
        for edu in edu_list:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            year = edu.get("passout_year", "")
            lines.append(f"- {degree}, {institution}, {year}")
        lines.append("")

    return "\n".join(lines).strip()