import io
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

TEMPLATE_PRIMARY_COLORS = {
    "professional": colors.HexColor('#1E3A8A'),     # Executive Navy Blue
    "corporate": colors.HexColor('#334155'),        # Slate Gray
    "modern": colors.HexColor('#047857'),           # Emerald Green
    "ats_standard": colors.HexColor('#0F172A'),     # High Parsing Dark Slate
    "minimal": colors.HexColor('#1E293B'),          # Charcoal Black
    "executive": colors.HexColor('#4338CA'),        # Royal Indigo
    "creative": colors.HexColor('#BE185D'),         # Accent Pink
    "software_engineer": colors.HexColor('#2563EB'),# Blue
    "data_scientist": colors.HexColor('#059669'),   # Emerald Dark
    "business_analyst": colors.HexColor('#D97706')  # Amber Gold
}

TEMPLATE_DOCX_COLORS = {
    "professional": RGBColor(30, 58, 138),
    "corporate": RGBColor(51, 65, 85),
    "modern": RGBColor(4, 120, 87),
    "ats_standard": RGBColor(15, 23, 42),
    "minimal": RGBColor(30, 41, 59),
    "executive": RGBColor(67, 56, 202),
    "creative": RGBColor(190, 24, 93),
    "software_engineer": RGBColor(37, 99, 235),
    "data_scientist": RGBColor(5, 150, 105),
    "business_analyst": RGBColor(217, 119, 6)
}


