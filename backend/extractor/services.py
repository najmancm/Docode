
from pathlib import Path
from django.conf import settings
from pypdf import PdfReader


def extract_pdf(document):
    """
    Extract text, metadata and images from an uploaded PDF.
    """

    pdf_path = document.original_file.path
    reader = PdfReader(pdf_path)

    extracted_pages = []

    # Create a separate folder for this document's images
    image_folder = (
        Path(settings.MEDIA_ROOT)
        / "extracted_images"
        / f"document_{document.id}"
    )

    image_folder.mkdir(parents=True, exist_ok=True)

    for page_number, page in enumerate(reader.pages, start=1):

        # Extract page text
        page_text = page.extract_text() or ""

        # Extract page images
        extracted_images = []

        for image_number, image in enumerate(page.images, start=1):

            extension = Path(image.name).suffix or ".bin"

            image_filename = (
                f"page_{page_number}_image_{image_number}{extension}"
            )

            image_path = image_folder / image_filename

            with open(image_path, "wb") as image_file:
                image_file.write(image.data)

            relative_path = image_path.relative_to(
                Path(settings.MEDIA_ROOT)
            )

            image_url = (
                settings.MEDIA_URL + relative_path.as_posix()
            )

            extracted_images.append({
                "filename": image_filename,
                "url": image_url,
            })

        extracted_pages.append({
            "page_number": page_number,
            "text": page_text,
            "images": extracted_images,
        })

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
