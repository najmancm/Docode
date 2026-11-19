
from pypdf import PdfReader


def extract_pdf(document):
    """
    Extract text and metadata from an uploaded PDF.
    """

    pdf_path = document.original_file.path

    reader = PdfReader(pdf_path)

    extracted_pages = []

    for page_number, page in enumerate(reader.pages, start=1):

        page_data = {
            "page_number": page_number,
            "text": page.extract_text() or "",
        }

        extracted_pages.append(page_data)

    result = {
        "filename": document.title,
        "total_pages": len(reader.pages),
        "metadata": {
            "title": reader.metadata.title if reader.metadata else None,
            "author": reader.metadata.author if reader.metadata else None,
            "subject": reader.metadata.subject if reader.metadata else None,
        },
        "pages": extracted_pages,
    }

    return result
