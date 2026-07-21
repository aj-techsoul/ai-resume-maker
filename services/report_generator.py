import io
import json
import re
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def generate_radar_chart(score, user_id):
    """
    Renders an 8-axis polar radar chart for the candidate scores and saves it
    to a temporary file, returning the file path.
    """
    labels = ['ATS Compatibility', 'Technical Skills', 'Soft Skills', 'Communication', 'Experience', 'Education', 'Projects', 'Certifications']
    
    values = [
        score.ats_compatibility,
        score.tech_skills,
        score.soft_skills,
        score.communication,
        score.experience_score,
        score.education_score,
        score.projects_score,
        score.certifications_score
    ]
    
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    
    # Close the polar plot loop
    values += values[:1]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(3, 3), subplot_kw=dict(polar=True))
    
    # Set labels around the radar plot
    plt.xticks(angles[:-1], labels, color='#475569', size=6)
    
    # Hide radial labels to keep visual layout clean
    ax.set_yticklabels([])
    plt.ylim(0, 100)
    
    # Plot and fill data
    ax.plot(angles, values, color='#3B82F6', linewidth=2, linestyle='solid')
    ax.fill(angles, values, color='#3B82F6', alpha=0.25)
    
    # Style polar grid lines
    ax.spines['polar'].set_color('#CBD5E1')
    ax.grid(color='#E2E8F0')
    
    plt.tight_layout()
    
    # Save chart image to a temp location
    temp_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'reports')
    os.makedirs(temp_dir, exist_ok=True)
    chart_path = os.path.join(temp_dir, f"radar_u{user_id}.png")
    
    plt.savefig(chart_path, format='png', dpi=150, bbox_inches='tight', transparent=True)
    plt.close()
    
    return chart_path


