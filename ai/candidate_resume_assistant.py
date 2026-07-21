import json
import re

DEFAULT_ACTION_VERBS = [
    "Spearheaded", "Engineered", "Optimized", "Orchestrated", "Implemented", 
    "Architected", "Accelerated", "Developed", "Streamlined", "Pioneered",
    "Automated", "Transformed", "Designed", "Executed", "Formulated"
]

RECOMMENDED_SKILLS_BY_ROLE = {
    "developer": ["Python", "JavaScript", "React", "Node.js", "Docker", "Git", "REST APIs", "SQL", "CI/CD", "TypeScript"],
    "software": ["Data Structures", "Algorithms", "System Design", "PostgreSQL", "Cloud Computing", "AWS", "Agile", "Unit Testing"],
    "data": ["Python", "SQL", "Pandas", "NumPy", "Scikit-Learn", "TensorFlow", "PowerBI", "Data Pipelines", "Machine Learning"],
    "manager": ["Project Management", "Agile/Scrum", "Team Leadership", "Strategic Planning", "Stakeholder Management", "KPI Tracking"],
    "default": ["Problem Solving", "Team Collaboration", "Communication", "Time Management", "Critical Thinking", "Adaptability"]
}

def get_default_resume_data(user_name="", user_email=""):
    """
    Returns default structured resume JSON for candidate builder.
    """
    return {
        "full_name": user_name or "Jane Doe",
        "professional_title": "Full Stack Software Engineer",
        "email": user_email or "jane.doe@example.com",
        "phone": "+1 (555) 234-5678",
        "address": "San Francisco, CA",
        "linkedin": "https://linkedin.com/in/janedoe",
        "github": "https://github.com/janedoe",
        "portfolio": "https://janedoe.dev",
        "career_objective": "Results-driven Software Engineer with 3+ years of experience crafting high-scalable web applications, optimizing microservices, and leading cross-functional teams.",
        "education": [
            {
                "degree": "B.S. in Computer Science",
                "institution": "University of Technology",
                "year": "2019 - 2023",
                "gpa_details": "GPA 3.8/4.0 - Dean's List"
            }
        ],
        "work_experience": [
            {
                "title": "Software Engineer",
                "company": "Tech Solutions Inc.",
                "duration": "2023 - Present",
                "location": "San Francisco, CA",
                "responsibilities": [
                    "Engineered RESTful APIs serving over 100k daily active users with 99.9% uptime.",
                    "Optimized database query performance by 40% through indexing and caching strategies.",
                    "Collaborated with product teams to roll out automated deployment pipelines."
                ]
            }
        ],
        "internships": [
            {
                "role": "Frontend Developer Intern",
                "organization": "CloudScale Systems",
                "duration": "Summer 2022",
                "details": "Developed interactive dashboards in React, improving user engagement by 25%."
            }
        ],
        "projects": [
            {
                "title": "AI Resume Builder & Screener",
                "tech_stack": "Python, Flask, React, SQLite",
                "description": "Architected an interactive career assistant app providing real-time ATS scoring and instant resume generation.",
                "impact": "Reduced user resume creation time by 60% with instant template exporting."
            }
        ],
        "technical_skills": ["Python", "JavaScript", "React", "Flask", "SQL", "Git", "Docker", "REST APIs"],
        "soft_skills": ["Problem Solving", "Cross-functional Collaboration", "Agile Methodology", "Communication"],
        "certifications": ["AWS Certified Cloud Practitioner", "Scrum Master Accredited"],
        "achievements": ["1st Place Hackathon Winner 2023", "Published Tech Blog Author (10k+ readers)"],
        "languages": ["English (Native)", "Spanish (Professional)"],
        "hobbies": ["Open Source Contributing", "Tech Blogging", "Chess"],
        "references": ["Available upon request"]
    }


