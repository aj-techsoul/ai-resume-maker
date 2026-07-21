import os
import json
import random
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_login import LoginManager, current_user, login_required
from database_models.models import db, User, Job, Resume, Application, ResumeScore, CandidateRanking, Notification, ActivityLog, Interview, PredictionLog, ModelInfo, CandidateResumeDraft, CandidateResumeVersion
from authentication.routes import auth
from parsers.resume_parser import parse_resume
from ai.scorer import score_resume_against_job
from ai.candidate_resume_assistant import (
    get_default_resume_data,
    calculate_candidate_resume_scores,
    generate_candidate_ai_suggestions,
    process_candidate_chat
)
from analytics.analyzer import get_dashboard_kpis, get_detailed_analytics
from services.report_generator import generate_resume_report_pdf
from services.candidate_resume_exporter import generate_candidate_pdf, generate_candidate_docx

app = Flask(__name__)
app.config['SECRET_KEY'] = 'antigravity-secret-key-182746'

# Configure directories
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'database', 'recruitment.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 # 5 MB limits

# Ensure storage directories exist
for folder in ['database', 'uploads', 'reports', 'exports', 'logs']:
    os.makedirs(os.path.join(BASE_DIR, folder), exist_ok=True)

# Initialize Database
db.init_app(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Expose global notifications to base layouts
@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(8).all()
        unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return dict(notifications=notifs, unread_notifications_count=unread_count)
    return dict(notifications=[], unread_notifications_count=0)

# Register Authentication Blueprints
app.register_blueprint(auth)

# HELPER: Append Timeline Step
def append_application_timeline(app_record, status, note=""):
    timeline_data = []
    if app_record.timeline:
        try:
            timeline_data = json.loads(app_record.timeline)
        except Exception:
            timeline_data = []
            
    timeline_data.append({
        'stage': status,
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M'),
        'note': note
    })
    app_record.timeline = json.dumps(timeline_data)

# HELPER: Compute & Cache rankings for a job posting
def update_job_rankings(job_id):
    apps = Application.query.filter_by(job_id=job_id).all()
    scored_apps = []
    
    for app_record in apps:
        score_record = ResumeScore.query.filter_by(resume_id=app_record.resume_id, job_id=job_id).first()
        score = score_record.overall_intelligence_score if score_record else 0.0
        scored_apps.append((app_record, score))
        
    # Sort candidates by ATS score descending
    scored_apps.sort(key=lambda x: x[1], reverse=True)
    
    # Delete old rankings for this job role
    CandidateRanking.query.filter_by(job_id=job_id).delete()
    
    # Commit new rankings
    for index, (app_record, score) in enumerate(scored_apps):
        rank = index + 1
        
        # Medals tier assignment
        if score >= 85 and rank <= 3:
            tier = 'Gold'
            overall_strength = 'Top Candidate'
        elif score >= 70:
            tier = 'Silver'
            overall_strength = 'Highly Recommended'
        elif score >= 55:
            tier = 'Bronze'
            overall_strength = 'Recommended'
        else:
            tier = 'None'
            overall_strength = 'Needs Improvement'
            
        ranking = CandidateRanking(
            job_id=job_id,
            candidate_id=app_record.candidate_id,
            rank_number=rank,
            overall_score=score,
            tier=tier,
            overall_strength=overall_strength
        )
        db.session.add(ranking)
        
    db.session.commit()

# --- ROUTES ---

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'candidate':
        return redirect(url_for('candidate_portal'))
        
    kpis = get_dashboard_kpis()
    # Add active openings KPI extra counts
    kpis['active_jobs'] = Job.query.count()
    kpis['shortlisted'] = Application.query.filter_by(status='Shortlisted').count()
    kpis['interviews'] = Interview.query.filter_by(status='Scheduled').count()
    kpis['success_rate'] = "84%"
    kpis['processing_time'] = "1.8s"
    
    active_jobs = Job.query.order_by(Job.created_at.desc()).all()
    chart_data = get_detailed_analytics()
    
    return render_template('dashboard.html', 
                           active_page='dashboard',
                           kpis=kpis, 
                           active_jobs=active_jobs,
                           chart_data=json.dumps(chart_data))


@app.route('/analytics')
@login_required
def analytics_portal():
    if current_user.role == 'candidate':
        return redirect(url_for('candidate_portal'))
        
    selected_job_id = request.args.get('job_id')
    if selected_job_id:
        try:
            selected_job_id = int(selected_job_id)
        except ValueError:
            selected_job_id = None
        
    jobs = Job.query.order_by(Job.title.asc()).all()
    chart_data = get_detailed_analytics(job_id=selected_job_id)
    
    return render_template('analytics.html',
                           active_page='analytics',
                           jobs=jobs,
                           selected_job_id=selected_job_id,
                           chart_data=json.dumps(chart_data))


@app.route('/candidate')
@login_required
def candidate_portal():
    if current_user.role == 'admin':
        return redirect(url_for('dashboard'))
        
    apps = Application.query.filter_by(candidate_id=current_user.id).order_by(Application.applied_at.desc()).all()
    available_jobs = Job.query.order_by(Job.title.asc()).all()
    interviews = Interview.query.filter_by(candidate_id=current_user.id).all()
    
    # Fetch Candidate Resume Draft if available
    draft = CandidateResumeDraft.query.filter_by(candidate_id=current_user.id, is_active=True).first()
    scores_obj = json.loads(draft.scores_json) if draft else {"overall_resume_score": 82, "ats_compatibility": 85, "resume_completeness": 90, "technical_strength": 78}
    
    # Process timelines for candidate view
    parsed_apps = []
    highest_score = 0.0
    for app_rec in apps:
        timeline_list = []
        if app_rec.timeline:
            try:
                timeline_list = json.loads(app_rec.timeline)
            except Exception:
                timeline_list = []
        score_item = ResumeScore.query.filter_by(resume_id=app_rec.resume_id, job_id=app_rec.job_id).first()
        if score_item and score_item.overall_intelligence_score > highest_score:
            highest_score = score_item.overall_intelligence_score
            
        parsed_apps.append({
            'app': app_rec,
            'timeline': timeline_list,
            'score': score_item
        })
        
    kpis = {
        'resume_completion': scores_obj.get('resume_completeness', 90),
        'ats_score': highest_score if highest_score > 0 else scores_obj.get('ats_compatibility', 85),
        'recruiter_views': len(apps) * 3 + 8,
        'applications_submitted': len(apps),
        'interview_invitations': len(interviews),
        'profile_strength': 'Optimal (Top 10%)' if scores_obj.get('overall_resume_score', 80) >= 80 else 'Good Quality',
        'resume_downloads': 6,
        'resume_health': f"{scores_obj.get('overall_resume_score', 82)}%"
    }

    cand_chart_data = {
        'timeline': {
            'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6'],
            'applications': [1, 2, 1, 3, 2, len(apps)],
            'views': [3, 5, 8, 12, 16, kpis['recruiter_views']]
        },
        'ats_history': {
            'labels': ['Initial Draft', 'v1.1 Action Verbs', 'v1.2 Skills Added', 'Current Active'],
            'scores': [62, 74, 80, kpis['ats_score']]
        },
        'skills': {
            'labels': ['Technical Stack', 'Soft Skills', 'Domain Knowledge', 'Certifications'],
            'values': [scores_obj.get('technical_strength', 80), 85, 78, 90]
        }
    }
        
    return render_template('candidate.html',
                           active_page='candidate',
                           applications_with_timeline=parsed_apps,
                           available_jobs=available_jobs,
                           kpis=kpis,
                           cand_chart_data=json.dumps(cand_chart_data))


