from datetime import datetime, timedelta
from database_models.models import db, User, Job, Application, ResumeScore, Resume
from sqlalchemy import func
import json
from collections import Counter
import re

def get_dashboard_kpis():
    """
    Computes high-level KPI cards metrics for the recruiter dashboard.
    """
    total_candidates = User.query.filter_by(role='candidate').count()
    
    # Today's applications
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    todays_apps = Application.query.filter(Application.applied_at >= today_start).count()
    
    # Average ATS Score
    avg_score_query = db.session.query(func.avg(ResumeScore.ats_match_score)).scalar()
    avg_ats_score = round(avg_score_query, 1) if avg_score_query is not None else 0.0
    
    # Top Candidate
    best_rs = ResumeScore.query.order_by(ResumeScore.ats_match_score.desc()).first()
    top_candidate_name = "N/A"
    if best_rs and best_rs.resume:
        cand = User.query.get(best_rs.resume.candidate_id)
        if cand:
            top_candidate_name = f"{cand.full_name} ({best_rs.ats_match_score}%)"
            
    # Most Applied Position
    job_counts = db.session.query(Application.job_id, func.count(Application.id))\
        .group_by(Application.job_id).all()
    most_applied_job = "None"
    if job_counts:
        job_counts.sort(key=lambda x: x[1], reverse=True)
        top_job_id = job_counts[0][0]
        top_job = Job.query.get(top_job_id)
        if top_job:
            most_applied_job = f"{top_job.title} ({job_counts[0][1]} apps)"
            
    # Recent Uploads
    recent_resumes = Resume.query.order_by(Resume.created_at.desc()).limit(5).all()
    recent_uploads_list = []
    for r in recent_resumes:
        cand = User.query.get(r.candidate_id)
        if cand:
            recent_uploads_list.append({
                'name': cand.full_name,
                'filename': r.filename,
                'time': r.created_at.strftime('%Y-%m-%d %H:%M')
            })
            
    return {
        'total_candidates': total_candidates,
        'todays_apps': todays_apps,
        'avg_ats_score': avg_ats_score,
        'top_candidate': top_candidate_name,
        'most_applied_job': most_applied_job,
        'recent_uploads': recent_uploads_list
    }


def get_detailed_analytics(job_id=None):
    """
    Gathers aggregate numbers for graphing (daily apps, skills, education, experience, funnel).
    """
    # 1. Applications per Day (last 7 days)
    daily_apps = []
    days = []
    for i in range(6, -1, -1):
        day_date = (datetime.utcnow() - timedelta(days=i)).date()
        day_start = datetime.combine(day_date, datetime.min.time())
        day_end = datetime.combine(day_date, datetime.max.time())
        
        query = Application.query.filter(Application.applied_at.between(day_start, day_end))
        if job_id:
            query = query.filter_by(job_id=job_id)
        count = query.count()
        
        days.append(day_date.strftime('%b %d'))
        daily_apps.append(count)
        
    # 2. Hiring Funnel Status Counts
    funnel_stages = ['Applied', 'Screening', 'Shortlisted', 'Interview Scheduled', 'Technical Round', 'HR Round', 'Selected', 'Rejected']
    funnel_counts = []
    for stage in funnel_stages:
        query = Application.query.filter_by(status=stage)
        if job_id:
            query = query.filter_by(job_id=job_id)
        funnel_counts.append(query.count())
        
    # 3. Skill Distribution
    skill_counter = Counter()
    scores_query = ResumeScore.query
    if job_id:
        scores_query = scores_query.filter_by(job_id=job_id)
    scores = scores_query.all()
    
    for s in scores:
        try:
            present_skills = json.loads(s.skills_present)
            for skill in present_skills:
                skill_counter[skill] += 1
        except Exception:
            pass
            
    top_skills_data = skill_counter.most_common(8)
    skills_labels = [item[0] for item in top_skills_data]
    skills_values = [item[1] for item in top_skills_data]
    
    # 4. Education Distribution
    edu_counter = Counter()
    resumes_query = Resume.query
    if job_id:
        resumes_query = resumes_query.join(Application, Application.resume_id == Resume.id).filter(Application.job_id == job_id)
    resumes = resumes_query.all()
    
    for r in resumes:
        text = r.parsed_text.lower()
        if 'phd' in text or 'ph.d' in text or 'doctor' in text:
            edu_counter['PhD'] += 1
        elif 'master' in text or 'm.s' in text or 'ms' in text or 'mtech' in text or 'm.tech' in text:
            edu_counter['Masters'] += 1
        elif 'bachelor' in text or 'b.s' in text or 'bs' in text or 'btech' in text or 'b.tech' in text or 'degree' in text:
            edu_counter['Bachelors'] += 1
        else:
            edu_counter['Other'] += 1
            
    edu_labels = list(edu_counter.keys())
    edu_values = list(edu_counter.values())
    
    # 5. Experience Distribution (Buckets)
    exp_buckets = {'0-1 Years': 0, '1-3 Years': 0, '3-5 Years': 0, '5-8 Years': 0, '8+ Years': 0}
    for r in resumes:
        text = r.parsed_text.lower()
        exp_found = re.findall(r'(\d+)\+?\s*years?', text)
        years = max([int(y) for y in exp_found]) if exp_found else 0
        
        # Heuristics if no numbers found but work details exist
        if years == 0:
            if len(text.split()) > 300:
                years = 3 # assume middle
            else:
                years = 1 # assume junior
                
        if years <= 1:
            exp_buckets['0-1 Years'] += 1
        elif years <= 3:
            exp_buckets['1-3 Years'] += 1
        elif years <= 5:
            exp_buckets['3-5 Years'] += 1
        elif years <= 8:
            exp_buckets['5-8 Years'] += 1
        else:
            exp_buckets['8+ Years'] += 1
            
    exp_labels = list(exp_buckets.keys())
    exp_values = list(exp_buckets.values())
    
    # 6. Top Universities Extraction
    univ_counter = Counter()
    for r in resumes:
        # Simple regex heuristic search for university names
        univ_matches = re.findall(r'(?:university|institute|college|school)\s+of\s+[A-Za-z\s]+|[A-Za-z\s]+\s+(?:university|institute|college|school)', r.parsed_text, re.IGNORECASE)
        for u in univ_matches:
            clean_u = u.strip().title()
            # filter generic short words
            if len(clean_u.split()) > 1 and len(clean_u) < 40 and not any(kw in clean_u.lower() for kw in ['resume', 'profile', 'education']):
                univ_counter[clean_u] += 1
                break # count one major university per resume
                
    univ_data = univ_counter.most_common(5)
    univ_labels = [item[0] for item in univ_data]
    univ_values = [item[1] for item in univ_data]
    
    return {
        'daily_apps': {
            'labels': days,
            'values': daily_apps
        },
        'funnel': {
            'labels': funnel_stages,
            'values': funnel_counts
        },
        'skills': {
            'labels': skills_labels,
            'values': skills_values
        },
        'education': {
            'labels': edu_labels,
            'values': edu_values
        },
        'experience': {
            'labels': exp_labels,
            'values': exp_values
        },
        'universities': {
            'labels': univ_labels,
            'values': univ_values
        }
    }
