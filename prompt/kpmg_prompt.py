def wrap_kpmg_template_clean(json_data):
    lines = []

    # Right-aligned KPMG logo
    lines.append(" " * 60 + "[KPMG Logo]\n")

    # Name - Skills
    primary_skills = ", ".join(json_data.get("primary_skill_set", []))
    lines.append(f"{json_data.get('name', '')} - {primary_skills}\n")

    # Summary
    lines.append("Summary")
    for s in json_data.get("professional_summary", {}).get("summary_points", []):
        lines.append(f"- {s}")
    lines.append("")

    # Professional Summary with years of experience
    years_exp = json_data.get("professional_summary", {}).get("years_of_experience", "")
    lines.append(f"Professional Summary ({years_exp})")

    for exp in json_data.get("professional_experience", []):
        job_role = exp.get("job_role", "")
        department = exp.get("department", "")
        duration = exp.get("duration", "")
        lines.append(f"{job_role} - {department if department else ''}, {duration}")

        # Project Description
        if exp.get("project_description"):
            lines.append("Project Description:")
            for pd in exp["project_description"]:
                lines.append(f"- {pd}")

        # Roles & Responsibilities
        if exp.get("roles_and_responsibilities"):
            lines.append("Role & Responsibilities:")
            for r in exp["roles_and_responsibilities"]:
                lines.append(f"- {r}")
        lines.append("")  # blank line between jobs

    # Skills
    if json_data.get("skills"):
        lines.append("Skills:")
        for skill in json_data["skills"]:
            lines.append(f"- {skill}")
        lines.append("")

    # Certifications
    if json_data.get("certifications"):
        lines.append("Certifications:")
        for cert in json_data["certifications"]:
            lines.append(f"- {cert}")
        lines.append("")

    # Education
    if json_data.get("education"):
        lines.append("Education:")
        for edu in json_data["education"]:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            year = edu.get("passout_year", "")
            lines.append(f"- {degree}, {institution}, {year}")
        lines.append("")

    return "\n".join(lines)