def draw_qr_code(canvas, doc):
    """
    ReportLab callback to draw a vector mock QR code and report footer.
    """
    canvas.saveState()
    
    # Footer line
    canvas.setStrokeColor(colors.HexColor('#E2E8F0'))
    canvas.setLineWidth(0.5)
    canvas.line(40, 50, 572, 50)
    
    # Footer text
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#64748B'))
    canvas.drawString(40, 36, "CONFIDENTIAL - Screening report generated for HR recruitment selection. Verify credentials before offer release.")
    canvas.drawRightString(572, 36, "Page 1 of 1")
    
    # QR Code at the bottom right corner (above footer)
    qx = 512
    qy = 60
    qsize = 60
    
    canvas.setFillColor(colors.HexColor('#0F172A'))
    canvas.rect(qx - 2, qy - 2, qsize + 4, qsize + 4, fill=0, stroke=1) # Outer border box
    
    # Finder Pattern corner square grids helper
    def draw_finder(px, py):
        canvas.setFillColor(colors.HexColor('#0F172A'))
        canvas.rect(px, py, 14, 14, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.rect(px + 2, py + 2, 10, 10, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor('#0F172A'))
        canvas.rect(px + 4, py + 4, 6, 6, fill=1, stroke=0)
        
    draw_finder(qx, qy + qsize - 14)            # Top-Left finder
    draw_finder(qx + qsize - 14, qy + qsize - 14)  # Top-Right finder
    draw_finder(qx, qy)                        # Bottom-Left finder
    
    # Data bits simulation (deterministic seed)
    import random
    random.seed(42 + doc.page)
    block_size = 2
    for r in range(qsize // block_size):
        for c in range(qsize // block_size):
            # Skip finder blocks
            if (r < 7 and c < 7) or (r < 7 and c > (qsize // block_size - 8)) or (r > (qsize // block_size - 8) and c < 7):
                continue
            if random.choice([True, False]):
                canvas.setFillColor(colors.HexColor('#0F172A'))
                canvas.rect(qx + r * block_size, qy + c * block_size, block_size, block_size, fill=1, stroke=0)
                
    canvas.setFont('Helvetica-Bold', 7)
    canvas.setFillColor(colors.HexColor('#1E3A8A'))
    canvas.drawRightString(qx - 8, qy + 34, "SCAN TO VIEW")
    canvas.setFont('Helvetica', 6)
    canvas.setFillColor(colors.HexColor('#64748B'))
    canvas.drawRightString(qx - 8, qy + 24, "ONLINE PROFILE")
    
    canvas.restoreState()


def generate_resume_report_pdf(user, job, resume, score, rank_num=None):
    """
    Builds a professional, single-page enterprise applicant analysis report in PDF.
    Generates a polar radar chart dynamically, draws vector QR components, and structures
    the score breakdowns.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=40, leftMargin=40, 
        topMargin=40, bottomMargin=60 # extra space for footer
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Theme specific fonts and alignments
    title_style = ParagraphStyle(
        'RepTitle', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=20, leading=24,
        textColor=colors.HexColor('#1E3A8A')
    )
    
    subtitle_style = ParagraphStyle(
        'RepSub', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, leading=12,
        textColor=colors.HexColor('#64748B'), spaceAfter=12
    )
    
    section_title = ParagraphStyle(
        'RepSec', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=12, leading=16,
        textColor=colors.HexColor('#1E3A8A'), spaceBefore=8, spaceAfter=4
    )
    
    body_style = ParagraphStyle(
        'RepBody', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=11,
        textColor=colors.HexColor('#334155')
    )
    
    bullet_style = ParagraphStyle(
        'RepBullet', parent=body_style,
        leftIndent=12, firstLineIndent=-8, spaceAfter=2
    )
    
    # 1. HEADER BAND
    story.append(Paragraph("AI Resume Intelligence Analysis Report", title_style))
    story.append(Paragraph(f"Candidate Profile Evaluation | Generated on {datetime.now().strftime('%Y-%m-%d')} for HR Portal", subtitle_style))
    
    # 2. PROFILE DETAILS TABLE
    rank_tier_text = "N/A"
    if rank_num:
        # Determine medal or tier
        if score.overall_intelligence_score >= 85:
            rank_tier_text = f"Rank #{rank_num} &bull; Gold Medal (Top Candidate)"
        elif score.overall_intelligence_score >= 70:
            rank_tier_text = f"Rank #{rank_num} &bull; Silver Medal (Highly Recommended)"
        else:
            rank_tier_text = f"Rank #{rank_num} &bull; Bronze Medal (Recommended)"
            
    info_data = [
        [
            Paragraph(f"<b>Candidate Name:</b> {user.full_name}", body_style),
            Paragraph(f"<b>Applied Position:</b> {job.title}", body_style)
        ],
        [
            Paragraph(f"<b>Email Address:</b> {user.email}", body_style),
            Paragraph(f"<b>Target Department:</b> {job.department}", body_style)
        ],
        [
            Paragraph(f"<b>Evaluation Rating:</b> {score.match_rating}", body_style),
            Paragraph(f"<b>Hiring Status:</b> {rank_tier_text}", body_style)
        ]
    ]
    
    info_table = Table(info_data, colWidths=[260, 260])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LINEBELOW', (0,2), (1,2), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8))
    
    # 3. SCORE PROFILE AND RADAR CHART (Two Column Layout)
    chart_file = None
    try:
        chart_file = generate_radar_chart(score, user.id)
    except Exception as e:
        print(f"Error drawing radar graph: {e}")
        
    score_sum_style = ParagraphStyle(
        'ScoreSum', fontName='Helvetica-Bold', fontSize=32, leading=36,
        textColor=colors.HexColor('#1E3A8A'), alignment=1
    )
    
    score_desc = []
    score_desc.append(Spacer(1, 10))
    score_desc.append(Paragraph("OVERALL INTEL CORE", ParagraphStyle('Sc1', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#475569'), alignment=1)))
    score_desc.append(Paragraph(f"{score.overall_intelligence_score}", score_sum_style))
    score_desc.append(Paragraph("SCORE SCALE: 0 - 100", ParagraphStyle('Sc2', fontName='Helvetica', fontSize=7, textColor=colors.HexColor('#94A3B8'), alignment=1)))
    score_desc.append(Spacer(1, 10))
    
    # Table showing core 12 breakdowns inside PDF
    score_metrics_data = [
        [Paragraph("<b>ATS Match</b>", body_style), Paragraph(f"{score.ats_compatibility}%", body_style),
         Paragraph("<b>Formatting</b>", body_style), Paragraph(f"{score.formatting_score}%", body_style)],
        [Paragraph("<b>Tech Skills</b>", body_style), Paragraph(f"{score.tech_skills}%", body_style),
         Paragraph("<b>Grammar</b>", body_style), Paragraph(f"{score.grammar_score}%", body_style)],
        [Paragraph("<b>Soft Skills</b>", body_style), Paragraph(f"{score.soft_skills}%", body_style),
         Paragraph("<b>Professionalism</b>", body_style), Paragraph(f"{score.professionalism_score}%", body_style)],
        [Paragraph("<b>Readability</b>", body_style), Paragraph(f"{score.readability_score}%", body_style),
         Paragraph("<b>Project Quality</b>", body_style), Paragraph(f"{score.projects_score}%", body_style)]
    ]
    
    score_metrics_table = Table(score_metrics_data, colWidths=[80, 45, 80, 45])
    score_metrics_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    score_desc.append(score_metrics_table)
    
    middle_row = [score_desc, Paragraph("Radar Chart Unavailable", body_style)]
    if chart_file and os.path.exists(chart_file):
        middle_row[1] = Image(chart_file, width=180, height=180)
        
    middle_table = Table([middle_row], colWidths=[290, 230])
    middle_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(middle_table)
    story.append(Spacer(1, 4))
    
    # 4. SKILL GAP GRID
    story.append(Paragraph("Skill Gaps & Keyword Alignment", section_title))
    present_skills = json.loads(score.skills_present)
    missing_skills = json.loads(score.skills_missing)
    high_priority = json.loads(score.high_priority_skills) if score.high_priority_skills else []
    
    gap_info = [
        [Paragraph("<b>Matched Skills</b>", body_style), Paragraph(", ".join(present_skills) if present_skills else "None", body_style)],
        [Paragraph("<b>Missing Required</b>", body_style), Paragraph(f"<font color='#991B1B'><b>{', '.join(missing_skills) if missing_skills else 'None (100% Match)'}</b></font>", body_style)],
        [Paragraph("<b>High Priority Gaps</b>", body_style), Paragraph(", ".join(high_priority) if high_priority else "None", body_style)]
    ]
    
    gap_table = Table(gap_info, colWidths=[110, 410])
    gap_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(gap_table)
    story.append(Spacer(1, 6))
    
    # 5. AI EXEC SUMMARY & ADVICE
    insights_list = []
    insights_list.append(Paragraph("Executive Summary & AI Insights", section_title))
    insights_list.append(Paragraph(score.insights_summary or "No executive insights generated.", ParagraphStyle('SummaryText', parent=body_style, spaceAfter=6)))
    
    strengths_list = json.loads(score.strengths)
    weaknesses_list = json.loads(score.weaknesses)
    
    left_block = [Paragraph("<b>KEY STRENGTHS</b>", ParagraphStyle('F1', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#065F46')))]
    for st in strengths_list[:3]:
        left_block.append(Paragraph(f"&bull; {st}", bullet_style))
        
    right_block = [Paragraph("<b>DEVELOPMENT AREAS</b>", ParagraphStyle('F2', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#991B1B')))]
    for wk in weaknesses_list[:3]:
        right_block.append(Paragraph(f"&bull; {wk}", bullet_style))
        
    feedback_table = Table([[left_block, right_block]], colWidths=[255, 255])
    feedback_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#FFF5F5')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    insights_list.append(feedback_table)
    
    story.append(KeepTogether(insights_list))
    
    # Build PDF with QR Canvas
    doc.build(story, onFirstPage=lambda c, d: draw_qr_code(c, doc))
    
    # Clean up temp file
    if chart_file and os.path.exists(chart_file):
        try:
            os.remove(chart_file)
        except Exception:
            pass
            
    buffer.seek(0)
    return buffer
