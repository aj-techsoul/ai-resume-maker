import pdfplumber

def extract_text_from_pdf(file_path):
    """
    Extracts raw text from a PDF file using pdfplumber.
    Provides a fallback to PyMuPDF (fitz) if pdfplumber fails or is unavailable.
    """
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"pdfplumber failed: {e}. Attempting PyMuPDF fallback...")
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text() + "\n"
        except Exception as e2:
            print(f"PyMuPDF fallback failed as well: {e2}")
            
    return text.strip()
