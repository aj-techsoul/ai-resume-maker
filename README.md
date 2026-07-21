# ScreenAI — Resume Screening & AI Builder Platform

ScreenAI is an end-to-end recruitment platform built with Python and Flask. It combines an automated ATS screening engine for recruiters with an interactive AI resume builder for job applicants.

---

## What it does

### For Candidates
* **AI Resume Builder & Career Coach**: An interactive assistant that helps refine resume bullet points, suggest technical skills, reword experience entries with power action verbs, and format sections.
* **Live Document Preview**: Real-time document preview with zoom, text search, page navigation, and template switching across 10 ATS-friendly designs (Executive, Corporate, Modern, Software Engineer, Data Scientist, etc.).
* **Instant Export & Versioning**: Download styled resumes as ReportLab PDFs or editable `.docx` files, with version history snapshots.
* **Candidate Dashboard**: Track submitted applications, view recruitment stage history, and monitor ATS compatibility scores.

### For Recruiters & HR Admins
* **Automated ATS Resume Parser**: Extracts and parses PDF and Word resumes using `pdfplumber` and `python-docx`.
* **TF-IDF Candidate Scoring & Ranking**: Matches candidate profiles against job postings based on skill alignment, experience records, and NLP text similarity (no dummy numbers).
* **Recruiter Analytics**: Funnel conversion stats, candidate rankings (Gold, Silver, Bronze badges), skill gap insights, and Chart.js analytics.
* **Interview Scheduling & Reports**: Generate automated PDF screening reports via ReportLab and manage candidate interview status.

### Design System & Dark Mode
* Includes **5 built-in theme presets** (Executive Blue, Emerald Green, Royal Indigo, Slate Dark, and Graphite Dark) with smooth client-side theme switching and persistent preferences.

---

## Tech Stack

* **Backend**: Python 3.8+, Flask, SQLAlchemy, SQLite
* **NLP & Parsing**: spaCy, NLTK, Scikit-learn (TF-IDF), pdfplumber, python-docx
* **Exporters**: ReportLab (PDF generation), python-docx (Word generation)
* **Frontend**: HTML5, Vanilla CSS3 (8px grid, multi-theme tokens), Bootstrap 5, Chart.js

---

## Project Structure

```text
resume-ai/
├── app.py                          # Flask application entry point & API endpoints
├── database_models/
│   └── models.py                   # SQLAlchemy schema (Users, Resumes, Jobs, Drafts, Snapshots)
├── ai/
│   ├── preprocess.py               # Text cleaning & tokenization
│   ├── scorer.py                   # TF-IDF ATS matching algorithm
│   └── candidate_resume_assistant.py # AI Career Coach logic & score calculations
├── parsers/                        # Document text extraction (pdfplumber, docx)
├── services/                       # PDF/DOCX export generators
├── static/                         # CSS variables, JS handlers, Chart.js scripts
└── templates/                      # Jinja2 HTML templates
```

---

## Getting Started

### 1. Set Up Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Download NLP Models (Optional)

The application automatically loads NLP models on launch, but you can pre-download them:

```bash
python -m spacy download en_core_web_sm
```

### 3. Launch Application

```bash
python app.py
```

The server will start at **`http://127.0.0.1:5000`**.

---

## Demo Credentials

* **Recruiter / Admin Account**:
  * **Email**: `admin@company.com` (or username `admin`)
  * **Password**: `AdminPass123!`

* **Candidate Account**:
  * Register a candidate account on the signup page to test the candidate dashboard and AI builder.

---

## Running Tests

Run the test suite to verify database setup, parsers, and scoring algorithms:

```bash
python test.py
```
