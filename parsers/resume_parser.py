import re
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None

def extract_contact_info(text):
    """
    Extract email, phone, and URLs from raw resume text using regular expressions.
    """
    # Email regex
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    emails = re.findall(email_pattern, text)
    email = emails[0] if emails else ""

    # Phone regex (matches various formats like +1-123-456-7890, (123) 456 7890, etc.)
    phone_pattern = r'(?:(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4,6})'
    phones = re.findall(phone_pattern, text)
    phone = phones[0] if phones else ""

    # URL patterns
    linkedin_pattern = r'(?:linkedin\.com/in/|linkedin\.com/pub/)[a-zA-Z0-9-_/]+'
    github_pattern = r'github\.com/[a-zA-Z0-9-_]+'
    
    linkedin_matches = re.findall(linkedin_pattern, text, re.IGNORECASE)
    linkedin = "https://" + linkedin_matches[0] if linkedin_matches else ""

    github_matches = re.findall(github_pattern, text, re.IGNORECASE)
    github = "https://" + github_matches[0] if github_matches else ""

    # Find general links that are not LinkedIn or GitHub as portfolio
    url_pattern = r'https?://[a-zA-Z0-9-]+\.[a-zA-Z0-9-./?%&=_]+'
    urls = re.findall(url_pattern, text, re.IGNORECASE)
    
    portfolio = ""
    for url in urls:
        if "linkedin" not in url.lower() and "github" not in url.lower():
            portfolio = url
            break
            
    return email, phone, linkedin, github, portfolio


def extract_name(text):
    """
    Extract name using spaCy NER or first non-empty lines heuristics as fallback.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return "Unknown Candidate"

    # Strategy 1: spaCy Named Entity Recognition
    if nlp:
        doc = nlp("\n".join(lines[:5])) # Analyze the top of the resume
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                # Clean up extracted name
                candidate_name = ent.text.strip().replace('\n', ' ')
                # Ensure the name doesn't contain digits or common resume sections
                if not any(char.isdigit() for char in candidate_name) and len(candidate_name.split()) >= 2:
                    return candidate_name

    # Strategy 2: Heuristics (First few lines, filter out emails, phone numbers, and URLs)
    contact_keywords = ['email', 'phone', 'linkedin', 'github', 'resume', 'curriculum', 'cv', 'page', 'address', 'mail']
    for line in lines[:5]:
        # Skip lines containing numbers with dashes (likely phone numbers) or emails or urls
        if '@' in line or 'http' in line or 'www' in line or '.com' in line:
            continue
        if any(kw in line.lower() for kw in contact_keywords):
            continue
        if len(line.split()) >= 2 and len(line.split()) <= 4:
            # Check if line contains too many numbers or special characters
            if not re.search(r'\d', line) and not re.search(r'[;:,\-\|\(\)]', line):
                return line
                
    # Fallback to the very first line if nothing matches
    first_line = lines[0]
    if len(first_line) < 50:
        return first_line
        
    return "Unknown Candidate"


def segment_resume(text):
    """
    Splits the resume text into logical sections based on header keywords.
    """
    # Mapping section identifiers to text blocks
    sections = {
        'education': [],
        'experience': [],
        'projects': [],
        'skills': [],
        'certifications': [],
        'languages': [],
        'achievements': [],
        'publications': [],
        'summary': []
    }
    
    # Header keywords mapped to their internal identifiers
    header_mapping = {
        'education': ['education', 'academic', 'qualification', 'study', 'university', 'college', 'degree', 'academic history', 'academic qualification', 'education & credentials'],
        'experience': ['experience', 'employment', 'history', 'professional experience', 'work history', 'career', 'career history', 'work experience', 'employment history'],
        'projects': ['projects', 'academic projects', 'personal projects', 'key projects', 'technical projects', 'software projects', 'relevant projects'],
        'skills': ['skills', 'technical skills', 'skills & technologies', 'core competencies', 'expertise', 'technologies', 'tools', 'languages & technologies', 'technical expertise', 'professional skills', 'technologies used', 'specialties', 'specialization'],
        'certifications': ['certifications', 'licenses', 'courses', 'certificates', 'accreditations', 'credentials', 'professional training'],
        'languages': ['languages', 'language proficiency', 'mother tongue', 'spoken languages'],
        'achievements': ['achievements', 'awards', 'honors', 'accomplishments', 'recognition', 'honors & awards'],
        'publications': ['publications', 'papers', 'research', 'articles', 'patents', 'research papers'],
        'summary': ['summary', 'objective', 'profile', 'professional summary', 'about me', 'executive summary', 'career objective']
    }
    
    lines = text.split('\n')
    current_section = 'summary' # Default initial section for objective/summary
    
    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            continue
            
        # Check if this line is a section header
        # Header conditions: short line (<= 5 words), and matches keyword, and not a sentence
        is_header = False
        words = cleaned_line.split()
        if len(words) <= 5:
            # Clean punctuation and check matching
            norm_line = re.sub(r'[^a-zA-Z0-9\s&]', '', cleaned_line).lower().strip()
            for sec_key, keywords in header_mapping.items():
                if norm_line in keywords or any(norm_line == kw for kw in keywords):
                    current_section = sec_key
                    is_header = True
                    break
            
            # Additional heuristic: line is all-caps and matches key phrases
            if not is_header and cleaned_line.isupper():
                for sec_key, keywords in header_mapping.items():
                    if any(kw in norm_line for kw in keywords):
                        current_section = sec_key
                        is_header = True
                        break
                        
        # If it was a header line, we don't necessarily add the header word itself
        if is_header:
            continue
            
        sections[current_section].append(cleaned_line)
        
    # Join text lists into strings
    parsed_sections = {}
    for key, val in sections.items():
        parsed_sections[key] = "\n".join(val).strip()
        
    return parsed_sections


def parse_resume(file_path, file_type):
    """
    Main orchestrator that reads, cleans, and parses a resume file.
    """
    if file_type.lower() == 'pdf':
        from .pdf_parser import extract_text_from_pdf
        raw_text = extract_text_from_pdf(file_path)
    elif file_type.lower() in ['docx', 'doc']:
        from .docx_parser import extract_text_from_docx
        raw_text = extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
        
    if not raw_text:
        return {
            'name': 'Unknown Candidate', 'email': '', 'phone': '', 
            'linkedin': '', 'github': '', 'portfolio': '', 
            'education': '', 'experience': '', 'skills': '', 
            'projects': '', 'certifications': '', 'languages': '', 
            'achievements': '', 'publications': '', 'summary': '', 
            'raw_text': ''
        }
        
    email, phone, linkedin, github, portfolio = extract_contact_info(raw_text)
    name = extract_name(raw_text)
    sections = segment_resume(raw_text)
    
    parsed_resume_data = {
        'name': name,
        'email': email,
        'phone': phone,
        'linkedin': linkedin,
        'github': github,
        'portfolio': portfolio,
        'education': sections.get('education', ''),
        'experience': sections.get('experience', ''),
        'skills': sections.get('skills', ''),
        'projects': sections.get('projects', ''),
        'certifications': sections.get('certifications', ''),
        'languages': sections.get('languages', ''),
        'achievements': sections.get('achievements', ''),
        'publications': sections.get('publications', ''),
        'summary': sections.get('summary', ''),
        'raw_text': raw_text
    }
    
    return parsed_resume_data
