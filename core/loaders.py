import re
import os
import pdfplumber
from pathlib import Path

def resolve_path(path_str: str) -> str:
    """
    Convert an environment path string into a platform-independent absolute path.
    """

    expanded = os.path.expandvars(os.path.expanduser(path_str))
    path = Path(expanded).resolve()

    return str(path)

def get_pdf_plumber_message(pdf_path: str) -> str:
    paragraphs = []
    with pdfplumber.open(resolve_path(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)  # Use layout mode for better text extraction
            if text:
                # Split into lines
                lines = text.split('\n')
                current_paragraph = []
                for i, line in enumerate(lines):
                    line = line.strip()
                    # Skip empty lines
                    if not line:
                        if current_paragraph:
                            # Join paragraph pieces
                            paragraph_text = ' '.join(current_paragraph)
                            paragraphs.append(paragraph_text)
                            current_paragraph = []
                        continue
                    # Check if this looks like a header (short, uppercase, ends with :, or numbered)
                    if (len(line) < 40 and (line.isupper() or line.endswith(':') or re.match(r'^\d+\.', line))):
                        # Save current paragraph if exists
                        if current_paragraph:
                            paragraph_text = ' '.join(current_paragraph)
                            paragraphs.append(paragraph_text)
                            current_paragraph = []
                        # Add the header as its own paragraph
                        paragraphs.append(line)
                    else:
                        # Add to current paragraph, joining single words properly
                        if len(line.split()) <= 2 and len(line) < 15 and current_paragraph:
                            # Join with the last element in current_paragraph
                            current_paragraph[-1] = current_paragraph[-1] + ' ' + line
                        else:
                            current_paragraph.append(line)
                # Save any remaining paragraph
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    paragraphs.append(paragraph_text)
    # Join paragraphs with double newlines
    text = '\n\n'.join(paragraphs)
    text = re.sub(r'[ \t]+', ' ', text)
    # Fix hyphenated word breaks
    text = re.sub(r'([a-z])-\s+([a-z])', r'\1\2', text)
    # Normalize bullet points
    text = re.sub(r'[•●○◦]', '•', text)
    # Clean up multiple newlines (more than 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()