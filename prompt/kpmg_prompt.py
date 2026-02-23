def wrap_kpmg_template_clean(json_data: dict) -> str:
    lines = []

    # Right-aligned KPMG logo
    lines.append(" " * 60 + "[KPMG Logo]\n")

    # Name + primary skills
    name = json_data.get('name', '')
    skills_set = json_data.get('skills_set', []) or []
    lines.append(f"{name} - {', '.join(skills_set)}\n")

    # Summary
    lines.append("Summary:")
    for s in json_data.get("summary", []) or []:
        lines.append(f"- {s}")
    lines.append("")

    # Professional Summary
    prof_summary = json_data.get("professional_summary", {}) or {}
    years_exp = prof_summary.get("years_of_experience", "")
    lines.append(f"Professional Summary ({years_exp} years):\n")

    for exp in prof_summary.get("experience", []) or []:
        job_role = exp.get("job_role", "")
        department = exp.get("department", "")
        duration = exp.get("duration", "")
        lines.append(f"{job_role} - {department}, {duration}")

        # Project Description
        if exp.get("project_description"):
            lines.append("Project Description:")
            for pd in exp["project_description"]:
                lines.append(f"- {pd}")

        # Roles & Responsibilities
        if exp.get("roles_and_responsibilities"):
            lines.append("Roles & Responsibilities:")
            for r in exp["roles_and_responsibilities"]:
                lines.append(f"- {r}")
        lines.append("")  # blank line between jobs

    # Skills
    lines.append("Skills:")
    for s in json_data.get("skills", []) or []:
        lines.append(f"- {s}")
    lines.append("")

    # Certifications
    lines.append("Certifications:")
    for c in json_data.get("certifications", []) or []:
        lines.append(f"- {c}")
    lines.append("")

    # Education
    lines.append("Education:")
    for e in json_data.get("education", []) or []:
        lines.append(f"- {e}")
    lines.append("")

    return "\n".join(lines).strip()  # ✅ Return string properly