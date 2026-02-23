from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm  # Fixed: was 'readabilipc' incorrectly
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import os
import re  # Added for regex operations


def normalize_bullets(text: str) -> str:
    """Convert various bullet formats to consistent • format"""
    lines = text.split("\n")
    new_lines = []

    for line in lines:
        stripped = line.lstrip()
        # Check for various bullet formats
        if stripped.startswith("-") or stripped.startswith("•") or stripped.startswith("*"):
            # Remove the bullet and clean up
            content = stripped.lstrip("-•* ").strip()
            new_lines.append("• " + content)
        else:
            new_lines.append(line)

    return "\n".join(new_lines)


def save_resume_as_pdf_reportlab(formatted_resume: str, filename="output/KPMG_Resume.pdf"):
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Register fonts (make sure these font files exist in your project)
    try:
        pdfmetrics.registerFont(TTFont("Calibri", "calibri.ttf"))
        pdfmetrics.registerFont(TTFont("Calibri-Bold", "calibrib.ttf"))
        font_name = "Calibri"
        font_bold = "Calibri-Bold"
    except:
        # Fallback to default fonts if Calibri not available
        font_name = "Helvetica"
        font_bold = "Helvetica-Bold"
        print("Warning: Calibri fonts not found, using Helvetica instead")

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
        fontName=font_bold,
        fontSize=14,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#00338D"),
        spaceAfter=8
    )

    name_style = ParagraphStyle(
        name="Name",
        fontName=font_bold,
        fontSize=14,
        alignment=TA_LEFT,
        spaceAfter=12,
        textColor=colors.HexColor("#00338D")
    )

    section_heading_style = ParagraphStyle(
        name="SectionHeading",
        fontName=font_bold,
        fontSize=11,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#00338D")
    )

    sub_heading_style = ParagraphStyle(
        name="SubHeading",
        fontName=font_bold,
        fontSize=10,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.black
    )

    job_role_style = ParagraphStyle(
        name="JobRole",
        fontName=font_bold,
        fontSize=9.5,
        spaceBefore=8,
        spaceAfter=2,
        textColor=colors.HexColor("#00338D")
    )

    paragraph_style = ParagraphStyle(
        name="Paragraph",
        fontName=font_name,
        fontSize=9,
        leading=12,
        spaceAfter=4,
        alignment=TA_JUSTIFY
    )

    bullet_style = ParagraphStyle(
        name="Bullet",
        fontName=font_name,
        fontSize=9,
        leading=12,
        leftIndent=20,
        firstLineIndent=-12,
        spaceAfter=3,
        alignment=TA_JUSTIFY
    )

    # ========================================= #

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            elements.append(Spacer(1, 6))
            i += 1
            continue

        try:
            # Handle KPMG Logo
            if "[KPMG Logo]" in line:
                elements.append(Paragraph("KPMG", logo_style))
                i += 1
                continue

            # Handle Name line (contains dash) - removed the undefined 'name' variable check
            if " - " in line:
                elements.append(Paragraph(line, name_style))
                i += 1
                continue

            # Handle section headings
            section_headings = ["Summary", "Professional Summary", "Skills", "Certifications", "Education"]
            if any(line.lower().startswith(heading.lower()) for heading in section_headings):
                # Clean up the heading
                heading_text = line.split('(')[0].strip().replace(':', '')
                elements.append(Paragraph(heading_text, section_heading_style))
                i += 1
                continue

            # Handle "Role & Responsibilities" and "Project Description" subheadings
            if line.lower().startswith("role & responsibilities") or line.lower().startswith("project description"):
                elements.append(Paragraph(line, sub_heading_style))
                i += 1
                continue

            # Handle job roles (they don't start with bullets)
            if not line.startswith("•") and not line.startswith("-") and len(line) > 10:
                # Check if this looks like a job title
                if any(keyword in line.lower() for keyword in
                       ["specialist", "advisor", "manager", "analyst", "associate"]):
                    elements.append(Paragraph(line, job_role_style))
                    i += 1
                    continue

            # Handle bullet points
            if line.startswith("•"):
                # Remove the bullet and clean up
                content = line[1:].strip()
                if content:
                    elements.append(Paragraph(f"• {content}", bullet_style))
                i += 1
                continue

            # Default paragraph
            elements.append(Paragraph(line, paragraph_style))
            i += 1

        except Exception as e:
            print(f"Warning: Could not process line: {line}")
            print(f"Error: {e}")
            # Skip problematic line and continue
            i += 1
            continue

    # Build PDF
    try:
        doc.build(elements)
        print(f"✅ Resume saved successfully as '{filename}'")
    except Exception as e:
        print(f"❌ Error building PDF: {e}")
        raise


# Example usage (optional - for testing)
if __name__ == "__main__":
    # Sample formatted resume text for testing
    sample_resume = """
    [KPMG Logo]
    DARSHAN SHROFF - Procurement Analysis, Category Management
    Summary:
    • Results-driven procurement professional with 11+ years of experience
    • Proven record of improving productivity, quality, and client satisfaction
    Professional Summary (11+ years):
    External Talent Category Specialist- Procurement, July 2023 – till date
    Role & Responsibilities:
    • Led supplier enablement and empanelment for niche IT skills
    • Managed end-to-end supplier onboarding and transition
    Skills:
    • Procurement Analysis & Management
    • Category Management
    Certifications:
    • Completed extensive Contracting Training
    Education:
    • Bachelor of Business Management (BBM) | Mysore University | 2011
    """

    save_resume_as_pdf_reportlab(sample_resume, "output/test_resume.pdf")