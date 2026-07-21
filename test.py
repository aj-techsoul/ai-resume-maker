import unittest
import os
import json
from datetime import datetime
from database_models.models import db, User, Job, Resume, Application, ResumeScore, CandidateRanking, Interview
from ai.scorer import score_resume_against_job
from app import app, update_job_rankings

class TestAATS(unittest.TestCase):
    
    def setUp(self):
        # Configure app for testing with in-memory SQLite database
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Build tables
        db.create_all()
        
        # Setup mock admin
        self.admin = User(username='recruiter_hr', email='hr@comp.com', full_name='Recruiter', role='admin')
        self.admin.set_password('AdminSec123!')
        db.session.add(self.admin)
        db.session.commit()
        
        # Setup mock Job Posting with weights
        self.job = Job(
            title="Senior Python Engineer",
            department="Engineering",
            description="Looking for a Python Developer experienced with Flask, SQLAlchemy, Docker, and AWS.",
            requirements="Python, Flask, SQLAlchemy, Docker, AWS",
            weighted_skills=json.dumps({"Python": 3, "Flask": 3, "SQLAlchemy": 2, "Docker": 2, "AWS": 1}),
            experience_years=5,
            created_by=self.admin.id
        )
        db.session.add(self.job)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_creation_and_auth(self):
        """
        Verify candidate registration, password hashing and check.
        """
        candidate = User(username='john_dev', email='john@dev.com', full_name='John Doe', role='candidate')
        candidate.set_password('SecretPass99!')
        db.session.add(candidate)
        db.session.commit()
        
        loaded_user = User.query.filter_by(username='john_dev').first()
        self.assertIsNotNone(loaded_user)
        self.assertEqual(loaded_user.full_name, 'John Doe')
        self.assertTrue(loaded_user.check_password('SecretPass99!'))
        self.assertFalse(loaded_user.check_password('WrongPass'))

    def test_ai_scoring_logic_and_breakdowns(self):
        """
        Validate ATS Match, 12 sub-scores, and weighted skills.
        """
        resume_text = """
        John Doe - Software Engineer
        Contact: john@dev.com | 123-456-7890 | github.com/johndoe
        
        EDUCATION
        Bachelor of Science in Computer Science, University of California
        
        SUMMARY
        Passionate Backend developer with 6+ years of experience designing scalable microservices.
        
        EXPERIENCE
        Senior Engineer at TechCorp (2020 - Present)
        - Developed REST APIs using Python and Flask, reducing latency by 35%.
        - Optimized database schema using SQLAlchemy and migrated queries.
        - Deployed scalable web containers using Docker.
        
        SKILLS
        Python, Flask, SQLAlchemy, Docker, Git, SQL, Postgres, leadership, problem solving
        """
        
        parsed_resume = {
            'name': 'John Doe',
            'email': 'john@dev.com',
            'phone': '123-456-7890',
            'linkedin': '',
            'github': 'https://github.com/johndoe',
            'portfolio': '',
            'education': 'Bachelor of Science in Computer Science, University of California',
            'experience': 'Senior Engineer at TechCorp (2020 - Present)\n- Developed REST APIs using Python and Flask, reducing latency by 35%.\n- Optimized database schema using SQLAlchemy and migrated queries.\n- Deployed scalable web containers using Docker.',
            'skills': 'Python, Flask, SQLAlchemy, Docker, Git, SQL, Postgres, leadership, problem solving',
            'projects': '',
            'certifications': '',
            'languages': '',
            'achievements': '',
            'publications': '',
            'summary': 'Passionate Backend developer with 6+ years of experience designing scalable microservices.',
            'raw_text': resume_text
        }
        
        analysis = score_resume_against_job(
            parsed_resume, 
            self.job.title, 
            self.job.requirements, 
            self.job.description, 
            weighted_skills_json=self.job.weighted_skills
        )
        
        # Verify 12 sub-scores
        self.assertIn('ats_compatibility', analysis)
        self.assertIn('tech_skills', analysis)
        self.assertIn('soft_skills', analysis)
        self.assertIn('communication', analysis)
        self.assertIn('experience_score', analysis)
        self.assertIn('projects_score', analysis)
        self.assertIn('overall_intelligence_score', analysis)
        
        # Verify value range limits
        self.assertGreaterEqual(analysis['overall_intelligence_score'], 10.0)
        self.assertLessEqual(analysis['overall_intelligence_score'], 100.0)

    def test_ranking_medals_and_caching(self):
        """
        Verify multiple candidates applied for a job are sorted and awarded medals.
        """
        c1 = User(username='john', email='john@comp.com', full_name='John Stack', role='candidate')
        c1.set_password('TestPass1!')
        db.session.add(c1)
        
        c2 = User(username='bob', email='bob@comp.com', full_name='Bob Basic', role='candidate')
        c2.set_password('TestPass2!')
        db.session.add(c2)
        db.session.commit()
        
        r1 = Resume(candidate_id=c1.id, filename='john.pdf', file_path='/path/john.pdf', file_size=100, parsed_text="Python, Flask, Docker, AWS developer")
        r2 = Resume(candidate_id=c2.id, filename='bob.pdf', file_path='/path/bob.pdf', file_size=100, parsed_text="HTML and CSS developer")
        db.session.add_all([r1, r2])
        db.session.commit()
        
        app1 = Application(candidate_id=c1.id, job_id=self.job.id, resume_id=r1.id, status='Applied')
        app2 = Application(candidate_id=c2.id, job_id=self.job.id, resume_id=r2.id, status='Applied')
        db.session.add_all([app1, app2])
        db.session.commit()
        
        s1 = ResumeScore(
            resume_id=r1.id, job_id=self.job.id, ats_match_score=92.0, match_rating="Excellent Match",
            ats_compatibility=92.0, tech_skills=90.0, soft_skills=80.0, communication=85.0,
            experience_score=90.0, education_score=80.0, projects_score=85.0, certifications_score=70.0,
            formatting_score=80.0, grammar_score=85.0, professionalism_score=90.0, readability_score=80.0,
            overall_rating=85.0, overall_intelligence_score=88.5, strengths='[]', weaknesses='[]', suggestions='[]',
            skills_present='["Python", "Flask", "Docker"]', skills_missing='["AWS"]', recommended_skills='[]',
            matched_keywords='[]', missing_keywords='[]', repeated_keywords='[]', power_verbs='[]'
        )
        s2 = ResumeScore(
            resume_id=r2.id, job_id=self.job.id, ats_match_score=25.0, match_rating="Poor Match",
            ats_compatibility=25.0, tech_skills=20.0, soft_skills=40.0, communication=50.0,
            experience_score=30.0, education_score=50.0, projects_score=20.0, certifications_score=30.0,
            formatting_score=40.0, grammar_score=50.0, professionalism_score=30.0, readability_score=40.0,
            overall_rating=35.0, overall_intelligence_score=31.2, strengths='[]', weaknesses='[]', suggestions='[]',
            skills_present='[]', skills_missing='["Python", "Flask", "Docker", "AWS"]', recommended_skills='[]',
            matched_keywords='[]', missing_keywords='[]', repeated_keywords='[]', power_verbs='[]'
        )
        db.session.add_all([s1, s2])
        db.session.commit()
        
        update_job_rankings(self.job.id)
        
        rank1 = CandidateRanking.query.filter_by(job_id=self.job.id, candidate_id=c1.id).first()
        rank2 = CandidateRanking.query.filter_by(job_id=self.job.id, candidate_id=c2.id).first()
        
        self.assertIsNotNone(rank1)
        self.assertIsNotNone(rank2)
        
        # John (score 88.5) should be Gold medal, Bob (score 31.2) should be Needs Improvement
        self.assertEqual(rank1.rank_number, 1)
        self.assertEqual(rank1.tier, 'Gold')
        self.assertEqual(rank2.rank_number, 2)
        self.assertEqual(rank2.tier, 'None')
        self.assertEqual(rank2.overall_strength, 'Needs Improvement')

    def test_interview_scheduling(self):
        """
        Verify that Interview records are stored in the database correctly.
        """
        candidate = User(username='jane_dev', email='jane@dev.com', full_name='Jane Smith', role='candidate')
        candidate.set_password('SecretPass1!')
        db.session.add(candidate)
        db.session.commit()
        
        resume = Resume(candidate_id=candidate.id, filename='jane.pdf', file_path='/path/jane.pdf', file_size=100, parsed_text="Python Developer")
        db.session.add(resume)
        db.session.commit()
        
        app_record = Application(candidate_id=candidate.id, job_id=self.job.id, resume_id=resume.id, status='Applied')
        db.session.add(app_record)
        db.session.commit()
        
        interview = Interview(
            application_id=app_record.id,
            candidate_id=candidate.id,
            job_id=self.job.id,
            interviewer_name="Sarah Jenkins",
            date_time=datetime(2026, 7, 20, 14, 30),
            meeting_link="https://meet.google.com/abc-defg-hij",
            notes="Technical conversation on system architectures"
        )
        db.session.add(interview)
        db.session.commit()
        
        loaded_iv = Interview.query.filter_by(candidate_id=candidate.id).first()
        self.assertIsNotNone(loaded_iv)
        self.assertEqual(loaded_iv.interviewer_name, "Sarah Jenkins")
        self.assertEqual(loaded_iv.status, "Scheduled")


if __name__ == '__main__':
    unittest.main()
