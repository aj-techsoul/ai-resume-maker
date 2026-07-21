import re
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .preprocess import preprocess_and_tokenize, clean_text

ROLE_SKILLS_MAP = {
    'frontend': ['React', 'Vue', 'TypeScript', 'JavaScript', 'Tailwind CSS', 'Bootstrap', 'HTML5', 'CSS3', 'Webpack', 'Sass', 'Redux'],
    'backend': ['Python', 'Django', 'Flask', 'Node.js', 'Express', 'Java', 'Spring Boot', 'Go', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Docker', 'REST API', 'GraphQL'],
    'ai': ['Python', 'PyTorch', 'TensorFlow', 'Scikit-learn', 'NLP', 'Deep Learning', 'Computer Vision', 'spaCy', 'NLTK', 'HuggingFace', 'LLMs', 'OpenCV'],
    'data': ['Python', 'SQL', 'Pandas', 'NumPy', 'R', 'Tableau', 'PowerBI', 'Data Warehousing', 'ETL', 'Machine Learning', 'Statistics'],
    'devops': ['AWS', 'Docker', 'Kubernetes', 'Terraform', 'Ansible', 'CI/CD', 'GitHub Actions', 'Jenkins', 'Linux', 'Bash', 'Prometheus', 'Grafana'],
    'fullstack': ['React', 'Node.js', 'Express', 'Python', 'Flask', 'TypeScript', 'PostgreSQL', 'Docker', 'AWS', 'HTML5', 'CSS3', 'JavaScript'],
    'design': ['Figma', 'Adobe XD', 'Sketch', 'Wireframing', 'Prototyping', 'User Research', 'UI Design', 'UX Design', 'Interaction Design']
}

SOFT_SKILLS = [
    'leadership', 'communication', 'collaboration', 'problem solving', 'teamwork', 'adaptability', 
    'mentorship', 'time management', 'critical thinking', 'creativity', 'negotiation', 'presentation',
    'conflict resolution', 'emotional intelligence', 'active listening', 'decision making'
]

POWER_VERBS = [
    'achieved', 'acquired', 'administered', 'advised', 'analyzed', 'architected', 'assembled', 'automated',
    'built', 'calculated', 'capitalized', 'championed', 'coached', 'collaborated', 'compiled', 'completed',
    'conceived', 'conducted', 'constructed', 'contracted', 'coordinated', 'created', 'debugged', 'delivered',
    'designed', 'detected', 'developed', 'devised', 'directed', 'distributed', 'documented', 'engineered',
    'enhanced', 'established', 'evaluated', 'executed', 'expanded', 'expedited', 'facilitated', 'formulated',
    'generated', 'guided', 'headed', 'identified', 'implemented', 'improved', 'increased', 'initiated',
    'innovated', 'inspected', 'installed', 'instituted', 'integrated', 'introduced', 'invented', 'investigated',
    'launched', 'led', 'managed', 'maximized', 'mentored', 'merged', 'minimized', 'modeled', 'monitored',
    'negotiated', 'operated', 'optimized', 'orchestrated', 'organized', 'originated', 'overhauled', 'oversaw',
    'pioneered', 'planned', 'prepared', 'presented', 'produced', 'programmed', 'projected', 'promoted',
    'qualified', 'recommended', 'reconstructed', 'redesigned', 'reduced', 'reengineered', 'reorganized', 'resolved',
    'restructured', 'retrieved', 'revamped', 'scheduled', 'shaped', 'solved', 'spearheaded', 'standardized',
    'steered', 'streamlined', 'supervised', 'supported', 'synthesized', 'systematized', 'targeted', 'trained',
    'transformed', 'upgraded', 'validated', 'wrote'
]

def count_syllables(word):
    word = word.lower()
    count = 0
    vowels = "aeiouy"
    if not word:
        return 0
    if word[0] in vowels:
        count += 1
    for index in range(1, len(word)):
        if word[index] in vowels and word[index - 1] not in vowels:
            count += 1
    if word.endswith("e"):
        count -= 1
    if count == 0:
        count += 1
    return count

def calculate_readability(text):
    if not text:
        return 0.0
    words = re.findall(r'\b\w+\b', text)
    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if s.strip()]
    num_words = len(words)
    num_sentences = len(sentences) if sentences else 1
    if num_words == 0:
        return 0.0
    num_syllables = sum(count_syllables(w) for w in words)
    score = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)
    return max(0.0, min(100.0, score))

