from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os


def create_kpmg_template_pdf(resume_data, filename="output/KPMG_Template.pdf"):
    src_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(src_dir)
    file_path = os.path.join(project_root, filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Register fonts (optional - will use Helvetica if Calibri not available)
    try:
        pdfmetrics.registerFont(TTFont("Calibri", "calibri.ttf"))
        pdfmetrics.registerFont(TTFont("Calibri-Bold", "calibrib.ttf"))
        font_name = "Calibri"
        font_bold = "Calibri-Bold"
    except:
        font_name = "Helvetica"
        font_bold = "Helvetica-Bold"
        print("⚠️ Calibri font not found, using Helvetica instead")

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    elements = []

    # ---------------- Styles ---------------- #
    logo_style = ParagraphStyle(
        "Logo",
        fontName=font_bold,
        fontSize=14,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#00338D"),
        spaceAfter=8
    )

    name_style = ParagraphStyle(
        "Name",
        fontName=font_bold,
        fontSize=13,
        spaceAfter=12,
        textColor=colors.HexColor("#00338D")
    )

    heading_style = ParagraphStyle(
        "Heading",
        fontName=font_bold,
        fontSize=11,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#00338D")
    )

    subheading_style = ParagraphStyle(
        "SubHeading",
        fontName=font_bold,
        fontSize=10,
        spaceBefore=8,
        spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        fontName=font_name,
        fontSize=10,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3,
        alignment=TA_JUSTIFY,
        leading=14
    )

    # ---------------- Header ---------------- #
    elements.append(Paragraph("KPMG", logo_style))
    elements.append(Spacer(1, 12))

    name = resume_data.get("name", "")
    skills = resume_data.get("skills", [])
    skills_text = ", ".join(skills[:5]) if isinstance(skills, list) and skills else ""

    elements.append(Paragraph(f"{name} – {skills_text}", name_style))

    # ---------------- Summary ---------------- #
    elements.append(Paragraph("Summary", heading_style))
    if resume_data.get("summary"):
        for point in resume_data.get("summary", []):
            if point and isinstance(point, str) and point.strip():
                elements.append(Paragraph(f"• {point}", bullet_style))
    else:
        elements.append(Paragraph("• No summary provided", bullet_style))

    # ---------------- Professional Summary ---------------- #
    ps = resume_data.get("professional_summary", {})
    years = ps.get("years_of_experience", "")

    if years:
        elements.append(Paragraph(f"Professional Summary ({years} Years)", heading_style))
    else:
        elements.append(Paragraph("Professional Summary", heading_style))

    experience_list = ps.get("experience", [])

    # Ensure list
    if not isinstance(experience_list, list):
        experience_list = [experience_list] if experience_list else []

    if experience_list:
        for exp in experience_list:
            if not exp:
                continue

            # Case 1: exp is simple string
            if isinstance(exp, str):
                if exp.strip():
                    elements.append(Paragraph(f"• {exp}", bullet_style))

            # Case 2: exp is dict (structured work experience)
            elif isinstance(exp, dict):
                job = exp.get("job_role", "")
                dept = exp.get("department", "")
                duration = exp.get("duration", "")
                company = exp.get("company", "")

                # Build job line with all available info
                job_parts = []
                if job:
                    job_parts.append(job)
                if dept:
                    job_parts.append(dept)
                if company:
                    job_parts.append(f"at {company}")

                job_line = " ".join(job_parts)
                if duration:
                    job_line += f", {duration}"

                if job_line.strip():
                    elements.append(Paragraph(job_line, subheading_style))

                # Project Description
                project_desc = exp.get("project_description", [])
                if project_desc:
                    if isinstance(project_desc, str):
                        project_desc = [project_desc] if project_desc.strip() else []

                    if project_desc:
                        elements.append(Paragraph("Project Description:", subheading_style))
                        for desc in project_desc:
                            if desc and isinstance(desc, str) and desc.strip():
                                # Handle multi-line descriptions
                                if '\n' in desc:
                                    sub_lines = [line.strip() for line in desc.split('\n') if line.strip()]
                                    for sub_line in sub_lines:
                                        elements.append(Paragraph(f"• {sub_line}", bullet_style))
                                else:
                                    elements.append(Paragraph(f"• {desc}", bullet_style))

                # Roles & Responsibilities
                roles = exp.get("roles_and_responsibilities", [])
                if roles:
                    if isinstance(roles, str):
                        roles = [roles] if roles.strip() else []

                    if roles:
                        elements.append(Paragraph("Role & Responsibilities:", subheading_style))
                        for role in roles:
                            if role and isinstance(role, str) and role.strip():
                                elements.append(Paragraph(f"• {role}", bullet_style))
    else:
        elements.append(Paragraph("• No work experience listed", bullet_style))

    elements.append(Spacer(1, 6))

    # ---------------- Skills ---------------- #
    elements.append(Paragraph("Skills", heading_style))
    if resume_data.get("skills"):
        for skill in resume_data.get("skills", []):
            if skill and isinstance(skill, str) and skill.strip():
                # Handle comma-separated skills
                if ',' in skill:
                    sub_skills = [s.strip() for s in skill.split(',') if s.strip()]
                    for sub_skill in sub_skills:
                        elements.append(Paragraph(f"• {sub_skill}", bullet_style))
                else:
                    elements.append(Paragraph(f"• {skill}", bullet_style))
    else:
        elements.append(Paragraph("• No skills listed", bullet_style))

    # ---------------- Certifications ---------------- #
    elements.append(Paragraph("Certifications", heading_style))  # Always show heading

    certifications_data = resume_data.get("certifications", [])
    if certifications_data:
        for cert in certifications_data:
            if not cert:
                continue

            if isinstance(cert, dict):
                # Try multiple field names for certification title
                title = (cert.get("title") or
                         cert.get("name") or
                         cert.get("certification") or
                         cert.get("certificate_name") or
                         "")

                # If no title found but dict has other fields, create a readable string
                if not title:
                    # Get all non-empty values
                    values = [str(v) for v in cert.values() if v and str(v).strip()]
                    if values:
                        title = " - ".join(values)
                    else:
                        continue  # Skip empty certification
            else:
                title = str(cert) if cert and str(cert).strip() else ""

            if title and title.strip() and title != "{}":
                elements.append(Paragraph(f"• {title}", bullet_style))
    else:
        elements.append(Paragraph("• No certifications listed", bullet_style))

    # ---------------- Education ---------------- #
    elements.append(Paragraph("Education", heading_style))  # Always show heading

    education_data = resume_data.get("education", [])
    if education_data:
        for edu in education_data:
            if not edu:
                continue

            if isinstance(edu, dict):
                # Try ALL possible field name variations with clear priority
                degree = (edu.get("degree_name") or  # Priority 1: exact schema match
                          edu.get("degree") or  # Priority 2: common alternative
                          edu.get("qualification") or  # Priority 3: other variations
                          "")

                institute = (edu.get("institute_name") or  # Priority 1: exact schema match
                             edu.get("institution") or  # Priority 2: common alternative
                             edu.get("institute") or  # Priority 3: other variations
                             edu.get("college") or
                             edu.get("school") or
                             "")

                university = (edu.get("university_name") or  # Priority 1: exact schema match
                              edu.get("university") or  # Priority 2: common alternative
                              edu.get("uni") or
                              "")

                year = (edu.get("passout_year") or  # Priority 1: exact schema match
                        edu.get("year") or  # Priority 2: common alternative
                        edu.get("graduation_year") or
                        edu.get("passing_year") or
                        edu.get("batch") or
                        "")

                # Build line with only non-empty fields
                parts = []
                if degree and degree.strip():
                    parts.append(degree.strip())
                if institute and institute.strip():
                    parts.append(institute.strip())
                if university and university.strip() and university != institute:
                    parts.append(university.strip())
                if year and str(year).strip():
                    parts.append(f"({str(year).strip()})")

                if parts:
                    line = " ".join(parts)
                    elements.append(Paragraph(f"• {line}", bullet_style))
                # Skip if all fields are empty
            elif isinstance(edu, str) and edu.strip():
                elements.append(Paragraph(f"• {edu}", bullet_style))
    else:
        elements.append(Paragraph("• No education listed", bullet_style))

    # ---------------- Build PDF ---------------- #
    try:
        doc.build(elements)
        print(f"✅ PDF created successfully at:\n{file_path}")
    except Exception as e:
        print(f"❌ Error creating PDF: {e}")
        raise