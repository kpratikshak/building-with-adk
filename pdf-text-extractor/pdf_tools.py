from pathlib import Path
import pdfplumber


def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract all text from a PDF.

    Returns plain text.
    """

    path = Path(pdf_path)

    if not path.exists():
        return "Error: PDF file not found."

    text = []

    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()

                if page_text:
                    text.append(page_text)

        return "\n\n".join(text)

    except Exception as ex:
        return f"Error extracting PDF: {ex}"