def generate_candidate_pdf(resume_data, template_style="professional"):
    """
    Generates a PDF buffer using ReportLab for candidate resume data.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    primary_color = TEMPLATE_PRIMARY_COLORS.get(template_style, TEMPLATE_PRIMARY_COLORS["professional"])
    styles = getSampleStyleSheet()

    # Define custom paragraph styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#475569')
    )

    contact_style = ParagraphStyle(
        'ContactInfo',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B')
    )

    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#1E293B')
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        leftIndent=12,
        textColor=colors.HexColor('#334155')
    )

    elements = []

    # 1. Header (Name, Title, Contact Info)
    full_name = resume_data.get("full_name", "Jane Doe")
    prof_title = resume_data.get("professional_title", "Professional Candidate")
    elements.append(Paragraph(full_name, title_style))
    elements.append(Paragraph(prof_title, subtitle_style))
    elements.append(Spacer(1, 4))

    contact_parts = []
    if resume_data.get("email"): contact_parts.append(f"Email: {resume_data.get('email')}")
    if resume_data.get("phone"): contact_parts.append(f"Phone: {resume_data.get('phone')}")
    if resume_data.get("address"): contact_parts.append(f"Location: {resume_data.get('address')}")
    if resume_data.get("linkedin"): contact_parts.append(f"LinkedIn: {resume_data.get('linkedin')}")
    if resume_data.get("github"): contact_parts.append(f"GitHub: {resume_data.get('github')}")
    if resume_data.get("portfolio"): contact_parts.append(f"Portfolio: {resume_data.get('portfolio')}")

    contact_line = " | ".join(contact_parts)
    elements.append(Paragraph(contact_line, contact_style))
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8))

    # 2. Professional Summary / Career Objective
    objective = resume_data.get("career_objective")
    if objective:
        elements.append(Paragraph("CAREER OBJECTIVE & SUMMARY", heading_style))
        elements.append(Paragraph(objective, body_style))
        elements.append(Spacer(1, 6))

    # 3. Work Experience
    exps = resume_data.get("work_experience", [])
    if exps and isinstance(exps, list):
        elements.append(Paragraph("WORK EXPERIENCE", heading_style))
        for exp in exps:
            if isinstance(exp, dict):
                job_head = f"<b>{exp.get('title', '')}</b> — {exp.get('company', '')} ({exp.get('duration', '')})"
                elements.append(Paragraph(job_head, body_style))
                resps = exp.get("responsibilities", [])
                if isinstance(resps, list):
                    for r in resps:
                        elements.append(Paragraph(f"• {r}", bullet_style))
                elements.append(Spacer(1, 4))

    # 4. Internships
    internships = resume_data.get("internships", [])
    if internships and isinstance(internships, list):
        elements.append(Paragraph("INTERNSHIPS", heading_style))
        for item in internships:
            if isinstance(item, dict):
                head = f"<b>{item.get('role', '')}</b> — {item.get('organization', '')} ({item.get('duration', '')})"
                elements.append(Paragraph(head, body_style))
                if item.get("details"):
                    elements.append(Paragraph(f"• {item.get('details')}", bullet_style))
                elements.append(Spacer(1, 4))

    # 5. Projects
    projects = resume_data.get("projects", [])
    if projects and isinstance(projects, list):
        elements.append(Paragraph("KEY PROJECTS", heading_style))
        for p in projects:
            if isinstance(p, dict):
                p_head = f"<b>{p.get('title', '')}</b> [{p.get('tech_stack', '')}]"
                elements.append(Paragraph(p_head, body_style))
                if p.get("description"):
                    elements.append(Paragraph(p.get("description"), bullet_style))
                if p.get("impact"):
                    elements.append(Paragraph(f"<i>Impact: {p.get('impact')}</i>", bullet_style))
                elements.append(Spacer(1, 4))

    # 6. Education
    edu = resume_data.get("education", [])
    if edu and isinstance(edu, list):
        elements.append(Paragraph("EDUCATION", heading_style))
        for item in edu:
            if isinstance(item, dict):
                e_head = f"<b>{item.get('degree', '')}</b> — {item.get('institution', '')} ({item.get('year', '')})"
                elements.append(Paragraph(e_head, body_style))
                if item.get("gpa_details"):
                    elements.append(Paragraph(f"• {item.get('gpa_details')}", bullet_style))
                elements.append(Spacer(1, 4))

    # 7. Technical & Soft Skills
    tech_skills = resume_data.get("technical_skills", [])
    soft_skills = resume_data.get("soft_skills", [])
    if tech_skills or soft_skills:
        elements.append(Paragraph("SKILLS & COMPETENCIES", heading_style))
        if tech_skills:
            t_str = ", ".join(tech_skills) if isinstance(tech_skills, list) else str(tech_skills)
            elements.append(Paragraph(f"<b>Technical Skills:</b> {t_str}", body_style))
        if soft_skills:
            s_str = ", ".join(soft_skills) if isinstance(soft_skills, list) else str(soft_skills)
            elements.append(Paragraph(f"<b>Soft Skills:</b> {s_str}", body_style))
        elements.append(Spacer(1, 6))

    # 8. Certifications & Achievements
    certs = resume_data.get("certifications", [])
    achievements = resume_data.get("achievements", [])
    if certs or achievements:
        elements.append(Paragraph("CERTIFICATIONS & ACHIEVEMENTS", heading_style))
        if certs:
            c_str = ", ".join(certs) if isinstance(certs, list) else str(certs)
            elements.append(Paragraph(f"<b>Certifications:</b> {c_str}", body_style))
        if achievements:
            a_str = ", ".join(achievements) if isinstance(achievements, list) else str(achievements)
            elements.append(Paragraph(f"<b>Key Achievements:</b> {a_str}", body_style))
        elements.append(Spacer(1, 6))

    # 9. Languages & Hobbies
    langs = resume_data.get("languages", [])
    hobbies = resume_data.get("hobbies", [])
    if langs or hobbies:
        elements.append(Paragraph("LANGUAGES & ADDITIONAL INFO", heading_style))
        if langs:
            l_str = ", ".join(langs) if isinstance(langs, list) else str(langs)
            elements.append(Paragraph(f"<b>Languages:</b> {l_str}", body_style))
        if hobbies:
            h_str = ", ".join(hobbies) if isinstance(hobbies, list) else str(hobbies)
            elements.append(Paragraph(f"<b>Interests & Hobbies:</b> {h_str}", body_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_candidate_docx(resume_data, template_style="professional"):
    """
    Generates a DOCX buffer using python-docx for candidate resume data.
    """
    doc = docx.Document()

    # Page Margins
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.5)
        s.bottom_margin = Inches(0.5)
        s.left_margin = Inches(0.5)
        s.right_margin = Inches(0.5)

    primary_rgb = TEMPLATE_DOCX_COLORS.get(template_style, TEMPLATE_DOCX_COLORS["professional"])

    # Header Name
    p_name = doc.add_paragraph()
    run_name = p_name.add_run(resume_data.get("full_name", "Jane Doe"))
    run_name.font.size = Pt(20)
    run_name.font.bold = True
    run_name.font.color.rgb = primary_rgb

    # Title
    p_title = doc.add_paragraph()
    run_title = p_title.add_run(resume_data.get("professional_title", "Professional Title"))
    run_title.font.size = Pt(12)
    run_title.font.italic = True
    run_title.font.color.rgb = RGBColor(71, 85, 105)

    # Contact Details
    contact_parts = []
    if resume_data.get("email"): contact_parts.append(f"Email: {resume_data.get('email')}")
    if resume_data.get("phone"): contact_parts.append(f"Phone: {resume_data.get('phone')}")
    if resume_data.get("address"): contact_parts.append(f"Location: {resume_data.get('address')}")
    if resume_data.get("linkedin"): contact_parts.append(f"LinkedIn: {resume_data.get('linkedin')}")
    if resume_data.get("github"): contact_parts.append(f"GitHub: {resume_data.get('github')}")
    if resume_data.get("portfolio"): contact_parts.append(f"Portfolio: {resume_data.get('portfolio')}")

    p_contact = doc.add_paragraph(" | ".join(contact_parts))
    p_contact.runs[0].font.size = Pt(9)
    p_contact.runs[0].font.color.rgb = RGBColor(100, 116, 139)

    doc.add_paragraph("----------------------------------------------------------------------------------------------------")

    # Helper for Section Heading
    def add_section_heading(text):
        p = doc.add_paragraph()
        run = p.add_run(text.upper())
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = primary_rgb

    # Summary
    if resume_data.get("career_objective"):
        add_section_heading("Career Objective & Summary")
        doc.add_paragraph(resume_data.get("career_objective"))

    # Experience
    exps = resume_data.get("work_experience", [])
    if exps and isinstance(exps, list):
        add_section_heading("Work Experience")
        for exp in exps:
            if isinstance(exp, dict):
                p = doc.add_paragraph()
                r = p.add_run(f"{exp.get('title', '')} — {exp.get('company', '')} ({exp.get('duration', '')})")
                r.bold = True
                resps = exp.get("responsibilities", [])
                if isinstance(resps, list):
                    for resp in resps:
                        doc.add_paragraph(f"• {resp}")

    # Internships
    internships = resume_data.get("internships", [])
    if internships and isinstance(internships, list):
        add_section_heading("Internships")
        for item in internships:
            if isinstance(item, dict):
                p = doc.add_paragraph()
                r = p.add_run(f"{item.get('role', '')} — {item.get('organization', '')} ({item.get('duration', '')})")
                r.bold = True
                if item.get("details"):
                    doc.add_paragraph(f"• {item.get('details')}")

    # Projects
    projects = resume_data.get("projects", [])
    if projects and isinstance(projects, list):
        add_section_heading("Key Projects")
        for p in projects:
            if isinstance(p, dict):
                p_para = doc.add_paragraph()
                r = p_para.add_run(f"{p.get('title', '')} [{p.get('tech_stack', '')}]")
                r.bold = True
                if p.get("description"):
                    doc.add_paragraph(f"• {p.get('description')}")
                if p.get("impact"):
                    doc.add_paragraph(f"• Impact: {p.get('impact')}")

    # Education
    edu = resume_data.get("education", [])
    if edu and isinstance(edu, list):
        add_section_heading("Education")
        for item in edu:
            if isinstance(item, dict):
                p = doc.add_paragraph()
                r = p.add_run(f"{item.get('degree', '')} — {item.get('institution', '')} ({item.get('year', '')})")
                r.bold = True
                if item.get("gpa_details"):
                    doc.add_paragraph(f"• {item.get('gpa_details')}")

    # Skills
    tech_skills = resume_data.get("technical_skills", [])
    soft_skills = resume_data.get("soft_skills", [])
    if tech_skills or soft_skills:
        add_section_heading("Skills & Competencies")
        if tech_skills:
            doc.add_paragraph(f"Technical Skills: {', '.join(tech_skills) if isinstance(tech_skills, list) else str(tech_skills)}")
        if soft_skills:
            doc.add_paragraph(f"Soft Skills: {', '.join(soft_skills) if isinstance(soft_skills, list) else str(soft_skills)}")

    # Certifications & Achievements
    certs = resume_data.get("certifications", [])
    achievements = resume_data.get("achievements", [])
    if certs or achievements:
        add_section_heading("Certifications & Achievements")
        if certs:
            doc.add_paragraph(f"Certifications: {', '.join(certs) if isinstance(certs, list) else str(certs)}")
        if achievements:
            doc.add_paragraph(f"Achievements: {', '.join(achievements) if isinstance(achievements, list) else str(achievements)}")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
