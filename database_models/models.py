from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import bcrypt

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='candidate') # 'candidate' or 'admin'
    theme_preference = db.Column(db.String(50), nullable=False, default='theme-executive-blue')
    dark_mode = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    resumes = db.relationship('Resume', backref='candidate', lazy=True, cascade='all, delete-orphan')
    applications = db.relationship('Application', backref='candidate', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)
    rankings = db.relationship('CandidateRanking', backref='candidate', lazy=True, cascade='all, delete-orphan')
    interviews = db.relationship('Interview', backref='candidate', lazy=True, cascade='all, delete-orphan')
    resume_drafts = db.relationship('CandidateResumeDraft', backref='candidate', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Job(db.Model):
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)  # Comma-separated or JSON list of skills
    preferred_skills = db.Column(db.Text, nullable=True) # JSON list or comma-separated
    required_education = db.Column(db.String(150), nullable=True)
    responsibilities = db.Column(db.Text, nullable=True)
    weighted_skills = db.Column(db.Text, nullable=True) # JSON dict maps skills to weights (1-3)
    experience_years = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    applications = db.relationship('Application', backref='job', lazy=True, cascade='all, delete-orphan')
    scores = db.relationship('ResumeScore', backref='job', lazy=True, cascade='all, delete-orphan')
    rankings = db.relationship('CandidateRanking', backref='job', lazy=True, cascade='all, delete-orphan')
    interviews = db.relationship('Interview', backref='job', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Job {self.title}>'


class Resume(db.Model):
    __tablename__ = 'resumes'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.Integer, nullable=False) # in bytes
    parsed_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='resume', lazy=True, cascade='all, delete-orphan')
    scores = db.relationship('ResumeScore', backref='resume', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Resume {self.filename}>'


class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Applied') 
    # 'Applied', 'Screening', 'Shortlisted', 'Interview Scheduled', 'Technical Round', 'HR Round', 'Selected', 'Rejected'
    timeline = db.Column(db.Text, nullable=True) # JSON list of stage milestones
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    interviews = db.relationship('Interview', backref='application', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Application Candidate:{self.candidate_id} Job:{self.job_id} Status:{self.status}>'


class ResumeScore(db.Model):
    __tablename__ = 'resume_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    
    # Matching Scores
    ats_match_score = db.Column(db.Float, nullable=False) # Percentage
    match_rating = db.Column(db.String(20), nullable=False) # 'Excellent Match', 'Good Match', etc.
    
    # Twelve-point score breakdowns (0-100)
    ats_compatibility = db.Column(db.Float, nullable=False, default=0.0)
    tech_skills = db.Column(db.Float, nullable=False, default=0.0)
    soft_skills = db.Column(db.Float, nullable=False, default=0.0)
    communication = db.Column(db.Float, nullable=False, default=0.0)
    experience_score = db.Column(db.Float, nullable=False, default=0.0)
    education_score = db.Column(db.Float, nullable=False, default=0.0)
    projects_score = db.Column(db.Float, nullable=False, default=0.0)
    certifications_score = db.Column(db.Float, nullable=False, default=0.0)
    formatting_score = db.Column(db.Float, nullable=False, default=0.0)
    grammar_score = db.Column(db.Float, nullable=False, default=0.0)
    professionalism_score = db.Column(db.Float, nullable=False, default=0.0)
    readability_score = db.Column(db.Float, nullable=False, default=0.0)
    
    # Combined Overall Intelligence metrics
    overall_rating = db.Column(db.Float, nullable=False, default=0.0) # Base Quality Rating
    overall_intelligence_score = db.Column(db.Float, nullable=False, default=0.0) # AI Intelligence Rating
    insights_summary = db.Column(db.Text, nullable=True) # AI executive summary
    
    # Feedback fields stored as JSON strings
    strengths = db.Column(db.Text, nullable=False) # JSON list
    weaknesses = db.Column(db.Text, nullable=False) # JSON list
    suggestions = db.Column(db.Text, nullable=False) # JSON list
    
    # Skill Gap details stored as JSON strings
    skills_present = db.Column(db.Text, nullable=False) # JSON list
    skills_missing = db.Column(db.Text, nullable=False) # JSON list
    high_priority_skills = db.Column(db.Text, nullable=True) # JSON list
    optional_skills = db.Column(db.Text, nullable=True) # JSON list
    recommended_skills = db.Column(db.Text, nullable=False) # JSON list (general)
    recommended_courses = db.Column(db.Text, nullable=True) # JSON list of dicts
    recommended_certifications = db.Column(db.Text, nullable=True) # JSON list
    suggested_projects = db.Column(db.Text, nullable=True) # JSON list
    learning_timeline = db.Column(db.Text, nullable=True) # JSON dict/list
    
    # Keyword analysis details stored as JSON strings
    matched_keywords = db.Column(db.Text, nullable=False) # JSON list
    missing_keywords = db.Column(db.Text, nullable=False) # JSON list
    repeated_keywords = db.Column(db.Text, nullable=False) # JSON list
    power_verbs = db.Column(db.Text, nullable=False) # JSON list
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ResumeScore Resume:{self.resume_id} Job:{self.job_id} ATS:{self.ats_match_score}%>'


class CandidateRanking(db.Model):
    __tablename__ = 'candidate_rankings'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rank_number = db.Column(db.Integer, nullable=False)
    overall_score = db.Column(db.Float, nullable=False)
    tier = db.Column(db.String(50), nullable=True) # 'Gold', 'Silver', 'Bronze'
    overall_strength = db.Column(db.String(50), nullable=True) # 'Top Candidate', 'Highly Recommended', 'Recommended', 'Needs Improvement'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CandidateRanking Job:{self.job_id} Candidate:{self.candidate_id} Rank:{self.rank_number} Tier:{self.tier}>'


class Interview(db.Model):
    __tablename__ = 'interviews'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    interviewer_name = db.Column(db.String(100), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    meeting_link = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Scheduled') # 'Scheduled', 'Completed', 'Cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Interview Candidate:{self.candidate_id} Date:{self.date_time} Status:{self.status}>'


class PredictionLog(db.Model):
    __tablename__ = 'prediction_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, nullable=False)
    job_id = db.Column(db.Integer, nullable=False)
    input_features = db.Column(db.Text, nullable=False) # JSON dump of parameters
    output_scores = db.Column(db.Text, nullable=False) # JSON dump of calculated outputs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PredictionLog Candidate:{self.candidate_id} Job:{self.job_id}>'


class ModelInfo(db.Model):
    __tablename__ = 'model_info'
    
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(50), nullable=False)
    accuracy = db.Column(db.Float, nullable=False)
    trained_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<ModelInfo Version:{self.version} Accuracy:{self.accuracy} Active:{self.active}>'


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False) # 'status_change', 'upload', 'announcement', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification User:{self.user_id} Title:{self.title}>'


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # None for anonymous/system events
    action = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ActivityLog User:{self.user_id} Action:{self.action}>'


class CandidateResumeDraft(db.Model):
    __tablename__ = 'candidate_resume_drafts'

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False, default="My Professional Resume")
    template_style = db.Column(db.String(50), nullable=False, default="professional")
    data_json = db.Column(db.Text, nullable=False) # Full structured json
    scores_json = db.Column(db.Text, nullable=False) # JSON breakdown of live scores
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    versions = db.relationship('CandidateResumeVersion', backref='draft', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<CandidateResumeDraft User:{self.candidate_id} Title:{self.title}>'


class CandidateResumeVersion(db.Model):
    __tablename__ = 'candidate_resume_versions'

    id = db.Column(db.Integer, primary_key=True)
    draft_id = db.Column(db.Integer, db.ForeignKey('candidate_resume_drafts.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False, default=1)
    version_label = db.Column(db.String(100), nullable=False, default="Version Snapshot")
    template_style = db.Column(db.String(50), nullable=False, default="professional")
    data_json = db.Column(db.Text, nullable=False)
    scores_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CandidateResumeVersion Draft:{self.draft_id} v{self.version_number}>'

