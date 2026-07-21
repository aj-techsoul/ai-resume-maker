import docx

def extract_text_from_docx(file_path):
    """
    Extracts text from a DOCX file, parsing both body text paragraphs
    and table cell values.
    """
    text_blocks = []
    try:
        doc = docx.Document(file_path)
        # Extract paragraph texts
        for paragraph in doc.paragraphs:
            if paragraph.text:
                text_blocks.append(paragraph.text)
        
        # Extract text from tables (often used in resumes for education or skill grids)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    # Avoid adding identical text if cells are merged
                    cell_text = cell.text.strip()
                    if cell_text and (not text_blocks or text_blocks[-1] != cell_text):
                        text_blocks.append(cell_text)
                        
    except Exception as e:
        print(f"python-docx failed to parse {file_path}: {e}")
        
    return "\n".join(text_blocks).strip()