def calculate_candidate_resume_scores(resume_data):
    """
    Calculates live resume metrics dynamically:
    - ATS Compatibility
    - Resume Completeness
    - Grammar Score
    - Formatting Score
    - Professionalism Score
    - Technical Strength
    - Overall Resume Score
    """
    if not isinstance(resume_data, dict):
        resume_data = {}

    # 1. Resume Completeness (Check 20 key areas)
    fields_to_check = [
        "full_name", "professional_title", "email", "phone", "address",
        "linkedin", "github", "portfolio", "career_objective",
        "education", "work_experience", "internships", "projects",
        "technical_skills", "soft_skills", "certifications", "achievements",
        "languages", "hobbies", "references"
    ]
    
    filled_count = 0
    for field in fields_to_check:
        val = resume_data.get(field)
        if val:
            if isinstance(val, list) and len(val) > 0:
                filled_count += 1
            elif isinstance(val, str) and len(val.strip()) > 0:
                filled_count += 1
                
    completeness_score = min(100.0, round((filled_count / len(fields_to_check)) * 100, 1))

    # 2. Technical Strength
    tech_skills = resume_data.get("technical_skills", [])
    projects = resume_data.get("projects", [])
    tech_skill_count = len(tech_skills) if isinstance(tech_skills, list) else 0
    
    # Check for metrics (% or numbers) in work experience and projects
    has_metrics = False
    all_text = json.dumps(resume_data)
    if re.search(r'\b\d+%\b|\b\d+\b\s*(users|clients|percent|ms|k|m)', all_text, re.IGNORECASE):
        has_metrics = True
        
    tech_base = min(60, tech_skill_count * 8)
    if projects:
        tech_base += 25
    if has_metrics:
        tech_base += 15
    technical_strength = min(100.0, round(float(tech_base), 1))

    # 3. Formatting Score
    formatting_base = 70.0
    if resume_data.get("full_name") and resume_data.get("email"):
        formatting_base += 10.0
    if isinstance(resume_data.get("education"), list) and len(resume_data.get("education")) > 0:
        formatting_base += 10.0
    if isinstance(resume_data.get("work_experience"), list) and len(resume_data.get("work_experience")) > 0:
        formatting_base += 10.0
    formatting_score = min(100.0, formatting_base)

    # 4. Grammar & Action Verb Score
    grammar_base = 80.0
    objective = resume_data.get("career_objective", "")
    if len(objective) > 30:
        grammar_base += 10.0
        
    # Check for strong action verbs in experience
    verb_found = False
    exp_list = resume_data.get("work_experience", [])
    if isinstance(exp_list, list):
        for exp in exp_list:
            resps = exp.get("responsibilities", []) if isinstance(exp, dict) else []
            for r in resps:
                first_word = r.strip().split()[0] if r.strip() else ""
                if first_word in DEFAULT_ACTION_VERBS:
                    verb_found = True
                    break
    if verb_found:
        grammar_base += 10.0
    grammar_score = min(100.0, grammar_base)

    # 5. Professionalism Score
    prof_base = 75.0
    if resume_data.get("linkedin"):
        prof_base += 10.0
    if resume_data.get("github") or resume_data.get("portfolio"):
        prof_base += 10.0
    if resume_data.get("certifications"):
        prof_base += 5.0
    professionalism_score = min(100.0, prof_base)

    # 6. ATS Compatibility Score
    ats_base = 65.0
    if completeness_score >= 80:
        ats_base += 15
    if technical_strength >= 75:
        ats_base += 10
    if verb_found:
        ats_base += 10
    ats_compatibility = min(100.0, float(ats_base))

    # Overall Score (Weighted)
    overall_score = round(
        (0.25 * ats_compatibility) +
        (0.20 * completeness_score) +
        (0.15 * grammar_score) +
        (0.15 * formatting_score) +
        (0.15 * professionalism_score) +
        (0.10 * technical_strength), 1
    )

    return {
        "overall_resume_score": overall_score,
        "ats_compatibility": ats_compatibility,
        "resume_completeness": completeness_score,
        "grammar_score": grammar_score,
        "formatting_score": formatting_score,
        "professionalism_score": professionalism_score,
        "technical_strength": technical_strength
    }