@app.route('/admin')
@login_required
def admin_portal():
    if current_user.role == 'candidate':
        return redirect(url_for('candidate_portal'))
        
    apps = Application.query.order_by(Application.applied_at.desc()).all()
    jobs = Job.query.all()
    job_titles = list(set([j.title for j in jobs]))
    
    return render_template('admin.html',
                           active_page='admin',
                           applications=apps,
                           job_titles=job_titles)


@app.route('/jobs', methods=['GET', 'POST'])
@login_required
def manage_jobs():
    if current_user.role == 'candidate':
        return redirect(url_for('candidate_portal'))
        
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        department = request.form.get('department', '').strip()
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()
        preferred_skills = request.form.get('preferred_skills', '').strip()
        required_education = request.form.get('required_education', '').strip()
        responsibilities = request.form.get('responsibilities', '').strip()
        exp_years = request.form.get('experience_years', 0)
        
        # Build weighted skills mapping dynamically
        skills_list = [s.strip() for s in requirements.split(',') if s.strip()]
        weighted_skills = {}
        for skill in skills_list:
            # Random default weight between 2 and 3 for demo JDs
            weighted_skills[skill] = random.choice([2, 3])
            
        if not title or not department or not description or not requirements:
            flash("All core fields are required to post a job.", "danger")
        else:
            try:
                new_job = Job(
                    title=title,
                    department=department,
                    description=description,
                    requirements=requirements,
                    preferred_skills=preferred_skills,
                    required_education=required_education,
                    responsibilities=responsibilities,
                    weighted_skills=json.dumps(weighted_skills),
                    experience_years=int(exp_years),
                    created_by=current_user.id
                )
                db.session.add(new_job)
                db.session.commit()
                
                # Log action
                log = ActivityLog(user_id=current_user.id, action=f"Created job posting: {title}", ip_address=request.remote_addr)
                db.session.add(log)
                db.session.commit()
                
                flash(f"Job posting for {title} created successfully!", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Failed to create job: {e}", "danger")
                
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return render_template('jobs.html', active_page='jobs', jobs=jobs)


@app.route('/jobs/delete/<int:job_id>')
@login_required
def delete_job(job_id):
    if current_user.role == 'candidate':
        return redirect(url_for('candidate_portal'))
        
    job = Job.query.get_or_404(job_id)
    title = job.title
    try:
        db.session.delete(job)
        db.session.commit()
        
        # Log action
        log = ActivityLog(user_id=current_user.id, action=f"Deleted job posting: {title}", ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        
        flash(f"Job posting {title} deleted.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting job: {e}", "danger")
        
    return redirect(url_for('manage_jobs'))


@app.route('/upload-resume', methods=['POST'])
@login_required
def upload_resume():
    if current_user.role == 'admin':
        return jsonify({'success': False, 'error': 'Admins cannot submit resumes.'})
        
    if 'resume' not in request.files or 'job_id' not in request.form:
        return jsonify({'success': False, 'error': 'Missing file or job target.'})
        
    file = request.files['resume']
    job_id_str = request.form['job_id']
    
    if file.filename == '' or not job_id_str:
        return jsonify({'success': False, 'error': 'Invalid arguments.'})
        
    job_id = int(job_id_str)
    job = Job.query.get(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Target job not found.'})
        
    filename = file.filename
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ['pdf', 'docx']:
        return jsonify({'success': False, 'error': 'Only PDF and DOCX formats are supported.'})
        
    try:
        # Save file to uploads folder
        safe_filename = f"user_{current_user.id}_job_{job_id}_{int(os.urandom(4).hex(), 16)}.{ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(file_path)
        
        # Parse resume text
        parsed_resume = parse_resume(file_path, ext)
        
        new_resume = Resume(
            candidate_id=current_user.id,
            filename=filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            parsed_text=parsed_resume['raw_text']
        )
        db.session.add(new_resume)
        db.session.commit()
        
        # Score resume using JD weighted skills
        analysis = score_resume_against_job(
            parsed_resume, 
            job.title, 
            job.requirements, 
            job.description, 
            weighted_skills_json=job.weighted_skills
        )
        
        score_record = ResumeScore(
            resume_id=new_resume.id,
            job_id=job.id,
            ats_match_score=analysis['ats_match_score'],
            match_rating=analysis['match_rating'],
            grammar_score=analysis['grammar_score'],
            formatting_score=analysis['formatting_score'],
            readability_score=analysis['readability_score'],
            professionalism_score=analysis['professionalism_score'],
            project_quality_score=analysis['project_quality_score'],
            overall_rating=analysis['overall_rating'],
            
            # New 12-point breakdown fields
            ats_compatibility=analysis['ats_compatibility'],
            tech_skills=analysis['tech_skills'],
            soft_skills=analysis['soft_skills'],
            communication=analysis['communication'],
            experience_score=analysis['experience_score'],
            education_score=analysis['education_score'],
            projects_score=analysis['projects_score'],
            certifications_score=analysis['certifications_score'],
            overall_intelligence_score=analysis['overall_intelligence_score'],
            insights_summary=analysis['insights_summary'],
            
            # Advice fields
            strengths=analysis['strengths'],
            weaknesses=analysis['weaknesses'],
            suggestions=analysis['suggestions'],
            skills_present=analysis['skills_present'],
            skills_missing=analysis['skills_missing'],
            high_priority_skills=analysis['high_priority_skills'],
            optional_skills=analysis['optional_skills'],
            recommended_skills=analysis['recommended_skills'],
            recommended_courses=analysis['recommended_courses'],
            recommended_certifications=analysis['recommended_certifications'],
            suggested_projects=analysis['suggested_projects'],
            learning_timeline=analysis['learning_timeline'],
            
            # Keywords
            matched_keywords=analysis['matched_keywords'],
            missing_keywords=analysis['missing_keywords'],
            repeated_keywords=analysis['repeated_keywords'],
            power_verbs=analysis['power_verbs']
        )
        db.session.add(score_record)
        
        # Create application and record timeline
        app_record = Application(
            candidate_id=current_user.id,
            job_id=job.id,
            resume_id=new_resume.id,
            status='Applied'
        )
        append_application_timeline(app_record, "Resume Uploaded", "Successfully uploaded PDF/DOCX resume file.")
        append_application_timeline(app_record, "AI Screening Completed", f"AI matched compatibility rating at {analysis['overall_intelligence_score']} score.")
        db.session.add(app_record)
        db.session.commit()
        
        # Log prediction for audit trail
        input_data = {'raw_words_count': len(parsed_resume['raw_text'].split()), 'job_id': job_id}
        output_data = {'score': analysis['overall_intelligence_score'], 'rating': analysis['match_rating']}
        prediction = PredictionLog(candidate_id=current_user.id, job_id=job_id, input_features=json.dumps(input_data), output_scores=json.dumps(output_data))
        db.session.add(prediction)
        
        # Update job rankings
        update_job_rankings(job.id)
        
        # Notifications
        cand_notif = Notification(
            user_id=current_user.id,
            title="Resume Uploaded & Screened",
            message=f"Your resume has been processed for the {job.title} posting. Score: {analysis['overall_intelligence_score']}/100.",
            notification_type="upload"
        )
        db.session.add(cand_notif)
        
        # Alert admins
        recruiters = User.query.filter_by(role='admin').all()
        for rec in recruiters:
            rec_notif = Notification(
                user_id=rec.id,
                title="New Application Received",
                message=f"Candidate {current_user.full_name} applied for {job.title} (ATS Score: {analysis['overall_intelligence_score']}%).",
                notification_type="upload"
            )
            db.session.add(rec_notif)
            
        # Log activity
        log = ActivityLog(user_id=current_user.id, action=f"Applied for job: {job.title}", ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True, 'redirect': url_for('candidate_portal')})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f"Processing failed: {e}"})


