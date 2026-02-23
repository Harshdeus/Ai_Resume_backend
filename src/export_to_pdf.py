from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors


def normalize_bullets(text: str) -> str:
    lines = text.split("\n")
    new_lines = []

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("-") or stripped.startswith("•"):
            new_lines.append("• " + stripped.lstrip("-• ").strip())
        else:
            new_lines.append(line)

    return "\n".join(new_lines)


def save_resume_as_pdf_reportlab(formatted_resume: str, filename="output/KPMG_Resume.pdf"):

    # Register fonts
    pdfmetrics.registerFont(TTFont("Calibri", "calibri.ttf"))
    pdfmetrics.registerFont(TTFont("Calibri-Bold", "calibrib.ttf"))

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    elements = []

    formatted_resume = normalize_bullets(formatted_resume)
    lines = formatted_resume.split("\n")

    # ================= STYLES ================= #

    logo_style = ParagraphStyle(
        name="Logo",
        fontName="Calibri-Bold",
        fontSize=13,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#00338D"),
        spaceAfter=8
    )

    name_style = ParagraphStyle(
        name="Name",
        fontName="Calibri-Bold",
        fontSize=13,
        alignment=TA_LEFT,
        spaceAfter=10
    )

    section_heading_style = ParagraphStyle(
        name="SectionHeading",
        fontName="Calibri-Bold",
        fontSize=10,
        spaceBefore=10,
        spaceAfter=4
    )

    job_role_style = ParagraphStyle(
        name="JobRole",
        fontName="Calibri-Bold",
        fontSize=8.5,
        spaceBefore=6,
        spaceAfter=2
    )

    paragraph_style = ParagraphStyle(
        name="Paragraph",
        fontName="Calibri",
        fontSize=8.5,
        leading=11,
        spaceAfter=3,
        alignment=TA_JUSTIFY
    )

    bullet_style = ParagraphStyle(
        name="Bullet",
        fontName="Calibri",
        fontSize=8.5,
        leading=11,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3,
        alignment=TA_JUSTIFY
    )

    # ========================================= #

    for line in lines:
        line = line.strip()

        if not line:
            elements.append(Spacer(1, 4))
            continue

        # Right aligned KPMG logo
        if "[KPMG Logo]" in line:
            elements.append(Paragraph("KPMG", logo_style))
            continue

        # Name + Skills line
        if " - " in line and "Procurement" in line:
            elements.append(Paragraph(line, name_style))
            continue

        # Section headings
        if line.lower() in [
            "summary",
            "professional summary (11+ years)",
            "skills:",
            "certifications:",
            "education:"
        ]:
            elements.append(Paragraph(line.replace(":", "").title(), section_heading_style))
            continue

        # Job role lines
        if any(keyword in line for keyword in [
            "External Talent", "Procurement Advisor", "Primary Associate"
        ]):
            elements.append(Paragraph(line, job_role_style))
            continue

        # Project Description / Role & Responsibilities
        if line.lower().startswith("project description") or line.lower().startswith("role & responsibilities"):
            elements.append(Paragraph(line, section_heading_style))
            continue

        # Bullet points
        if line.startswith("•"):
            clean_line = line.lstrip("• ").strip()
            if clean_line:
                elements.append(Paragraph(f"• {clean_line}", bullet_style))
            continue

        # Default paragraph
        elements.append(Paragraph(line, paragraph_style))

    doc.build(elements)
    print(f" Resume saved successfully as '{filename}'")