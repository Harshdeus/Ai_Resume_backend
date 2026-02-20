def format_to_kpmg_template(data: dict) -> str:
    lines = []

    # ---------------- Header ----------------
    name = data.get("name", "Not Provided")
    skills_set = ", ".join(data.get("primary_skill_set", [])) if isinstance(data.get("primary_skill_set"), list) else data.get("primary_skill_set", "Not Provided")
    header_text = f"KPMG\n{name} - {skills_set}"
    # Right-align KPMG at the same line
    total_width = 100
    kpmg_text = "KPMG"
    space_count = max(2, total_width - len(header_text) - len(kpmg_text))
    lines.append(header_text + " " * space_count + kpmg_text)
    # lines.append("=" * total_width)

    # ---------------- Summary ----------------
    lines.append("\nSUMMARY")
    summary = data.get("summary", [])
    if isinstance(summary, list):
        for s in summary:
            if s.strip():
                lines.append(f"- {s.strip()}")
    elif isinstance(summary, str) and summary.strip():
        for s in summary.split(". "):
            if s.strip():
                lines.append(f"- {s.strip()}.")

    # ---------------- Professional Experience ----------------
    total_exp = data.get("total_experience_years", "Not Provided")
    lines.append(f"\nPROFESSIONAL EXPERIENCE ({total_exp} Years)")

    experiences = data.get("professional_experience", [])
    # Sort descending by duration if possible (assumes current experience first in data)
    for exp in experiences:
        job_role = exp.get("job_role", "Not Provided")
        dept = exp.get("department", "")
        duration = exp.get("duration", "Not Provided")
        header_line = f"{job_role}"
        if dept:
            header_line += f" - {dept}"
        header_line += f", {duration}"
        lines.append(f"\n{header_line}")

        # Project Description
        proj_desc = exp.get("project_description", [])
        if proj_desc:
            lines.append("Project Description:")
            for p in proj_desc:
                if p.strip():
                    lines.append(f"- {p.strip()}")

        # Roles & Responsibilities
        roles = exp.get("roles_and_responsibilities", [])
        if roles:
            lines.append("Roles & Responsibilities:")
            for r in roles:
                if r.strip():
                    lines.append(f"- {r.strip()}")

    # ---------------- Skills ----------------
    lines.append("\nSKILLS")
    skills = data.get("skills", []) or data.get("primary_skill_set", [])
    if isinstance(skills, list) and skills:
        for s in skills:
            if isinstance(s, str) and s.strip():
                lines.append(f"- {s.strip()}")
            elif isinstance(s, dict):
                skill_name = s.get("skill") or s.get("name")
                if skill_name and skill_name.strip():
                    lines.append(f"- {skill_name.strip()}")
    elif isinstance(skills, dict):
        for category, items in skills.items():
            lines.append(f"{category}:")
            for s in items:
                if s.strip():
                    lines.append(f"- {s.strip()}")

    # ---------------- Certifications ----------------
    lines.append("\nCERTIFICATIONS")
    for c in data.get("certifications", []):
        # Handle dict or string
        if isinstance(c, dict):
            # Assuming LLM returns something like {"cert": "..."}
            c_text = c.get("cert") or c.get("name") or ""
        else:
            c_text = str(c)

        if c_text.strip():
            lines.append(f"- {c_text.strip()}")



    # ---------------- Education ----------------
    lines.append("\nEDUCATION")

    for edu in data.get("education", []):
        degree = edu.get("degree") or "Not Provided"
        institution = edu.get("institution") or "Not Provided"
        year = edu.get("passout_year") or "Not Provided"

        # Fix if LLM put degree in institution field
        if degree == "Not Provided" and institution != "Not Provided":
            if any(keyword in institution for keyword in
                   ["Bachelor", "Master", "B.E", "B.Tech", "MCA", "MBA", "B.Com"]):
                degree, institution = institution, "Not Provided"

        # Skip empty rows
        if degree == "Not Provided" and institution == "Not Provided" and year == "Not Provided":
            continue

        # Append education in its own section, NOT under certifications
        lines.append(f"- {degree}, {institution}, {year}")

    return "\n".join(lines)