def generate_candidate_ai_suggestions(resume_data):
    """
    Generates contextual actionable suggestions for the candidate with 1-click apply data.
    """
    suggestions = []

    # Check missing contact details
    if not resume_data.get("linkedin"):
        suggestions.append({
            "id": "add_linkedin",
            "type": "contact",
            "title": "Add LinkedIn Profile",
            "text": "Candidates with a LinkedIn link receive 71% more interview callbacks.",
            "action_label": "Add Default LinkedIn",
            "apply_key": "linkedin",
            "apply_val": "https://linkedin.com/in/" + (resume_data.get("full_name", "candidate").lower().replace(" ", ""))
        })

    if not resume_data.get("github"):
        suggestions.append({
            "id": "add_github",
            "type": "contact",
            "title": "Add GitHub Portfolio",
            "text": "Showcase code quality and repositories directly to recruiters.",
            "action_label": "Add GitHub Profile",
            "apply_key": "github",
            "apply_val": "https://github.com/" + (resume_data.get("full_name", "candidate").lower().replace(" ", ""))
        })

    # Check Technical Skills
    tech_skills = resume_data.get("technical_skills", [])
    if len(tech_skills) < 6:
        title = resume_data.get("professional_title", "").lower()
        recommended = RECOMMENDED_SKILLS_BY_ROLE.get("developer")
        for key in RECOMMENDED_SKILLS_BY_ROLE:
            if key in title:
                recommended = RECOMMENDED_SKILLS_BY_ROLE[key]
                break
        missing_skills = [s for s in recommended if s not in tech_skills][:3]
        if missing_skills:
            suggestions.append({
                "id": "add_skills",
                "type": "skills",
                "title": "Recommended Industry Skills",
                "text": f"Add trending skills for your title: {', '.join(missing_skills)}",
                "action_label": "Add Skills",
                "apply_key": "technical_skills_append",
                "apply_val": missing_skills
            })

    # Check Action Verbs & Metrics
    all_text = json.dumps(resume_data)
    if not re.search(r'\b\d+%\b|\b\d+\b\s*(users|clients|percent|ms|k|m)', all_text, re.IGNORECASE):
        suggestions.append({
            "id": "quantify_achievements",
            "type": "content",
            "title": "Add Quantifiable Metrics",
            "text": "Resumes with numbers, percentages, and metrics rank 40% higher in ATS filters.",
            "action_label": "Optimize Work Bullet",
            "apply_key": "quantify_sample",
            "apply_val": "Improved API throughput by 35% and reduced latency to under 120ms."
        })

    # Check Summary Statement
    summary = resume_data.get("career_objective", "")
    if len(summary) < 40:
        suggestions.append({
            "id": "improve_summary",
            "type": "summary",
            "title": "Enhance Professional Summary",
            "text": "Craft a high-impact summary highlighting years of experience and core strengths.",
            "action_label": "Generate Executive Summary",
            "apply_key": "career_objective",
            "apply_val": f"Dedicated {resume_data.get('professional_title', 'Professional')} with expertise in scalable systems, modern tools, and driving impactful technology solutions."
        })

    # Recommended Certifications
    certs = resume_data.get("certifications", [])
    if not certs:
        suggestions.append({
            "id": "add_cert",
            "type": "certification",
            "title": "Add Industry Certifications",
            "text": "Certifications validate domain expertise to hiring managers.",
            "action_label": "Add Cloud Cert",
            "apply_key": "certifications_append",
            "apply_val": ["AWS Certified Solutions Architect"]
        })

    return suggestions


