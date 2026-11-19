
import fitz


def extract_pdf(document):
    """
    Extract text and metadata from an uploaded PDF.
    """

    pdf_path = document.original_file.path

    pdf = fitz.open(pdf_path)

    extracted_pages = []

    for page_number, page in enumerate(pdf, start=1):

        page_data = {
            "page_number": page_number,
            "text": page.get_text("text"),
        }

        extracted_pages.append(page_data)

    result = {
        "filename": document.title,
        "total_pages": len(pdf),
        "metadata": pdf.metadata,
        "pages": extracted_pages,
    }

    pdf.close()

    return result
