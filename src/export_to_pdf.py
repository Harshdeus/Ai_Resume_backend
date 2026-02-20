from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from reportlab.lib import colors


def save_resume_as_pdf_reportlab(formatted_resume: str, filename="output/KPMG_Resume.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            rightMargin=2 * cm, leftMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    elements = []

    # Styles
    logo_style = ParagraphStyle(name="Logo", fontSize=13, leading=14, alignment=TA_RIGHT,
                                spaceAfter=10, fontName="Helvetica-Bold", textColor=colors.HexColor("#00338D"))

    name_skills_style = ParagraphStyle(name="NameSkills", fontSize=13, leading=16, alignment=TA_LEFT,
                                       spaceAfter=12, fontName="Helvetica", textColor=colors.black)

    section_heading_style = ParagraphStyle(name="SectionHeading", fontSize=10, leading=12,
                                           spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold",
                                           textColor=colors.black)

    bullet_style = ParagraphStyle(name="Bullet", fontSize=8.5, leading=12,
                                  leftIndent=15, firstLineIndent=-10, spaceAfter=3,
                                  fontName="Helvetica", textColor=colors.black)

    job_role_style = ParagraphStyle(name="JobRole", fontSize=8.5, leading=12, spaceAfter=2,
                                    fontName="Helvetica-Bold", textColor=colors.black)

    sub_header_style = ParagraphStyle(name="SubHeader", fontSize=8.5, leading=12, spaceBefore=4, spaceAfter=2,
                                      fontName="Helvetica-Bold", textColor=colors.black)

    lines = formatted_resume.split("\n")
    cert_section_active = False

    for line in lines:
        line = line.strip()
        if not line:
            elements.append(Spacer(1, 4))
            continue

        # KPMG Logo - right aligned
        if "[KPMG Logo]" in line:
            elements.append(Paragraph("KPMG", logo_style))
            continue

        # Name of the candidate - skills set
        if "DAR SHROFF" in line and " - " in line:
            elements.append(Paragraph(line, name_skills_style))
            continue

        # Professional Summary (11+ years) specifically
        if line.startswith("Professional Summary ("):
            elements.append(Paragraph(line, section_heading_style))
            cert_section_active = False
            continue

        # Other section headings
        if line.lower() in ["summary", "skills", "education", "certification", "certifications"]:
            section_name = line.title()
            elements.append(Paragraph(section_name, section_heading_style))
            cert_section_active = "cert" in line.lower()
            continue

        # Job role lines
        if any(role in line for role in ["External Talent Category Specialist", "Procurement Advisor", "Primary Associate"]):
            elements.append(Paragraph(line, job_role_style))
            continue

        # Role & Responsibilities sub-heading
        if "Role & Responsibilities" in line:
            elements.append(Paragraph("Role & Responsibilities:", sub_header_style))
            continue

        # Handle bullet points (for Summary, Skills, Certifications, etc.)
        if line.startswith("-") or line.startswith("•"):
            clean_line = line.lstrip("-• ").strip()
            if clean_line:
                elements.append(Paragraph(f"• {clean_line}", bullet_style))
            continue

        # Handle lines in certifications section that may not start with bullet
        if cert_section_active and line:
            elements.append(Paragraph(f"• {line}", bullet_style))
            continue

        # Handle normal text lines outside bullets
        elements.append(Paragraph(line, bullet_style))

    doc.build(elements)
    print(f"✅ Resume saved successfully as '{filename}'")