def check_grammar_heuristics(text):
    if not text:
        return 0.0
    score = 100.0
    excl_count = text.count('!')
    if excl_count > 2:
        score -= min(15.0, excl_count * 3)
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    bad_sentences = 0
    for s in sentences:
        if s and s[0].islower() and not s.startswith(('http', 'www')):
            bad_sentences += 1
    if sentences:
        bad_pct = (bad_sentences / len(sentences)) * 100
        score -= min(30.0, bad_pct * 0.5)
    paragraphs = [p for p in text.split('\n') if p.strip()]
    for p in paragraphs:
        if len(p.split()) > 100:
            score -= 10
    return max(30.0, score)

def get_job_role_category(job_title):
    title_lower = job_title.lower()
    if 'front' in title_lower or 'ui' in title_lower or 'ux' in title_lower or 'designer' in title_lower:
        if 'design' in title_lower:
            return 'design'
        return 'frontend'
    elif 'back' in title_lower or 'api' in title_lower or 'django' in title_lower or 'node' in title_lower:
        return 'backend'
    elif 'ai' in title_lower or 'nlp' in title_lower or 'machine' in title_lower or 'ml' in title_lower or 'learning' in title_lower or 'deep' in title_lower or 'vision' in title_lower:
        return 'ai'
    elif 'data' in title_lower or 'analyst' in title_lower or 'sql' in title_lower or 'bi' in title_lower:
        return 'data'
    elif 'devops' in title_lower or 'cloud' in title_lower or 'aws' in title_lower or 'infrastructure' in title_lower or 'security' in title_lower:
        return 'devops'
    elif 'full' in title_lower or 'stack' in title_lower:
        return 'fullstack'
    return 'backend'

