import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from database_models.models import db, User, CandidateResumeDraft, CandidateResumeVersion
from ai.candidate_resume_assistant import (
    get_default_resume_data,
    calculate_candidate_resume_scores,
    generate_candidate_ai_suggestions,
    process_candidate_chat
)
from services.candidate_resume_exporter import generate_candidate_pdf, generate_candidate_docx

def run_tests():
    print("=== STARTING CANDIDATE RESUME BUILDER VERIFICATION ===")

    # 1. Test AI Assistant Functions
    print("[1] Testing AI Assistant default data & scores...")
    default_data = get_default_resume_data("Test Candidate", "candidate@company.com")
    scores = calculate_candidate_resume_scores(default_data)
    print(f"    Scores calculated: Overall={scores['overall_resume_score']}, ATS={scores['ats_compatibility']}%, Completeness={scores['resume_completeness']}%")
    assert scores['overall_resume_score'] > 0, "Score calculation failed!"
    assert scores['ats_compatibility'] > 0, "ATS compatibility calculation failed!"

    # 2. Test Contextual Suggestions
    print("[2] Testing contextual AI suggestions...")
    suggestions = generate_candidate_ai_suggestions(default_data)
    print(f"    Generated {len(suggestions)} suggestions.")

    # 3. Test Chat Processing
    print("[3] Testing Chat Processing...")
    chat_res = process_candidate_chat("Optimize for ATS", default_data)
    print(f"    Coach Reply snippet: {chat_res['reply'][:60]}...")

    # 4. Test PDF & DOCX Generation
    print("[4] Testing PDF & DOCX Exporter services...")
    pdf_buf = generate_candidate_pdf(default_data, template_style="professional")
    pdf_bytes = pdf_buf.getvalue()
    print(f"    PDF generated: {len(pdf_bytes)} bytes.")

    docx_buf = generate_candidate_docx(default_data, template_style="corporate")
    docx_bytes = docx_buf.getvalue()
    print(f"    DOCX generated: {len(docx_bytes)} bytes.")

    # 5. Flask App Context & Route Verification
    print("[5] Testing Flask Routes in App Context...")
    with app.app_context():
        db.create_all()
        candidate = User.query.filter_by(role='candidate').first()
        if not candidate:
            candidate = User(
                username="test_cand",
                email="test_cand@example.com",
                full_name="Test Cand",
                role="candidate"
            )
            candidate.set_password("CandPass123!")
            db.session.add(candidate)
            db.session.commit()

        client = app.test_client()
        client.post('/login', data={'username': candidate.username, 'password': 'CandPass123!'}, follow_redirects=True)

        builder_res = client.get('/candidate/resume-builder')
        print(f"    GET /candidate/resume-builder status: {builder_res.status_code}")
        assert builder_res.status_code == 200, "Page load failed!"

        api_chat_res = client.post('/api/candidate-ai/chat', json={'message': 'Build My Resume', 'data': default_data})
        assert api_chat_res.status_code == 200, "API Chat failed!"
        print("    API /api/candidate-ai/chat success!")

        save_res = client.post('/api/candidate-ai/save-draft', json={'data': default_data, 'template_style': 'modern', 'label': 'Test Snapshot'})
        assert save_res.status_code == 200, "API Save draft failed!"
        save_json = save_res.get_json()
        print(f"    API /api/candidate-ai/save-draft success! Version v{save_json['version_number']}")

        admin_chat_res = client.get('/ai-chat')
        assert admin_chat_res.status_code == 200, "Admin AI Chat route broken!"
        print("    Admin /ai-chat route sanity check passed (remains unchanged)!")

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY! 🎉")

if __name__ == '__main__':
    run_tests()