@app.route('/preview/<int:app_id>')
@login_required
def preview_candidate(app_id):
    if current_user.role == 'candidate':
        return redirect(url_for('candidate_portal'))
        
    app_record = Application.query.get_or_404(app_id)
    resume = app_record.resume
    candidate = app_record.candidate
    job = app_record.job
    
    score = ResumeScore.query.filter_by(resume_id=resume.id, job_id=job.id).first()
    if not score:
        flash("AI screening scores not generated for this resume yet.", "warning")
        return redirect(url_for('admin_portal'))
        
    # Query Candidate Ranking Medal & Tier
    ranking_record = CandidateRanking.query.filter_by(job_id=job.id, candidate_id=candidate.id).first()
    
    # Process timeline milestones
    timeline_list = []
    if app_record.timeline:
        try:
            timeline_list = json.loads(app_record.timeline)
        except Exception:
            timeline_list = []
            
    return render_template('resume_preview.html',
                           app_record=app_record,
                           resume=resume,
                           candidate=candidate,
                           job=job,
                           score=score,
                           ranking=ranking_record,
                           timeline=timeline_list,
                           strengths=json.loads(score.strengths),
                           weaknesses=json.loads(score.weaknesses),
                           suggestions=json.loads(score.suggestions),
                           present_skills=json.loads(score.skills_present),
                           missing_skills=json.loads(score.skills_missing),
                           high_priority_skills=json.loads(score.high_priority_skills) if score.high_priority_skills else [],
                           optional_skills=json.loads(score.optional_skills) if score.optional_skills else [],
                           learning_suggestions=json.loads(score.recommended_courses) if score.recommended_courses else [],
                           recommended_certifications=json.loads(score.recommended_certifications) if score.recommended_certifications else [],
                           suggested_projects=json.loads(score.suggested_projects) if score.suggested_projects else [],
                           learning_timeline=json.loads(score.learning_timeline) if score.learning_timeline else {},
                           matched_keywords=json.loads(score.matched_keywords),
                           repeated_keywords=json.loads(score.repeated_keywords),
                           power_verbs=json.loads(score.power_verbs))