def score_resume_against_job(parsed_resume, job_title, job_requirements, job_desc, weighted_skills_json=None):
    """
    Compares resume against target job, yielding 12 sub-scores, overall Resume Intelligence, 
    weighted JD matches, and detailed training timelines.
    """
    resume_raw_text = parsed_resume['raw_text']
    clean_resume = clean_text(resume_raw_text)
    clean_job_desc = clean_text(job_desc)
    
    # 1. ATS COMPATIBILITY
    similarity_score = 0.0
    if clean_resume and clean_job_desc:
        try:
            vectorizer = TfidfVectorizer(tokenizer=preprocess_and_tokenize, token_pattern=None)
            tfidf = vectorizer.fit_transform([clean_resume, clean_job_desc])
            similarity_score = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]) * 100
        except Exception:
            similarity_score = 45.0
            
    # 2. WEIGHTED SKILLS (Technical Skills matches)
    req_skills = [s.strip() for s in job_requirements.split(',') if s.strip()]
    if not req_skills:
        req_skills = re.findall(r'\b[A-Z][a-zA-Z0-9+#\.\-]+', job_requirements or job_desc)
        req_skills = list(set([s for s in req_skills if len(s) > 1 and s.lower() not in ['the', 'and', 'job', 'we', 'our']]))[:10]
        
    weights = {}
    if weighted_skills_json:
        try:
            weights = json.loads(weighted_skills_json)
        except Exception:
            weights = {}
            
    # Normalize weights
    skills_weights = {skill: int(weights.get(skill, 2)) for skill in req_skills}
    
    matched_skills = []
    missing_skills = []
    
    resume_search_space = f"{parsed_resume['skills']} {parsed_resume['projects']} {parsed_resume['experience']} {resume_raw_text}".lower()
    
    total_weight = 0
    earned_weight = 0
    
    for skill in req_skills:
        escaped_skill = re.escape(skill)
        if 'c++' in skill.lower():
            pattern = r'\bc\+\+'
        elif 'c#' in skill.lower():
            pattern = r'\bc\#'
        elif '.net' in skill.lower():
            pattern = r'\.net'
        else:
            pattern = r'\b' + escaped_skill.lower() + r'\b'
            
        weight = skills_weights.get(skill, 2)
        total_weight += weight
        
        if re.search(pattern, resume_search_space):
            matched_skills.append(skill)
            earned_weight += weight
        else:
            missing_skills.append(skill)
            
    tech_skills_score = (earned_weight / total_weight) * 100 if total_weight > 0 else 100.0
    
    # 3. SOFT SKILLS
    matched_soft = []
    for soft in SOFT_SKILLS:
        if re.search(r'\b' + re.escape(soft) + r'\b', resume_search_space):
            matched_soft.append(soft.title())
    soft_skills_score = (len(matched_soft) / 6.0) * 100 if len(matched_soft) < 6 else 100.0
    
    # 4. READABILITY & GRAMMAR
    readability_score = calculate_readability(resume_raw_text)
    readability_score = max(20.0, min(100.0, readability_score))
    
    grammar_score = check_grammar_heuristics(resume_raw_text)
    
    # Communication (average of grammar & readability)
    communication_score = (readability_score + grammar_score) / 2.0
    
    # 5. EXPERIENCE & CAREER PROGRESSION
    experience_score = 50.0
    experience_text = parsed_resume['experience']
    
    exp_years_found = re.findall(r'(\d+)\+?\s*years?', experience_text.lower())
    resume_years = max([int(y) for y in exp_years_found]) if exp_years_found else 0
    
    job_years_match = re.search(r'(\d+)\+?\s*years?', (job_requirements + " " + job_desc).lower())
    job_expected_years = int(job_years_match.group(1)) if job_years_match else 0
    
    if job_expected_years > 0:
        if resume_years >= job_expected_years:
            experience_score = 100.0
        else:
            experience_score = (resume_years / job_expected_years) * 100
    else:
        experience_score = 70.0
        if len(experience_text.split()) > 100:
            experience_score += 20
            
    # Check career progression & leadership tags
    progression_found = sum(1 for kw in ['promoted', 'spearheaded', 'led', 'senior', 'lead', 'manager', 'director', 'founder'] if kw in experience_text.lower())
    experience_score = min(100.0, experience_score + (progression_found * 5))
    
    # 6. EDUCATION
    education_score = 50.0
    education_text = parsed_resume['education']
    edu_match_count = sum(1 for deg in ['bachelor', 'master', 'phd', 'degree', 'computer science'] if deg in education_text.lower())
    education_score = min(100.0, 50.0 + (edu_match_count * 15))
    
    # 7. PROJECTS
    projects_score = 40.0
    projects_text = parsed_resume['projects']
    if len(projects_text.split()) > 30:
        projects_score += 20
    # Search power verbs in projects
    proj_verbs = sum(1 for verb in POWER_VERBS if verb in projects_text.lower())
    projects_score += min(20.0, proj_verbs * 4)
    # Search metrics
    proj_metrics = sum(1 for pat in [r'\d+%', r'\$\d+', r'\b(?:reduced|increased|optimized)\b'] if re.search(pat, projects_text.lower()))
    projects_score += min(20.0, proj_metrics * 10)
    projects_score = min(100.0, projects_score)
    
    # 8. CERTIFICATIONS
    cert_text = parsed_resume['certifications']
    certifications_score = min(100.0, 40.0 + (len(cert_text.split()) / 5) * 10) if cert_text else 30.0
    
    # 9. FORMATTING & PROFESSIONALISM
    formatting_score = 30.0
    sections_present = sum(1 for sec in ['education', 'experience', 'skills', 'projects'] if parsed_resume[sec])
    formatting_score += (sections_present * 12.5)
    contacts = sum(1 for f in ['email', 'phone', 'linkedin', 'github'] if parsed_resume[f])
    formatting_score += (contacts * 5.0)
    formatting_score = min(100.0, formatting_score)
    
    professionalism_score = 40.0
    if parsed_resume['linkedin']: professionalism_score += 20
    if parsed_resume['github']: professionalism_score += 20
    if len(parsed_resume['summary']) > 20: professionalism_score += 20
    professionalism_score = min(100.0, professionalism_score)
    
    # Keyword density score
    total_words = len(re.findall(r'\b\w+\b', resume_raw_text))
    flat_matched = sum(resume_raw_text.lower().count(skill.lower()) for skill in req_skills)
    keyword_density = (flat_matched / total_words) * 100 if total_words > 0 else 0.0
    
    if 1.5 <= keyword_density <= 3.5:
        keyword_density_score = 100.0
    elif keyword_density < 1.5:
        keyword_density_score = 50.0 + (keyword_density / 1.5) * 45.0
    else:
        keyword_density_score = max(40.0, 100.0 - (keyword_density - 3.5) * 10.0)
        
    # Combine ATS Compatibility Score
    # Weighted average: similarity (40%), Tech Skills (40%), exp (10%), edu (10%)
    ats_compatibility = (similarity_score * 0.40) + (tech_skills_score * 0.40) + (experience_score * 0.10) + (education_score * 0.10)
    ats_compatibility = round(max(10.0, min(99.0, ats_compatibility)), 1)
    
    # Combined Overall Quality Score (average of structural ratings)
    overall_rating = round((readability_score + formatting_score + keyword_density_score + grammar_score + projects_score + professionalism_score) / 6.0, 1)
    
    # Combined overall Resume Intelligence Score (weighted average of structural and text match scores)
    overall_intelligence_score = (ats_compatibility * 0.35) + (tech_skills_score * 0.20) + (soft_skills_score * 0.10) + (experience_score * 0.15) + (projects_score * 0.10) + (professionalism_score * 0.10)
    overall_intelligence_score = round(max(10.0, min(99.5, overall_intelligence_score)), 1)
    
    # 10. RATINGS AND TIERS
    if overall_intelligence_score >= 85:
        match_rating = "Excellent"
    elif overall_intelligence_score >= 70:
        match_rating = "Good"
    elif overall_intelligence_score >= 55:
        match_rating = "Average"
    else:
        match_rating = "Poor"
        
    # 11. KEYWORD EXTRACTOR
    words_list = clean_resume.split()
    freq_dict = {}
    for w in words_list:
        if len(w) > 3 and w not in ['with', 'from', 'this', 'that', 'have', 'experience', 'project']:
            freq_dict[w] = freq_dict.get(w, 0) + 1
            
    repeated_keywords = []
    for key, count in freq_dict.items():
        if count > 5 and key in [s.lower() for s in req_skills]:
            repeated_keywords.append({'keyword': key, 'count': count})
            
    matched_power_verbs = list(set([verb for verb in POWER_VERBS if verb in f"{projects_text} {experience_text}".lower()]))[:8]
    
    # 12. SKILL GAP AND ADVICE
    role_cat = get_job_role_category(job_title)
    general_role_skills = ROLE_SKILLS_MAP.get(role_cat, ROLE_SKILLS_MAP['backend'])
    
    high_priority_skills = [s for s in missing_skills if s in general_role_skills][:3]
    optional_skills = [s for s in missing_skills if s not in general_role_skills][:4]
    
    recommended_skills = [s for s in general_role_skills if s.lower() not in [m.lower() for m in matched_skills]][:5]
    
    # Career suggested courses
    recommended_courses = []
    for skill in recommended_skills[:3]:
        recommended_courses.append({
            'skill': skill,
            'course': f"Specialized {skill} Development Program (Coursera/edX)"
        })
        
    recommended_certifications = []
    if role_cat in ['devops', 'backend']:
        recommended_certifications = ['AWS Certified Solutions Architect', 'Docker Certified Associate']
    elif role_cat in ['ai', 'data']:
        recommended_certifications = ['TensorFlow Developer Certificate', 'Google Professional Data Engineer']
    else:
        recommended_certifications = ['Certified ScrumMaster (CSM)', 'Google UX Design Certificate']
        
    suggested_projects = [
        f"Build an open-source scalable system demonstrating {', '.join(recommended_skills[:2])}.",
        "Optimize query indexing and migrate data configurations on AWS/Docker environments."
    ]
    
    # Create learning timeline
    learning_timeline = {
        'Week 1-3': f"Complete core learning modules on {', '.join(recommended_skills[:2]) if recommended_skills else 'missing requirements'}.",
        'Week 4-6': "Develop a portfolio project incorporating action verbs and quantifiable impact metrics.",
        'Week 7-8': "Publish codebase to GitHub and integrate LinkedIn profile hooks for recruiter visibility."
    }

    # Strengths, Weaknesses, Suggestions
    strengths = []
    weaknesses = []
    suggestions = []
    
    if overall_intelligence_score >= 80:
        strengths.append(f"Strong overall resume matching (Intelligence Score: {overall_intelligence_score}%).")
    if len(matched_skills) >= 3:
        strengths.append(f"Demonstrated command of core tech: {', '.join(matched_skills[:2])}.")
    if parsed_resume['github'] and parsed_resume['linkedin']:
        strengths.append("Excellent professional presence (linked LinkedIn & GitHub profiles).")
    if projects_score >= 80:
        strengths.append("Project logs utilize high-impact action verbs and quantitative metrics.")
        
    if len(strengths) < 2:
        strengths.append("Document features logical section formatting and clean styling.")
        strengths.append("Basic contact details are completely filled out and readable.")
        
    if missing_skills:
        weaknesses.append(f"Missing core technology requirements: {', '.join(missing_skills[:2])}.")
    if not parsed_resume['linkedin']:
        weaknesses.append("Missing LinkedIn link, which is standard for quick recruiter checks.")
    if not parsed_resume['github'] and role_cat in ['backend', 'frontend', 'ai']:
        weaknesses.append("No active GitHub repository listed to audit code quality.")
    if projects_score < 70:
        weaknesses.append("Project descriptions are descriptive rather than impact-focused.")
        
    if len(weaknesses) < 2:
        weaknesses.append("Missing specialized cloud architectures or certifications.")
        weaknesses.append("No leadership indicators or career progression markers identified.")
        
    if missing_skills:
        suggestions.append(f"Incorporate missing core technologies: {', '.join(missing_skills[:2])} if you have prior exposure.")
    if not parsed_resume['linkedin']:
        suggestions.append("Add a hyperlink to a detailed professional LinkedIn profile.")
    if projects_score < 80:
        suggestions.append("Refactor project logs using action verbs and percent metrics (e.g. 'Boosted performance by 25%').")
    if recommended_skills:
        suggestions.append(f"Acquire foundation skills: {', '.join(recommended_skills[:2])}.")
        
    if len(suggestions) < 2:
        suggestions.append("Incorporate quantitative metrics to highlight projects impact.")
        suggestions.append("List industry certifications to demonstrate continuous learning.")

    # Executive AI summary
    insights_summary = f"This candidate demonstrates {match_rating.lower()} alignment with the {job_title} role. "
    if matched_skills:
        insights_summary += f"Strengths include working experience with {', '.join(matched_skills[:2])}. "
    if missing_skills:
        insights_summary += f"Primary skill gaps are identified in {', '.join(missing_skills[:2])}, and we recommend developing certifications like {', '.join(recommended_certifications[:1])} to improve profile matching."
    else:
        insights_summary += "The candidate meets all core requirements of the job description."

    return {
        'ats_match_score': ats_compatibility, # compatibility score
        'match_rating': match_rating,
        'grammar_score': grammar_score,
        'formatting_score': formatting_score,
        'readability_score': readability_score,
        'professionalism_score': professionalism_score,
        'project_quality_score': projects_score,
        'overall_rating': overall_rating,
        
        # New Enterprise Upgraded Fields
        'ats_compatibility': ats_compatibility,
        'tech_skills': tech_skills_score,
        'soft_skills': soft_skills_score,
        'communication': communication_score,
        'experience_score': experience_score,
        'education_score': education_score,
        'projects_score': projects_score,
        'certifications_score': certifications_score,
        'overall_intelligence_score': overall_intelligence_score,
        'insights_summary': insights_summary,
        
        # Lists / Details
        'strengths': json.dumps(strengths),
        'weaknesses': json.dumps(weaknesses),
        'suggestions': json.dumps(suggestions),
        'skills_present': json.dumps(matched_skills),
        'skills_missing': json.dumps(missing_skills),
        'high_priority_skills': json.dumps(high_priority_skills),
        'optional_skills': json.dumps(optional_skills),
        'recommended_skills': json.dumps(recommended_skills),
        'recommended_courses': json.dumps(recommended_courses),
        'recommended_certifications': json.dumps(recommended_certifications),
        'suggested_projects': json.dumps(suggested_projects),
        'learning_timeline': json.dumps(learning_timeline),
        
        # Keywords
        'matched_keywords': json.dumps(req_skills[:10]),
        'missing_keywords': json.dumps(missing_skills[:10]),
        'repeated_keywords': json.dumps(repeated_keywords),
        'power_verbs': json.dumps(matched_power_verbs)
    }
