from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib import colors


def save_resume_as_pdf_reportlab(formatted_resume: str, filename="output/KPMG_Resume.pdf"):
    # Create PDF document
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            rightMargin=2 * cm, leftMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)

    elements = []

    # Define styles
    styles = getSampleStyleSheet()

    logo_style = ParagraphStyle('LogoStyle', fontName='Helvetica-Bold', fontSize=13, alignment=TA_RIGHT)
    name_style = ParagraphStyle('NameStyle', fontName='Helvetica-Bold', fontSize=13)
    section_style = ParagraphStyle('SectionStyle', fontName='Helvetica-Bold', fontSize=10, spaceBefore=10)
    job_style = ParagraphStyle('JobStyle', fontName='Helvetica-Bold', fontSize=8.5, spaceBefore=6)
    bullet_style = ParagraphStyle('BulletStyle', fontName='Helvetica', fontSize=8.5, leftIndent=12, bulletIndent=0,
                                  spaceBefore=2)

    # Split the resume by lines
    lines = formatted_resume.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # KPMG Logo right-aligned
        if "[KPMG Logo]" in line:
            elements.append(Paragraph("KPMG Logo", logo_style))
            elements.append(Spacer(1, 0.3 * cm))

        # Name and skillset
        elif " - " in line and not line.startswith("-"):
            elements.append(Paragraph(line, name_style))
            elements.append(Spacer(1, 0.2 * cm))

        # Sections like Summary, Professional Summary, Skills, Education
        elif line.lower() in ["summary", "professional summary", "skills:", "certifications", "education:"]:
            elements.append(Paragraph(line, section_style))
            elements.append(Spacer(1, 0.2 * cm))

        # Job roles, ProjectDescription, Role & Responsibilities
        elif (" - " in line and "-" not in line[:2]) or line.lower().startswith(
                "role & responsibilities") or line.lower().startswith("projectdescription"):
            elements.append(Paragraph(line, job_style))
            elements.append(Spacer(1, 0.1 * cm))

        # Bullet points
        elif line.startswith("-") or line.startswith("•"):
            # Remove bullet from original text and use ListFlowable
            bullet_text = line.lstrip("-").lstrip("•").strip()
            bullet_item = ListFlowable([ListItem(Paragraph(bullet_text, bullet_style), bulletColor=colors.black)],
                                       bulletType='bullet')
            elements.append(bullet_item)
            elements.append(Spacer(1, 0.05 * cm))

        # Regular paragraph text
        else:
            elements.append(Paragraph(line, bullet_style))
            elements.append(Spacer(1, 0.05 * cm))

    # Build PDF
    doc.build(elements)
    print(f"✅ Resume saved successfully as '{filename}'")