@app.route('/download-resume/<int:resume_id>')
@login_required
def download_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if current_user.role == 'candidate' and resume.candidate_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('candidate_portal'))
    return send_file(resume.file_path, as_attachment=True, download_name=resume.filename)


@app.route('/download-report/<int:score_id>')
@login_required
def download_report_pdf(score_id):
    score = ResumeScore.query.get_or_404(score_id)
    resume = score.resume
    job = score.job
    user = User.query.get(resume.candidate_id)
    
    if current_user.role == 'candidate' and user.id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('candidate_portal'))
        
    rank_record = CandidateRanking.query.filter_by(job_id=job.id, candidate_id=user.id).first()
    rank_num = rank_record.rank_number if rank_record else None
    
    try:
        pdf_buffer = generate_resume_report_pdf(user, job, resume, score, rank_num)
        return send_file(
            pdf_buffer, 
            mimetype='application/pdf', 
            as_attachment=True, 
            download_name=f"{user.full_name.replace(' ', '_')}_Analysis_Report.pdf"
        )
    except Exception as e:
        flash(f"Could not generate PDF report: {e}", "danger")
        if current_user.role == 'admin':
            return redirect(url_for('admin_portal'))
        return redirect(url_for('candidate_portal'))


@app.route('/update-status/<int:app_id>', methods=['POST'])
@login_required
def update_candidate_status(app_id):
    if current_user.role == 'candidate':
        return redirect(url_for('candidate_portal'))
        
    app_record = Application.query.get_or_404(app_id)
    new_status = request.form.get('status')
    
    if new_status:
        old_status = app_record.status
        app_record.status = new_status
        
        # Append timeline stage
        append_application_timeline(app_record, new_status, f"HR Admin advanced candidate from {old_status}.")
        db.session.commit()
        
        # Add notifications for candidate
        notif = Notification(
            user_id=app_record.candidate_id,
            title="Application Status Updated",
            message=f"Your application status for {app_record.job.title} was updated to {new_status}.",
            notification_type="status_change"
        )
        db.session.add(notif)
        db.session.commit()
        
        # Log action
        log = ActivityLog(user_id=current_user.id, action=f"Updated candidate {app_record.candidate.full_name} status for job {app_record.job.title} to {new_status}", ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        
        flash(f"Updated status for {app_record.candidate.full_name} to {new_status}.", "success")
        
    return redirect(url_for('admin_portal'))


@app.route('/delete-application/<int:app_id>')
@login_required
def delete_application(app_id):
    if current_user.role == 'candidate':
        return redirect(url_for('candidate_portal'))
        
    app_record = Application.query.get_or_404(app_id)
    cand_name = app_record.candidate.full_name
    job_title = app_record.job.title
    job_id = app_record.job_id
    
    try:
        db.session.delete(app_record)
        db.session.commit()
        
        # Re-compute rankings
        update_job_rankings(job_id)
        
        # Log action
        log = ActivityLog(user_id=current_user.id, action=f"Deleted application of {cand_name} for {job_title}", ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        
        flash(f"Application for {cand_name} deleted.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete candidate: {e}", "danger")
        
    return redirect(url_for('admin_portal'))


# --- CALENDAR SCHEDULER ---

@app.route('/interviews', methods=['GET', 'POST'])
@login_required
def interviews_calendar():
    if current_user.role == 'candidate':
        # Candidate views their scheduled interviews
        upcoming = Interview.query.filter_by(candidate_id=current_user.id).order_by(Interview.date_time.asc()).all()
        return render_template('calendar.html', active_page='calendar', interviews=upcoming)
        
    # Admin view: List all interviews and schedule new ones
    if request.method == 'POST':
        app_id_str = request.form.get('application_id')
        interviewer = request.form.get('interviewer', '').strip()
        datetime_str = request.form.get('date_time')
        link = request.form.get('meeting_link', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not app_id_str or not interviewer or not datetime_str:
            flash("Missing core interview details.", "danger")
        else:
            try:
                app_record = Application.query.get(int(app_id_str))
                dt = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')
                
                new_interview = Interview(
                    application_id=app_record.id,
                    candidate_id=app_record.candidate_id,
                    job_id=app_record.job_id,
                    interviewer_name=interviewer,
                    date_time=dt,
                    meeting_link=link,
                    notes=notes
                )
                db.session.add(new_interview)
                
                # Advance candidate stage and timeline
                app_record.status = "Interview Scheduled"
                append_application_timeline(app_record, "Interview Scheduled", f"Scheduled round with {interviewer} for {dt.strftime('%Y-%m-%d %H:%M')}.")
                
                # Alert candidate
                notif = Notification(
                    user_id=app_record.candidate_id,
                    title="Interview Scheduled!",
                    message=f"You have an upcoming interview scheduled for {dt.strftime('%b %d at %H:%M')} with {interviewer}.",
                    notification_type="status_change"
                )
                db.session.add(notif)
                db.session.commit()
                
                # Log action
                log = ActivityLog(user_id=current_user.id, action=f"Scheduled interview for {app_record.candidate.full_name} on {dt.strftime('%Y-%m-%d')}", ip_address=request.remote_addr)
                db.session.add(log)
                db.session.commit()
                
                flash(f"Interview scheduled for {app_record.candidate.full_name}!", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Scheduling failed: {e}", "danger")
                
    interviews = Interview.query.order_by(Interview.date_time.asc()).all()
    applications = Application.query.filter(Application.status.in_(['Applied', 'Screening', 'Shortlisted'])).all()
    
    # Structure interviews data for calendar grid plotting
    events = []
    for iv in interviews:
        events.append({
            'id': iv.id,
            'title': f"{iv.candidate.full_name} ({iv.job.title})",
            'date': iv.date_time.strftime('%Y-%m-%d'),
            'time': iv.date_time.strftime('%H:%M'),
            'interviewer': iv.interviewer_name,
            'status': iv.status
        })
        
    return render_template('calendar.html', 
                           active_page='calendar', 
                           interviews=interviews, 
                           applications=applications,
                           events_json=json.dumps(events))


@app.route('/interviews/cancel/<int:interview_id>')
@login_required
def cancel_interview(interview_id):
    if current_user.role == 'candidate':
        return redirect(url_for('candidate_portal'))
        
    iv = Interview.query.get_or_404(interview_id)
    iv.status = 'Cancelled'
    
    app_record = iv.application
    app_record.status = 'Screening'
    append_application_timeline(app_record, "Screening", "Interview cancelled; reset back to screening.")
    
    db.session.commit()
    flash("Interview cancelled.", "info")
    return redirect(url_for('interviews_calendar'))


# --- SYSTEM SETTINGS & AUDIT LOGS ---

@app.route('/admin/settings')
@login_required
def admin_settings():
    if current_user.role == 'candidate':
        return redirect(url_for('candidate_portal'))
        
    predictions = PredictionLog.query.order_by(PredictionLog.created_at.desc()).limit(20).all()
    activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(20).all()
    models = ModelInfo.query.order_by(ModelInfo.trained_at.desc()).all()
    
    return render_template('admin_settings.html',
                           active_page='settings',
                           predictions=predictions,
                           activities=activities,
                           models=models)


@app.route('/admin/settings/backup')
@login_required
def database_backup_simulation():
    if current_user.role == 'candidate':
        return redirect(url_for('candidate_portal'))
        
    # Simulate DB backup (write copy of DB to reports folder as a mock)
    try:
        db_path = os.path.join(BASE_DIR, 'database', 'recruitment.db')
        backup_path = os.path.join(BASE_DIR, 'reports', 'backup_recruitment.db')
        if os.path.exists(db_path):
            import shutil
            shutil.copy2(db_path, backup_path)
            flash("Database backup completed successfully! Backup file saved in /reports.", "success")
        else:
            flash("Source database file not found.", "danger")
    except Exception as e:
        flash(f"Backup failed: {e}", "danger")
        
    return redirect(url_for('admin_settings'))


@app.route('/admin/settings/retrain', methods=['POST'])
@login_required
def simulate_model_retraining():
    if current_user.role == 'candidate':
        return redirect(url_for('candidate_portal'))
        
    # Add a new version of model info to table
    try:
        # deactivate previous models
        ModelInfo.query.update({ModelInfo.active: False})
        
        # generate new random version details
        new_version = f"ATS-BERT-v{random.randint(2, 5)}.{random.randint(1, 9)}"
        new_acc = round(85.0 + random.random() * 10, 2)
        
        new_model = ModelInfo(version=new_version, accuracy=new_acc, active=True)
        db.session.add(new_model)
        db.session.commit()
        
        # Log action
        log = ActivityLog(user_id=current_user.id, action=f"Triggered model retraining: {new_version}", ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        
        flash(f"Model retraining complete. Active Version: {new_version} (Accuracy: {new_acc}%).", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Retraining simulation failed: {e}", "danger")
        
    return redirect(url_for('admin_settings'))


# --- SAAS DASHBOARD FEATURE ROUTES ---

@app.route('/ai-chat')
@login_required
def ai_chat():
    return render_template('ai_chat.html', active_page='ai_chat')


# --- CANDIDATE DEDICATED AI RESUME BUILDER ROUTES ---

@app.route('/candidate/resume-builder')
@login_required
def candidate_resume_builder():
    if current_user.role == 'admin':
        return redirect(url_for('dashboard'))
        
    draft = CandidateResumeDraft.query.filter_by(candidate_id=current_user.id, is_active=True).first()
    if not draft:
        # Create initial default draft for candidate
        init_data = get_default_resume_data(user_name=current_user.full_name, user_email=current_user.email)
        init_scores = calculate_candidate_resume_scores(init_data)
        
        draft = CandidateResumeDraft(
            candidate_id=current_user.id,
            title=f"{current_user.full_name}'s Professional Resume",
            template_style="professional",
            data_json=json.dumps(init_data),
            scores_json=json.dumps(init_scores)
        )
        db.session.add(draft)
        db.session.commit()
        
        # Create Initial Version Checkpoint v1
        ver1 = CandidateResumeVersion(
            draft_id=draft.id,
            candidate_id=current_user.id,
            version_number=1,
            version_label="Initial Draft v1",
            template_style="professional",
            data_json=draft.data_json,
            scores_json=draft.scores_json
        )
        db.session.add(ver1)
        db.session.commit()

    data_obj = json.loads(draft.data_json)
    scores_obj = json.loads(draft.scores_json)
    suggestions_list = generate_candidate_ai_suggestions(data_obj)
    versions_list = CandidateResumeVersion.query.filter_by(draft_id=draft.id).order_by(CandidateResumeVersion.version_number.desc()).all()

    return render_template(
        'candidate_resume_builder.html',
        active_page='candidate_resume_builder',
        draft=draft,
        data=data_obj,
        scores=scores_obj,
        suggestions=suggestions_list,
        versions=versions_list
    )


@app.route('/api/candidate-ai/chat', methods=['POST'])
@login_required
def api_candidate_ai_chat():
    if current_user.role == 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized access.'}), 403
        
    req = request.get_json() or {}
    message = req.get('message', '').strip()
    data = req.get('data', {})
    draft_id = req.get('draft_id')
    
    draft = None
    if draft_id:
        draft = CandidateResumeDraft.query.get(draft_id)
    if not draft:
        draft = CandidateResumeDraft.query.filter_by(candidate_id=current_user.id, is_active=True).first()
        
    if not data and draft:
        data = json.loads(draft.data_json)
        
    res = process_candidate_chat(message, data)
    
    if draft:
        draft.data_json = json.dumps(res['updated_data'])
        draft.scores_json = json.dumps(res['scores'])
        draft.updated_at = datetime.utcnow()
        db.session.commit()
        
    return jsonify({
        'success': True,
        'reply': res['reply'],
        'data': res['updated_data'],
        'scores': res['scores'],
        'suggestions': res['suggestions'],
        'quick_actions': res['quick_actions']
    })


@app.route('/api/candidate-ai/save-draft', methods=['POST'])
@login_required
def api_candidate_ai_save_draft():
    if current_user.role == 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized access.'}), 403
        
    req = request.get_json() or {}
    draft_id = req.get('draft_id')
    data = req.get('data', {})
    template_style = req.get('template_style', 'professional')
    label = req.get('label', '').strip()
    
    draft = CandidateResumeDraft.query.get(draft_id) if draft_id else CandidateResumeDraft.query.filter_by(candidate_id=current_user.id, is_active=True).first()
    if not draft:
        return jsonify({'success': False, 'error': 'Draft not found.'})
        
    scores = calculate_candidate_resume_scores(data)
    draft.data_json = json.dumps(data)
    draft.scores_json = json.dumps(scores)
    draft.template_style = template_style
    draft.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Save Version Snapshot
    last_version = CandidateResumeVersion.query.filter_by(draft_id=draft.id).order_by(CandidateResumeVersion.version_number.desc()).first()
    next_v = (last_version.version_number + 1) if last_version else 1
    
    version_label = label if label else f"Snapshot v{next_v} ({template_style.title()})"
    new_version = CandidateResumeVersion(
        draft_id=draft.id,
        candidate_id=current_user.id,
        version_number=next_v,
        version_label=version_label,
        template_style=template_style,
        data_json=draft.data_json,
        scores_json=draft.scores_json
    )
    db.session.add(new_version)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Resume draft saved as {version_label}!',
        'version_number': next_v,
        'scores': scores
    })


@app.route('/api/candidate-ai/update-resume', methods=['POST'])
@login_required
def api_candidate_ai_update_resume():
    if current_user.role == 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized access.'}), 403
        
    req = request.get_json() or {}
    data = req.get('data', {})
    
    draft = CandidateResumeDraft.query.filter_by(candidate_id=current_user.id, is_active=True).first()
    if not data and draft:
        data = json.loads(draft.data_json)
        
    text_content = f"""
FULL NAME: {data.get('full_name')}
TITLE: {data.get('professional_title')}
EMAIL: {data.get('email')} | PHONE: {data.get('phone')}
LOCATION: {data.get('address')}
SUMMARY: {data.get('career_objective')}
EDUCATION: {json.dumps(data.get('education', []))}
EXPERIENCE: {json.dumps(data.get('work_experience', []))}
PROJECTS: {json.dumps(data.get('projects', []))}
SKILLS: {', '.join(data.get('technical_skills', []))}
    """
    
    # Save text as an active candidate resume file
    safe_filename = f"ai_builder_resume_u{current_user.id}.txt"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text_content)
        
    existing_resume = Resume.query.filter_by(candidate_id=current_user.id, filename="AI_Builder_Resume.docx").first()
    if not existing_resume:
        existing_resume = Resume.query.filter_by(candidate_id=current_user.id).first()
        
    if existing_resume:
        existing_resume.parsed_text = text_content
        existing_resume.file_path = file_path
        existing_resume.file_size = len(text_content.encode('utf-8'))
    else:
        existing_resume = Resume(
            candidate_id=current_user.id,
            filename="AI_Builder_Resume.docx",
            file_path=file_path,
            file_size=len(text_content.encode('utf-8')),
            parsed_text=text_content
        )
        db.session.add(existing_resume)
        
    db.session.commit()
    
    # Log Activity
    log = ActivityLog(user_id=current_user.id, action="Updated primary resume via AI Resume Builder", ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Primary resume updated successfully! Ready for job applications.'
    })


@app.route('/api/candidate-ai/export-pdf', methods=['GET', 'POST'])
@login_required
def api_candidate_ai_export_pdf():
    draft = CandidateResumeDraft.query.filter_by(candidate_id=current_user.id, is_active=True).first()
    data = json.loads(draft.data_json) if draft else get_default_resume_data(current_user.full_name, current_user.email)
    template_style = request.args.get('template', draft.template_style if draft else 'professional')
    
    pdf_buffer = generate_candidate_pdf(data, template_style=template_style)
    safe_name = data.get('full_name', 'Resume').replace(' ', '_')
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{safe_name}_Resume_{template_style.title()}.pdf"
    )


@app.route('/api/candidate-ai/export-docx', methods=['GET', 'POST'])
@login_required
def api_candidate_ai_export_docx():
    draft = CandidateResumeDraft.query.filter_by(candidate_id=current_user.id, is_active=True).first()
    data = json.loads(draft.data_json) if draft else get_default_resume_data(current_user.full_name, current_user.email)
    template_style = request.args.get('template', draft.template_style if draft else 'professional')
    
    docx_buffer = generate_candidate_docx(data, template_style=template_style)
    safe_name = data.get('full_name', 'Resume').replace(' ', '_')
    return send_file(
        docx_buffer,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name=f"{safe_name}_Resume_{template_style.title()}.docx"
    )


@app.route('/api/candidate-ai/version-history/<int:draft_id>')
@login_required
def api_candidate_ai_version_history(draft_id):
    draft = CandidateResumeDraft.query.get_or_404(draft_id)
    if draft.candidate_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    versions = CandidateResumeVersion.query.filter_by(draft_id=draft.id).order_by(CandidateResumeVersion.version_number.desc()).all()
    res = []
    for v in versions:
        res.append({
            'id': v.id,
            'version_number': v.version_number,
            'version_label': v.version_label,
            'template_style': v.template_style,
            'scores': json.loads(v.scores_json),
            'created_at': v.created_at.strftime('%Y-%m-%d %H:%M')
        })
    return jsonify({'success': True, 'versions': res})


@app.route('/api/candidate-ai/restore-version/<int:version_id>', methods=['POST'])
@login_required
def api_candidate_ai_restore_version(version_id):
    ver = CandidateResumeVersion.query.get_or_404(version_id)
    if ver.candidate_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    draft = CandidateResumeDraft.query.get(ver.draft_id)
    if draft:
        draft.data_json = ver.data_json
        draft.scores_json = ver.scores_json
        draft.template_style = ver.template_style
        draft.updated_at = datetime.utcnow()
        db.session.commit()
        
    return jsonify({
        'success': True,
        'message': f'Restored to Version {ver.version_number}: {ver.version_label}!',
        'data': json.loads(ver.data_json),
        'scores': json.loads(ver.scores_json),
        'template_style': ver.template_style
    })



@app.route('/budget-simulator')
@login_required
def budget_simulator():
    return render_template('budget_simulator.html', active_page='budget_simulator')


@app.route('/compare-packages')
@login_required
def compare_packages():
    return render_template('compare_packages.html', active_page='compare_packages')


@app.route('/quotations')
@login_required
def quotations():
    return render_template('quotations.html', active_page='quotations')


@app.route('/proposals')
@login_required
def proposals():
    return render_template('proposals.html', active_page='proposals')


@app.route('/chat-history')
@login_required
def chat_history():
    return render_template('chat_history.html', active_page='chat_history')


@app.route('/profile')
@login_required
def customer_profile():
    return render_template('customer_profile.html', active_page='customer_profile')


@app.route('/help-support')
@login_required
def help_support():
    return render_template('help_support.html', active_page='help_support')


# --- INTERFACE UTILITIES ---

@app.route('/save-theme', methods=['POST'])
@login_required
def save_theme():
    req = request.get_json()
    theme = req.get('theme')
    if theme in ['theme-executive-blue', 'theme-emerald-professional', 'theme-royal-indigo', 'theme-slate-executive', 'theme-graphite-premium']:
        current_user.theme_preference = theme
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid theme selection.'})


@app.route('/toggle-dark-mode', methods=['POST'])
@login_required
def toggle_dark_mode():
    current_user.dark_mode = not current_user.dark_mode
    # Adjust theme preferences to match light/dark modes
    if current_user.dark_mode:
        if current_user.theme_preference not in ['theme-slate-executive', 'theme-graphite-premium']:
            current_user.theme_preference = 'theme-slate-executive'
    else:
        if current_user.theme_preference in ['theme-slate-executive', 'theme-graphite-premium']:
            current_user.theme_preference = 'theme-executive-blue'
            
    db.session.commit()
    return jsonify({'success': True, 'theme': current_user.theme_preference, 'dark_mode': current_user.dark_mode})


@app.route('/clear-notifications')
@login_required
def clear_notifications():
    notifications_list = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for notif in notifications_list:
        notif.is_read = True
    db.session.commit()
    
    if current_user.role == 'admin':
        return redirect(url_for('dashboard'))
    return redirect(url_for('candidate_portal'))


# Startup: Create tables and default Recruiter Admin
with app.app_context():
    try:
        db.create_all()
        # Verify query runs successfully to check schema sanity
        admin_user = User.query.filter_by(role='admin').first()
    except Exception as e:
        print(f"Database schema mismatch detected: {e}. Recreating tables...")
        db.session.remove()
        try:
            db.engine.dispose()
        except Exception:
            pass
        db_path = os.path.join(BASE_DIR, 'database', 'recruitment.db')
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception as remove_error:
                print(f"Could not remove database file: {remove_error}")
        db.create_all()

    # Create default recruiter admin account
    admin_user = User.query.filter_by(role='admin').first()
    if not admin_user:
        admin = User(
            username="admin",
            email="admin@company.com",
            full_name="Enterprise Admin",
            role="admin",
            theme_preference="theme-executive-blue",
            dark_mode=False
        )
        admin.set_password("AdminPass123!")
        db.session.add(admin)
        db.session.commit()
        
    # Create default active models record if none exists
    model_record = ModelInfo.query.first()
    if not model_record:
        init_model = ModelInfo(version="ATS-RoBERTa-v1.0", accuracy=89.4, active=True)
        db.session.add(init_model)
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True)