def process_candidate_chat(user_query, resume_data, chat_history=None):
    """
    Main interactive Career Coach logic for candidate resume builder.
    """
    if not isinstance(resume_data, dict):
        resume_data = get_default_resume_data()
        
    query_lower = user_query.strip().lower()
    updated_data = dict(resume_data)
    reply_text = ""
    
    # 1. Action Intent Detection
    if "build my resume" in query_lower or "start building" in query_lower:
        reply_text = (
            "Fantastic! Let's build a top-tier ATS resume step by step. 🚀\n\n"
            f"Currently, your resume title is set to **{updated_data.get('professional_title')}**.\n"
            "Would you like to update your **Full Name**, **Professional Title**, or start with your **Work Experience**?"
        )
    elif "improve my resume" in query_lower or "review my resume" in query_lower or "review" in query_lower:
        scores = calculate_candidate_resume_scores(updated_data)
        reply_text = (
            f"📊 **Resume Review & ATS Breakdown:**\n\n"
            f"• **Overall Score:** {scores['overall_resume_score']}/100\n"
            f"• **ATS Match:** {scores['ats_compatibility']}%\n"
            f"• **Completeness:** {scores['resume_completeness']}%\n"
            f"• **Technical Strength:** {scores['technical_strength']}%\n\n"
            "💡 **Coach Advice:** I recommend adding quantifiable metrics to your work accomplishments and adding industry certifications."
        )
    elif "optimize for ats" in query_lower or "ats" in query_lower:
        # Auto-enhance work experience bullet points with action verbs
        exps = updated_data.get("work_experience", [])
        if isinstance(exps, list) and len(exps) > 0:
            for exp in exps:
                resps = exp.get("responsibilities", [])
                new_resps = []
                for r in resps:
                    words = r.split()
                    if words and words[0] not in DEFAULT_ACTION_VERBS:
                        new_r = f"Spearheaded and {r[0].lower()}{r[1:]}"
                        new_resps.append(new_r)
                    else:
                        new_resps.append(r)
                exp["responsibilities"] = new_resps
            updated_data["work_experience"] = exps
        reply_text = "⚡ **ATS Optimization Applied!** I've reformatted your work bullet points with strong power action verbs to boost ATS parser scoring."
        
    elif "suggest better skills" in query_lower or "skills" in query_lower:
        new_skills = ["Docker", "Kubernetes", "GraphQL", "CI/CD Pipelines", "System Design"]
        curr_skills = list(updated_data.get("technical_skills", []))
        added = []
        for s in new_skills:
            if s not in curr_skills:
                curr_skills.append(s)
                added.append(s)
        updated_data["technical_skills"] = curr_skills
        reply_text = f"✨ **Added Top Skills:** Added {', '.join(added)} to your Technical Skills section!"
        
    elif "improve project descriptions" in query_lower or "project" in query_lower:
        projs = updated_data.get("projects", [])
        if isinstance(projs, list) and len(projs) > 0:
            for p in projs:
                p["description"] = f"Architected high-performance {p.get('title', 'application')} utilizing modern design patterns, ensuring low latency and 99.9% availability."
                p["impact"] = "Increased efficiency by 35% and scaled system to handle high concurrency."
            updated_data["projects"] = projs
        reply_text = "🚀 **Projects Enhanced!** Upgraded project bullet points with high-impact descriptions and measurable results."
        
    else:
        # Parsing direct updates from chat (e.g. "My name is John", "Email: john@test.com", "Title: DevOps Engineer")
        if "name" in query_lower and ":" in user_query:
            val = user_query.split(":", 1)[1].strip()
            updated_data["full_name"] = val
            reply_text = f"Updated your Full Name to **{val}**."
        elif "title" in query_lower and ":" in user_query:
            val = user_query.split(":", 1)[1].strip()
            updated_data["professional_title"] = val
            reply_text = f"Updated your Professional Title to **{val}**."
        elif "email" in query_lower and ":" in user_query:
            val = user_query.split(":", 1)[1].strip()
            updated_data["email"] = val
            reply_text = f"Updated your Email to **{val}**."
        elif "phone" in query_lower and ":" in user_query:
            val = user_query.split(":", 1)[1].strip()
            updated_data["phone"] = val
            reply_text = f"Updated your Phone Number to **{val}**."
        elif "add skill" in query_lower:
            val = user_query.replace("add skill", "").replace("Add skill", "").replace(":", "").strip()
            curr = list(updated_data.get("technical_skills", []))
            if val and val not in curr:
                curr.append(val)
                updated_data["technical_skills"] = curr
                reply_text = f"Added **{val}** to your technical skills!"
            else:
                reply_text = f"Skill **{val}** is already present or invalid."
        else:
            reply_text = (
                f"I've received your input: *\"{user_query}\"*.\n\n"
                "I can help you rewrite project details, optimize bullet points with action verbs, calculate live ATS compatibility, or switch modern resume templates!"
            )

    # Recalculate scores & suggestions
    scores = calculate_candidate_resume_scores(updated_data)
    suggestions = generate_candidate_ai_suggestions(updated_data)
    
    quick_actions = [
        "Build My Resume",
        "Improve My Resume",
        "Review My Resume",
        "Optimize for ATS",
        "Suggest Better Skills",
        "Improve Project Descriptions"
    ]

    return {
        "reply": reply_text,
        "updated_data": updated_data,
        "scores": scores,
        "suggestions": suggestions,
        "quick_actions": quick_actions
    }
