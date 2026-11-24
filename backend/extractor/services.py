import base64
import io
import re
import shutil
from html import escape
from pathlib import Path

from PIL import Image as PILImage

from django.conf import settings
from django.contrib.staticfiles import finders

from docx import Document as WordDocument
from docx.document import Document as WordDocumentType
from docx.table import Table as WordTable
from docx.text.paragraph import Paragraph as WordParagraph
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pypdf import PdfReader


# =========================================================
# TELESOM ACADEMY - EIGHT TEMPLATES
# =========================================================

TEMPLATE_CATALOG = {
    "academy": {
        "name": "Academy",
        "description": "Structured educational lessons with clear learning sections.",
    },
    "editorial": {
        "name": "Editorial",
        "description": "Elegant reading experience inspired by professional publications.",
    },
    "interactive": {
        "name": "Interactive",
        "description": "Expandable lesson sections with interactive navigation.",
    },
    "presentation": {
        "name": "Presentation",
        "description": "Slide-based presentation with navigation and progress.",
    },
    "modern": {
        "name": "Modern",
        "description": "Contemporary cards, bold headings and clean visual hierarchy.",
    },
    "minimal": {
        "name": "Minimal",
        "description": "Distraction-free reading with generous spacing.",
    },
    "corporate": {
        "name": "Corporate",
        "description": "Professional company training and business documentation.",
    },
    "workbook": {
        "name": "Workbook",
        "description": "Study-focused sections, notes areas and structured content.",
    },
}


# =========================================================
# IMAGE STORAGE
# =========================================================

def _image_folder(document):
    folder = (
        Path(settings.MEDIA_ROOT)
        / "extracted_images"
        / f"document_{document.id}"
    )
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _normalize_image_bytes(data, preferred_extension=None):
    """Keep browser-supported original image formats unchanged."""

    try:
        with PILImage.open(io.BytesIO(data)) as image:
            image_format = (image.format or "").upper()

            if image_format == "JPEG":
                return data, "jpg"

            if image_format == "PNG":
                return data, "png"

            if image_format == "GIF":
                return data, "gif"

            if image_format == "WEBP":
                return data, "webp"

            if image_format == "BMP":
                output = io.BytesIO()
                image.convert("RGB").save(output, format="PNG")
                return output.getvalue(), "png"

            if image_format == "TIFF":
                output = io.BytesIO()
                image.seek(0)
                image.convert("RGBA").save(output, format="PNG")
                return output.getvalue(), "png"

    except Exception:
        pass

    extension = (preferred_extension or "bin").lower().lstrip(".")
    if extension == "jpeg":
        extension = "jpg"

    return data, extension


def _save_image(document, filename, data):
    folder = _image_folder(document)
    image_path = folder / filename
    image_path.write_bytes(data)

    relative_path = image_path.relative_to(Path(settings.MEDIA_ROOT))
    media_url = (settings.MEDIA_URL or "/media/").rstrip("/") + "/"

    return {
        "filename": filename,
        "url": media_url + relative_path.as_posix(),
    }


def _extract_and_save_image(document, filename, data, extension=None):
    normalized_data, normalized_extension = _normalize_image_bytes(
        data, extension
    )

    filename = (
        str(Path(filename).with_suffix(""))
        + "."
        + normalized_extension
    )

    return _save_image(document, filename, normalized_data)


# =========================================================
# TEXT EXTRACTION HELPERS
# =========================================================

def _clean_line(line):
    return (
        str(line or "")
        .replace("\x00", "")
        .replace("\u00a0", " ")
        .strip()
    )


def _is_extraction_artifact(line):
    value = str(line or "").strip()

    if not value:
        return True

    if re.fullmatch(r"Page\s+\d+\s+of\s+\d+", value, re.I):
        return True

    if re.fullmatch(r"\d{12,}", value):
        return True

    return False


def _text_to_blocks(text, page_number=None):
    blocks = []
    lines = [_clean_line(line) for line in (text or "").splitlines()]

    paragraph_lines = []
    list_items = []
    list_type = None

    def flush_paragraph():
        nonlocal paragraph_lines

        if paragraph_lines:
            value = " ".join(paragraph_lines).strip()
            if value:
                blocks.append({
                    "kind": "paragraph",
                    "text": value,
                    "page": page_number,
                })

        paragraph_lines = []

    def flush_list():
        nonlocal list_items, list_type

        if list_items:
            blocks.append({
                "kind": "list",
                "list_type": list_type or "unordered",
                "items": list_items[:],
                "page": page_number,
            })

        list_items = []
        list_type = None

    for line in lines:
        if _is_extraction_artifact(line):
            flush_paragraph()
            flush_list()
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)

        if heading:
            flush_paragraph()
            flush_list()
            blocks.append({
                "kind": "heading",
                "level": len(heading.group(1)),
                "text": heading.group(2).strip(),
                "page": page_number,
            })
            continue

        bullet = re.match(
            r"^\s*(?:[-*\u2022\u25aa\u25e6\u2023]|\bo)\s+(.+)$",
            line,
            re.I,
        )

        if bullet:
            flush_paragraph()

            if list_type != "unordered":
                flush_list()

            list_type = "unordered"
            list_items.append(bullet.group(1).strip())
            continue

        numbered = re.match(r"^\s*(\d+)[.)]\s+(.+)$", line)

        if numbered:
            flush_paragraph()

            if list_type != "ordered":
                flush_list()

            list_type = "ordered"
            list_items.append(numbered.group(2).strip())
            continue

        flush_list()

        if not line:
            flush_paragraph()
            continue

        paragraph_lines.append(line)

    flush_paragraph()
    flush_list()

    return blocks


# =========================================================
# WORD DOCUMENT EXTRACTION
# =========================================================

def _iter_word_blocks(parent):
    if isinstance(parent, WordDocumentType):
        parent_element = parent.element.body
    else:
        parent_element = parent._tc

    for child in parent_element.iterchildren():
        if isinstance(child, CT_P):
            yield WordParagraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield WordTable(child, parent)


def _word_table_rows(table):
    return [
        [cell.text for cell in row.cells]
        for row in table.rows
    ]


def _extract_word_paragraph_images(
    document,
    word_document,
    paragraph,
    page_number=1,
    image_counter=None,
):
    images = []

    if image_counter is None:
        image_counter = {"value": 0}

    try:
        blips = paragraph._p.xpath(".//a:blip")

        for blip in blips:
            relationship_id = blip.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
            )

            if not relationship_id:
                continue

            relationship = word_document.part.related_parts.get(
                relationship_id
            )

            if not relationship or not hasattr(relationship, "blob"):
                continue

            image_counter["value"] += 1

            image_bytes = relationship.blob
            content_type = getattr(
                relationship, "content_type", "image/png"
            )
            extension = content_type.split("/")[-1]

            saved = _extract_and_save_image(
                document,
                f"word_image_{image_counter['value']}.{extension}",
                image_bytes,
                extension,
            )

            images.append({
                **saved,
                "page": page_number,
            })

    except Exception:
        pass

    return images


def _docx_style_name(paragraph):
    return paragraph.style.name.lower() if paragraph.style else ""


def _docx_heading_level(paragraph):
    match = re.search(r"heading\s*(\d+)", _docx_style_name(paragraph))
    return max(1, min(int(match.group(1)), 6)) if match else None


def _docx_list_type(paragraph):
    name = _docx_style_name(paragraph)
    properties = paragraph._p.pPr
    has_numbering = properties is not None and properties.numPr is not None

    if "list number" in name:
        return "ordered"

    if "list bullet" in name or name.startswith("list") or has_numbering:
        return "unordered"

    return None


def extract_docx(document):
    word_document = WordDocument(document.original_file.path)
    items = list(_iter_word_blocks(word_document))

    levels = {
        _docx_heading_level(item)
        for item in items
        if isinstance(item, WordParagraph) and item.text.strip()
    }
    levels.discard(None)
    split_level = 1 if 1 in levels else (2 if 2 in levels else None)

    pages = []
    image_counter = {"value": 0}

    def new_page():
        page = {
            "page_number": len(pages) + 1,
            "text": "",
            "blocks": [],
            "images": [],
        }
        pages.append(page)
        return page

    current = new_page()

    for item in items:
        if isinstance(item, WordParagraph):
            text = item.text
            level = _docx_heading_level(item) if text.strip() else None

            if split_level and level == split_level and current["blocks"]:
                current = new_page()

            number = current["page_number"]
            blocks = current["blocks"]

            if text.strip():
                if level:
                    blocks.append({
                        "kind": "heading",
                        "level": level,
                        "text": text,
                        "page": number,
                    })
                else:
                    list_type = _docx_list_type(item)
                    last = blocks[-1] if blocks else None

                    if list_type:
                        if (
                            last
                            and last["kind"] == "list"
                            and last["list_type"] == list_type
                        ):
                            last["items"].append(text)
                        else:
                            blocks.append({
                                "kind": "list",
                                "list_type": list_type,
                                "items": [text],
                                "page": number,
                            })
                    else:
                        blocks.append({
                            "kind": "paragraph",
                            "text": text,
                            "page": number,
                        })

            for image in _extract_word_paragraph_images(
                document, word_document, item, number, image_counter
            ):
                current["images"].append(image)
                blocks.append({
                    "kind": "image",
                    "url": image["url"],
                    "filename": image["filename"],
                    "page": number,
                })

        elif isinstance(item, WordTable):
            current["blocks"].append({
                "kind": "table",
                "rows": _word_table_rows(item),
                "page": current["page_number"],
            })

    for page in pages:
        parts = []

        for block in page["blocks"]:
            if block["kind"] in ("heading", "paragraph"):
                parts.append(block["text"])
            elif block["kind"] == "list":
                parts.extend(block["items"])
            elif block["kind"] == "table":
                parts.extend(
                    " | ".join(str(cell) for cell in row)
                    for row in block["rows"]
                )

        page["text"] = "\n".join(parts)

    return {
        "filename": document.title,
        "format": "docx",
        "total_pages": len(pages),
        "metadata": {},
        "pages": pages,
    }


# =========================================================
# PDF EXTRACTION
# =========================================================

def extract_pdf(document):
    reader = PdfReader(document.original_file.path)
    extracted_pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        blocks = _text_to_blocks(page_text, page_number)
        images = []

        try:
            page_images = page.images
        except Exception:
            page_images = []

        for image_number, image in enumerate(page_images, start=1):
            extension = (
                Path(image.name).suffix.lower().lstrip(".") or "png"
            )

            saved = _extract_and_save_image(
                document,
                f"pdf_page_{page_number}_image_{image_number}.{extension}",
                image.data,
                extension,
            )

            images.append({
                **saved,
                "page": page_number,
            })

        extracted_pages.append({
            "page_number": page_number,
            "text": page_text,
            "blocks": blocks,
            "images": images,
        })

    metadata = reader.metadata

    return {
        "filename": document.title,
        "format": "pdf",
        "total_pages": len(reader.pages),
        "metadata": {
            "title": metadata.title if metadata else None,
            "author": metadata.author if metadata else None,
            "subject": metadata.subject if metadata else None,
        },
        "pages": extracted_pages,
    }


# =========================================================
# POWERPOINT EXTRACTION
# =========================================================

def _powerpoint_table_rows(table):
    return [
        [cell.text for cell in row.cells]
        for row in table.rows
    ]


def _walk_shapes(shapes):
    """Yield every shape, including the ones inside groups."""

    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _walk_shapes(shape.shapes)
        else:
            yield shape


def _is_title_shape(shape):
    try:
        return shape.is_placeholder and shape.placeholder_format.type in (
            PP_PLACEHOLDER.TITLE,
            PP_PLACEHOLDER.CENTER_TITLE,
        )
    except Exception:
        return False


def extract_pptx(document):
    presentation = Presentation(document.original_file.path)

    extracted_pages = []
    slide_width = presentation.slide_width
    slide_height = presentation.slide_height

    for slide_number, slide in enumerate(presentation.slides, start=1):
        parts = []
        blocks = []
        images = []
        elements = []
        image_number = 0

        for shape_order, shape in enumerate(
            _walk_shapes(slide.shapes), start=1
        ):
            if None in (shape.left, shape.top, shape.width, shape.height):
                continue

            position = {
                "left": round(shape.left / slide_width * 100, 4),
                "top": round(shape.top / slide_height * 100, 4),
                "width": round(shape.width / slide_width * 100, 4),
                "height": round(shape.height / slide_height * 100, 4),
                "order": shape_order,
            }

            if getattr(shape, "has_table", False):
                rows = _powerpoint_table_rows(shape.table)

                elements.append({
                    "kind": "table",
                    "position": position,
                    "rows": rows,
                })

                blocks.append({
                    "kind": "table",
                    "rows": rows,
                    "page": slide_number,
                })

                parts.append(
                    "\n".join(" | ".join(row) for row in rows)
                )

            elif hasattr(shape, "image"):
                try:
                    picture = shape.image
                    picture_blob = picture.blob
                    picture_ext = picture.ext
                except Exception:
                    continue

                image_number += 1

                saved = _extract_and_save_image(
                    document,
                    f"slide_{slide_number}_image_{image_number}.{picture_ext}",
                    picture_blob,
                    picture_ext,
                )

                images.append({
                    **saved,
                    "position": position,
                    "page": slide_number,
                })

                elements.append({
                    "kind": "image",
                    "position": position,
                    "url": saved["url"],
                    "filename": saved["filename"],
                })

                blocks.append({
                    "kind": "image",
                    "url": saved["url"],
                    "filename": saved["filename"],
                    "page": slide_number,
                })

            elif getattr(shape, "has_text_frame", False):
                paragraphs = []
                font_sizes = []

                for paragraph in shape.text_frame.paragraphs:
                    if paragraph.text.strip():
                        paragraphs.append(paragraph.text)

                    for run in paragraph.runs:
                        if run.font.size:
                            font_sizes.append(run.font.size.pt)

                if paragraphs:
                    text_value = "\n".join(paragraphs)

                    average_font_size = (
                        sum(font_sizes) / len(font_sizes)
                        if font_sizes else 18
                    )

                    elements.append({
                        "kind": "text",
                        "position": position,
                        "text": text_value,
                        "font_size_pt": round(average_font_size, 2),
                    })

                    parts.append(text_value)

                    # One block per paragraph: the teacher's lines are
                    # never merged together.
                    is_title = _is_title_shape(shape)

                    for paragraph_text in paragraphs:
                        blocks.append({
                            "kind": "heading" if is_title else "paragraph",
                            "level": 2,
                            "text": paragraph_text,
                            "page": slide_number,
                        })

        extracted_pages.append({
            "page_number": slide_number,
            "text": "\n".join(parts),
            "blocks": blocks,
            "images": images,
            "elements": elements,
        })

    return {
        "filename": document.title,
        "format": "pptx",
        "total_pages": len(presentation.slides),
        "slide_width": slide_width,
        "slide_height": slide_height,
        "metadata": {},
        "pages": extracted_pages,
    }


# =========================================================
# MAIN EXTRACTION ROUTER
# =========================================================

def extract_document(document):
    extension = Path(document.original_file.name).suffix.lower()

    if extension not in (".pdf", ".pptx", ".docx"):
        if extension in (".ppt", ".doc"):
            raise ValueError(
                f"The {extension} format is not supported directly. "
                "Save the file as PPTX or DOCX first."
            )

        raise ValueError(
            "Unsupported document format. "
            "Supported formats: PDF, PPTX and DOCX."
        )

    old_folder = (
        Path(settings.MEDIA_ROOT)
        / "extracted_images"
        / f"document_{document.id}"
    )

    if old_folder.exists():
        shutil.rmtree(old_folder)

    if extension == ".pdf":
        return extract_pdf(document)

    if extension == ".pptx":
        return extract_pptx(document)

    return extract_docx(document)


# =========================================================
# CONTENT NORMALIZATION AND RENDERING
# =========================================================

def _page_blocks(page):
    if page.get("blocks"):
        return page["blocks"]

    return _text_to_blocks(
        page.get("text", ""),
        page.get("page_number"),
    )


def _all_blocks(extracted_data):
    blocks = []

    for page in extracted_data.get("pages", []):
        page_number = page.get("page_number")
        page_content = _page_blocks(page)

        for block in page_content:
            item = dict(block)
            item.setdefault("page", page_number)
            blocks.append(item)

        existing_images = {
            block.get("url")
            for block in page_content
            if block.get("kind") == "image"
        }

        for image in page.get("images", []):
            if image.get("url") not in existing_images:
                blocks.append({
                    "kind": "image",
                    "url": image.get("url", ""),
                    "filename": image.get("filename", ""),
                    "page": page_number,
                })

    return blocks


def _render_blocks(blocks):
    output = []

    for block in blocks:
        kind = block.get("kind")

        if kind == "heading":
            level = max(1, min(int(block.get("level") or 2), 6))
            content = escape(str(block.get("text", "")))
            output.append(f"<h{level}>{content}</h{level}>")

        elif kind == "paragraph":
            content = escape(str(block.get("text", "")))
            output.append(f"<p>{content}</p>")

        elif kind == "list":
            tag = (
                "ol"
                if block.get("list_type") == "ordered"
                else "ul"
            )

            items = "".join(
                f"<li>{escape(str(item))}</li>"
                for item in block.get("items", [])
            )

            output.append(
                f'<{tag} class="content-list">{items}</{tag}>'
            )

        elif kind == "table":
            rows = []

            for row_index, row in enumerate(block.get("rows", [])):
                tag = "th" if row_index == 0 else "td"
                cells = "".join(
                    f"<{tag}>{escape(str(cell))}</{tag}>"
                    for cell in row
                )
                rows.append(f"<tr>{cells}</tr>")

            output.append(
                '<div class="table-wrap"><table><tbody>'
                + "".join(rows)
                + "</tbody></table></div>"
            )

        elif kind == "image":
            url = escape(str(block.get("url", "")))

            if url:
                filename = escape(str(block.get("filename", "")))
                output.append(
                    f"""
                    <figure class="document-image">
                        <img src="{url}" alt="{filename}" loading="lazy">
                    </figure>
                    """
                )

    return "".join(output)


# =========================================================
# TELESOM ACADEMY LOGO
# =========================================================

def _find_brand_logo():
    candidates = []

    try:
        found = finders.find("brand/telesom-academy-logo.png")
        if found:
            candidates.append(Path(found))
    except Exception:
        pass

    candidates.extend([
        Path(settings.BASE_DIR) / "static" / "brand" / "telesom-academy-logo.png",
        Path(settings.BASE_DIR) / "staticfiles" / "brand" / "telesom-academy-logo.png",
    ])

    static_root = getattr(settings, "STATIC_ROOT", None)

    if static_root:
        candidates.append(
            Path(static_root) / "brand" / "telesom-academy-logo.png"
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def _embedded_brand_logo_src():
    logo_path = _find_brand_logo()

    if not logo_path:
        return ""

    encoded = base64.b64encode(
        logo_path.read_bytes()
    ).decode("ascii")

    return "data:image/png;base64," + encoded


def _brand_markup():
    logo = _embedded_brand_logo_src()

    if logo:
        return (
            f'<img class="brand-logo" src="{logo}" '
            'alt="Telesom Academy">'
        )

    return (
        '<div class="brand-wordmark">'
        '<span>TELESOM</span> ACADEMY'
        '</div>'
    )


# =========================================================
# SHARED CSS - BRAND AND RESPONSIVENESS
# =========================================================

def _base_css():
    return """
    :root {
        --green: #31B44A;
        --green-dark: #2e7a00;
        --green-light: #eaf5e0;
        --gold: #D7982F;
        --gold-dark: #aa841c;
        --ink: #1d2922;
        --muted: #68766d;
        --line: #dfe8e1;
        --surface: #ffffff;
        --background: #f5f8f5;
    }

    * { box-sizing: border-box; }

    html { scroll-behavior: smooth; }

    body {
        margin: 0;
        color: var(--ink);
        background: var(--background);
        font-family: Inter, "Segoe UI", Arial, sans-serif;
        line-height: 1.75;
    }

    img {
        display: block;
        max-width: 100%;
        height: auto;
    }

    h1, h2, h3, h4, h5, h6 {
        color: var(--green-dark);
        line-height: 1.35;
        overflow-wrap: anywhere;
    }

    p {
        margin: 0 0 1.2em;
        overflow-wrap: anywhere;
    }

    ul, ol {
        padding-left: 1.7em;
        margin: 0 0 1.4em;
    }

    li { margin-bottom: .5em; }

    .content-list { line-height: 1.8; }

    .table-wrap {
        width: 100%;
        overflow-x: auto;
        margin: 24px 0;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: white;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        min-width: 360px;
    }

    td, th {
        border-bottom: 1px solid var(--line);
        padding: 13px 15px;
        text-align: left;
        vertical-align: top;
    }

    th {
        color: var(--green-dark);
        background: var(--green-light);
        font-weight: 700;
    }

    tr:nth-child(even) td { background: #f9fbf9; }

    .document-image {
        margin: 28px auto;
        max-width: 100%;
        text-align: center;
    }

    .document-image img {
        display: inline-block;
        width: auto;
        max-width: 100%;
        height: auto;
        object-fit: contain;
    }

    .brand-header {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 16px;
        background: white;
        border-bottom: 1px solid var(--line);
    }

    .brand-logo {
        height: 64px;
        width: auto;
        max-width: 80%;
        object-fit: contain;
    }

    .brand-wordmark {
        color: var(--green-dark);
        font-weight: 900;
        letter-spacing: 1.5px;
        font-size: 16px;
    }

    .brand-wordmark span { color: var(--green); }

    .academy-footer {
        text-align: center;
        color: var(--muted);
        font-size: 11px;
        letter-spacing: 1.3px;
        padding: 25px 15px;
        border-top: 1px solid var(--line);
        margin-top: 35px;
    }

    @media(max-width: 600px) {
        .brand-header { padding: 12px; }
        .brand-logo { height: 52px; }
        td, th { padding: 9px; }
    }
    """


# =========================================================
# TEMPLATE-SPECIFIC CSS
# =========================================================

def _academy_css():
    return """
    .academy-page {
        max-width: 1050px;
        margin: 35px auto;
        padding: 0 24px 60px;
    }

    .academy-cover {
        padding: 48px;
        margin-bottom: 25px;
        border-radius: 18px;
        background: linear-gradient(125deg, #2e7a00, #31B44A);
        color: white;
        box-shadow: 0 14px 35px rgba(46,122,0,.13);
    }

    .academy-cover .eyebrow {
        color: #e6f7d9;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 2px;
    }

    .academy-cover h1 {
        color: white;
        font-size: clamp(28px, 5vw, 43px);
        margin: 14px 0 0;
    }

    .academy-content {
        padding: clamp(24px, 5vw, 55px);
        background: white;
        border: 1px solid var(--line);
        border-radius: 16px;
        box-shadow: 0 8px 30px rgba(20,50,25,.04);
    }

    .academy-content h2 {
        margin-top: 38px;
        padding-bottom: 10px;
        border-bottom: 2px solid var(--green-light);
    }

    .academy-content h2:first-child { margin-top: 0; }
    .academy-content h3 { margin-top: 26px; }

    @media(max-width: 600px) {
        .academy-page { margin: 18px auto; padding: 0 12px 35px; }
        .academy-cover { padding: 27px 22px; }
        .academy-content { padding: 22px 17px; }
    }
    """


def _editorial_css():
    return """
    body.template-editorial {
        background: #faf9f6;
        color: #302f2a;
        font-family: Georgia, "Times New Roman", serif;
    }

    .editorial-topline {
        height: 5px;
        background: linear-gradient(90deg, #31B44A 0 75%, #D7982F 75%);
    }

    .editorial-header {
        max-width: 900px;
        margin: 0 auto;
        padding: 38px 30px 25px;
        border-bottom: 1px solid #e4dfd4;
    }

    .editorial-header .brand-logo { margin-bottom: 30px; }

    .editorial-kicker {
        color: #8b7b55;
        font-family: Arial, sans-serif;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 2px;
    }

    .editorial-header h1 {
        color: #252c25;
        font-family: Georgia, serif;
        font-size: clamp(32px, 5vw, 54px);
        font-weight: 500;
        line-height: 1.13;
        margin: 15px 0;
    }

    .editorial-rule {
        width: 65px;
        height: 3px;
        background: #D7982F;
        margin-top: 25px;
    }

    .editorial-content {
        max-width: 780px;
        margin: 0 auto;
        padding: 42px 30px 90px;
        font-size: 18px;
        line-height: 1.95;
    }

    .editorial-content h2 {
        margin: 52px 0 20px;
        color: #2e7a00;
        font-family: Georgia, serif;
        font-size: 29px;
        font-weight: 500;
    }

    .editorial-content h3 {
        margin-top: 35px;
        color: #746039;
        font-family: Georgia, serif;
        font-size: 22px;
    }

    .editorial-content p { margin-bottom: 1.6em; }

    .editorial-content .document-image {
        margin: 38px auto;
        padding: 12px;
        background: white;
        border: 1px solid #e9e3d8;
    }

    @media(max-width: 600px) {
        .editorial-header { padding: 25px 19px; }
        .editorial-content { padding: 27px 19px 60px; font-size: 16px; }
        .editorial-content h2 { font-size: 25px; }
    }
    """


def _interactive_css():
    return """
    body.template-interactive { background: #f1f7f1; }

    .interactive-header {
        padding: 18px 24px;
        background: white;
        border-bottom: 1px solid var(--line);
    }

    .interactive-header-inner {
        max-width: 1100px;
        margin: auto;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 20px;
    }

    .interactive-header h1 {
        margin: 0;
        font-size: clamp(23px, 4vw, 35px);
    }

    .interactive-header .brand-logo { height: 54px; }

    .interactive-wrap {
        display: grid;
        grid-template-columns: 245px minmax(0, 1fr);
        gap: 25px;
        max-width: 1150px;
        margin: 35px auto;
        padding: 0 22px 60px;
    }

    .interactive-index {
        position: sticky;
        top: 20px;
        align-self: start;
        padding: 20px;
        background: white;
        border: 1px solid var(--line);
        border-radius: 13px;
    }

    .interactive-index h3 {
        margin: 0 0 15px;
        font-size: 12px;
        letter-spacing: 1px;
    }

    .interactive-index a {
        display: block;
        padding: 9px 10px;
        margin: 4px 0;
        color: #526157;
        font-size: 12px;
        text-decoration: none;
        border-radius: 7px;
    }

    .interactive-index a:hover {
        background: var(--green-light);
        color: var(--green-dark);
    }

    .interactive-section {
        margin-bottom: 14px;
        padding: 22px 25px;
        background: white;
        border: 1px solid var(--line);
        border-radius: 13px;
        box-shadow: 0 5px 18px rgba(20,50,25,.035);
    }

    .interactive-section summary {
        display: flex;
        align-items: center;
        gap: 13px;
        cursor: pointer;
        list-style: none;
        color: var(--green-dark);
        font-size: 18px;
        font-weight: 800;
    }

    .interactive-section summary::-webkit-details-marker { display: none; }

    .interactive-section summary::after {
        content: "+";
        margin-left: auto;
        color: var(--gold-dark);
        font-size: 23px;
    }

    .interactive-section[open] summary::after { content: "\\2212"; }

    .section-number {
        display: grid;
        place-items: center;
        flex: 0 0 34px;
        height: 34px;
        border-radius: 9px;
        background: var(--green-light);
        color: var(--green-dark);
        font-size: 12px;
    }

    .interactive-section-content {
        padding-top: 23px;
        border-top: 1px solid var(--line);
        margin-top: 19px;
    }

    .interactive-tools {
        display: flex;
        justify-content: flex-end;
        gap: 9px;
        margin-bottom: 15px;
    }

    .interactive-tools button {
        padding: 9px 13px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: white;
        color: var(--green-dark);
        cursor: pointer;
        font-weight: 700;
    }

    @media(max-width: 750px) {
        .interactive-wrap {
            grid-template-columns: 1fr;
            margin-top: 18px;
            padding: 0 13px 35px;
            gap: 15px;
        }

        .interactive-index { position: static; }

        .interactive-index nav {
            display: flex;
            overflow-x: auto;
            gap: 5px;
        }

        .interactive-index a {
            flex: 0 0 auto;
            white-space: nowrap;
        }

        .interactive-header-inner { flex-wrap: wrap; }
        .interactive-section { padding: 17px; }
    }
    """


def _modern_css():
    return """
    body.template-modern {
        background: #f2f6f3;
    }

    .modern-page {
        max-width: 1120px;
        margin: 35px auto;
        padding: 0 24px 60px;
    }

    .modern-hero {
        position: relative;
        overflow: hidden;
        padding: clamp(30px, 6vw, 65px);
        color: white;
        border-radius: 22px;
        background: linear-gradient(120deg, #176d2b, #31B44A);
    }

    .modern-hero:after {
        content: "";
        position: absolute;
        width: 230px;
        height: 230px;
        border: 35px solid rgba(255,255,255,.10);
        border-radius: 50%;
        right: -65px;
        bottom: -100px;
    }

    .modern-hero h1 {
        color: white;
        max-width: 780px;
        font-size: clamp(30px, 5vw, 48px);
        line-height: 1.2;
        margin: 20px 0 0;
    }

    .modern-label {
        color: #f9e5bd;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 2px;
    }

    .modern-content {
        display: grid;
        grid-template-columns: minmax(0, 1fr);
        gap: 18px;
        margin-top: 22px;
    }

    .modern-content > h2,
    .modern-content > h3 {
        margin-bottom: 0;
    }

    .modern-content > p,
    .modern-content > ul,
    .modern-content > ol,
    .modern-content > .table-wrap,
    .modern-content > .document-image {
        background: white;
        padding: 23px;
        border: 1px solid var(--line);
        border-radius: 13px;
        margin: 0;
    }

    .modern-content > h2 {
        background: white;
        padding: 18px 22px;
        border-left: 5px solid var(--gold);
        border-radius: 9px;
    }

    @media(max-width: 600px) {
        .modern-page { padding: 0 13px 35px; }
        .modern-content > p,
        .modern-content > ul,
        .modern-content > ol { padding: 17px; }
    }
    """


def _minimal_css():
    return """
    body.template-minimal {
        background: #ffffff;
        color: #303a33;
    }

    .minimal-header {
        max-width: 850px;
        margin: auto;
        padding: 35px 30px 28px;
        border-bottom: 1px solid #edf0ed;
    }

    .minimal-header .brand-logo { height: 58px; margin-bottom: 30px; }

    .minimal-header h1 {
        font-size: clamp(29px, 4.5vw, 44px);
        font-weight: 650;
        color: #1f3827;
        margin: 0;
        line-height: 1.2;
    }

    .minimal-content {
        max-width: 780px;
        margin: auto;
        padding: 38px 30px 80px;
        font-size: 17px;
        line-height: 1.9;
    }

    .minimal-content h2 {
        font-size: 25px;
        margin-top: 44px;
        color: #2e7a00;
    }

    .minimal-content h3 {
        font-size: 20px;
        margin-top: 30px;
    }

    .minimal-content .document-image {
        margin: 35px auto;
    }

    @media(max-width: 600px) {
        .minimal-header { padding: 25px 18px; }
        .minimal-content { padding: 27px 18px 55px; font-size: 16px; }
    }
    """


def _corporate_css():
    return """
    body.template-corporate {
        background: #f3f6f4;
    }

    .corporate-banner {
        background: #174d2a;
        color: white;
        padding: 20px 25px;
    }

    .corporate-banner-inner {
        max-width: 1100px;
        margin: auto;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 20px;
    }

    .corporate-banner .brand-logo {
        height: 56px;
        width: auto;
        padding: 6px 10px;
        background: white;
        border-radius: 10px;
    }

    .corporate-banner .brand-wordmark { color: white; }
    .corporate-banner .brand-wordmark span { color: #9ee2a8; }

    .corporate-label {
        color: #e8d2a3;
        font-size: 11px;
        letter-spacing: 2px;
        font-weight: 800;
    }

    .corporate-title {
        max-width: 1100px;
        margin: 35px auto 20px;
        padding: 0 25px;
    }

    .corporate-title h1 {
        font-size: clamp(29px, 4.5vw, 44px);
        margin: 0;
    }

    .corporate-content {
        max-width: 1100px;
        margin: 0 auto 55px;
        padding: 38px;
        background: white;
        border: 1px solid var(--line);
        border-top: 4px solid var(--gold);
        box-shadow: 0 8px 30px rgba(20,50,25,.04);
    }

    .corporate-content h2 {
        padding-bottom: 10px;
        border-bottom: 1px solid var(--line);
        margin-top: 38px;
    }

    @media(max-width: 600px) {
        .corporate-banner { padding: 14px; }
        .corporate-banner-inner { flex-wrap: wrap; }
        .corporate-content { margin: 0 12px 35px; padding: 20px; }
        .corporate-title { margin-top: 25px; padding: 0 15px; }
    }
    """


def _workbook_css():
    return """
    body.template-workbook {
        background: #f6f8f4;
    }

    .workbook-page {
        max-width: 1000px;
        margin: 30px auto;
        padding: 0 22px 55px;
    }

    .workbook-cover {
        background: white;
        padding: 35px;
        border: 1px solid var(--line);
        border-top: 6px solid var(--green);
        border-radius: 12px;
        margin-bottom: 20px;
    }

    .workbook-cover .brand-logo { height: 58px; margin-bottom: 22px; }

    .workbook-cover h1 {
        font-size: clamp(28px, 4vw, 42px);
        margin: 0;
    }

    .workbook-content {
        background: white;
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: clamp(20px, 4vw, 42px);
    }

    .workbook-content h2 {
        background: #eaf5e0;
        padding: 13px 17px;
        border-left: 4px solid var(--green);
        border-radius: 7px;
        margin-top: 36px;
    }

    .workbook-content h3 { color: #946a20; }

    .workbook-content li { padding-left: 5px; }

    .workbook-notes {
        margin-top: 35px;
        padding: 18px;
        border: 1px dashed #b8c9b9;
        border-radius: 9px;
        color: #68766d;
        font-size: 13px;
    }

    .workbook-notes strong {
        display: block;
        color: var(--green-dark);
        margin-bottom: 35px;
    }

    @media(max-width: 600px) {
        .workbook-page { padding: 0 12px 35px; }
        .workbook-cover { padding: 22px; }
    }
    """


# =========================================================
# SHARED DOCUMENT SHELL
# =========================================================

def _document_shell(title, body, css="", template_key="academy"):
    safe_title = escape(str(title or "TELESOM ACADEMY"))
    safe_template = escape(str(template_key))

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#31B44A">
    <title>{safe_title}</title>
    <style>
        {_base_css()}
        {css}
    </style>
</head>
<body class="template-{safe_template}">
    {body}
</body>
</html>"""


# =========================================================
# DOCUMENT TITLES
# =========================================================

def _document_title(document):
    return str(document.title or "TELESOM ACADEMY")


def _page_title(page, index):
    for block in _page_blocks(page):
        if block.get("kind") == "heading":
            title = str(block.get("text", "")).strip()
            if title:
                return title[:100]

    text = str(page.get("text", "")).strip()

    if text:
        return text.splitlines()[0][:100]

    return f"Lesson section {index}"


# =========================================================
# ACADEMY TEMPLATE
# =========================================================

def _generate_academy_html(document, extracted_data):
    content = _render_blocks(_all_blocks(extracted_data))

    body = f"""
    <header class="brand-header">{_brand_markup()}</header>

    <main class="academy-page">
        <section class="academy-cover">
            <div class="eyebrow">TELESOM ACADEMY &middot; LEARNING MATERIAL</div>
            <h1>{escape(_document_title(document))}</h1>
        </section>

        <article class="academy-content">{content}</article>

        <footer class="academy-footer">TELESOM ACADEMY</footer>
    </main>
    """

    return _document_shell(
        document.title, body, _academy_css(), "academy"
    )


# =========================================================
# EDITORIAL TEMPLATE
# =========================================================

def _generate_editorial_html(document, extracted_data):
    content = _render_blocks(_all_blocks(extracted_data))

    body = f"""
    <div class="editorial-topline"></div>

    <header class="editorial-header">
        {_brand_markup()}
        <div class="editorial-kicker">TELESOM ACADEMY &middot; STUDY EDITION</div>
        <h1>{escape(_document_title(document))}</h1>
        <div class="editorial-rule"></div>
    </header>

    <main class="editorial-content">{content}</main>

    <footer class="academy-footer">TELESOM ACADEMY</footer>
    """

    return _document_shell(
        document.title, body, _editorial_css(), "editorial"
    )


# =========================================================
# INTERACTIVE TEMPLATE
# =========================================================

def _generate_interactive_html(document, extracted_data):
    pages = extracted_data.get("pages", [])

    if not pages:
        raise ValueError("No document content was extracted.")

    sections = []
    navigation = []

    for index, page in enumerate(pages, start=1):
        title = _page_title(page, index)
        content = _render_blocks(_page_blocks(page))
        section_id = f"interactive-section-{index}"

        if not content.strip():
            content = "<p>No readable content was extracted.</p>"

        opened = "open" if index == 1 else ""

        sections.append(
            f"""
            <details class="interactive-section"
                     id="{section_id}" {opened}>
                <summary>
                    <span class="section-number">{index:02d}</span>
                    <span>{escape(title)}</span>
                </summary>
                <div class="interactive-section-content">
                    {content}
                </div>
            </details>
            """
        )

        navigation.append(
            f'<a href="#{section_id}">{index:02d} &middot; {escape(title)}</a>'
        )

    body = f"""
    <header class="interactive-header">
        <div class="interactive-header-inner">
            {_brand_markup()}
            <h1>{escape(_document_title(document))}</h1>
        </div>
    </header>

    <main class="interactive-wrap">
        <aside class="interactive-index">
            <h3>LESSON SECTIONS</h3>
            <nav>{''.join(navigation)}</nav>
        </aside>

        <section>
            <div class="interactive-tools">
                <button type="button" id="expand-all">Expand all</button>
                <button type="button" id="collapse-all">Collapse all</button>
            </div>
            {''.join(sections)}
        </section>
    </main>

    <script>
    (() => {{
        const sections = Array.from(
            document.querySelectorAll(".interactive-section")
        );

        document.getElementById("expand-all").addEventListener("click", () => {{
            sections.forEach(section => {{ section.open = true; }});
        }});

        document.getElementById("collapse-all").addEventListener("click", () => {{
            sections.forEach(section => {{ section.open = false; }});
        }});

        document.querySelectorAll(".interactive-index a").forEach(link => {{
            link.addEventListener("click", () => {{
                const target = document.querySelector(link.getAttribute("href"));
                if (target) target.open = true;
            }});
        }});
    }})();
    </script>
    """

    return _document_shell(
        document.title, body, _interactive_css(), "interactive"
    )


# =========================================================
# PRESENTATION TEMPLATE - POWERPOINT SUPPORT
# =========================================================

def _presentation_css(slide_width, slide_height):
    try:
        width = max(1, int(slide_width))
        height = max(1, int(slide_height))
    except (TypeError, ValueError):
        width, height = 16, 9

    return f"""
    body.template-presentation {{ background: #edf2ed; }}

    .deck-header {{
        min-height: 72px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
        padding: 8px 25px;
        background: white;
        border-bottom: 1px solid #dfe8e1;
    }}

    .deck-brand {{
        display: flex;
        align-items: center;
        gap: 12px;
        color: #2e7a00;
        font-weight: 800;
        letter-spacing: 1px;
        font-size: 12px;
    }}

    .deck-brand .brand-logo {{
        height: 52px;
        width: auto;
        object-fit: contain;
    }}

    .deck-document-title {{
        font-size: 13px;
        color: #68766d;
        text-align: right;
    }}

    .deck-shell {{
        display: grid;
        grid-template-columns: 260px minmax(0,1fr);
        max-width: 1650px;
        margin: auto;
        min-height: calc(100vh - 72px);
    }}

    .deck-sidebar {{
        background: white;
        border-right: 1px solid #dfe8e1;
        padding: 20px 13px;
        height: calc(100vh - 72px);
        position: sticky;
        top: 0;
        overflow-y: auto;
    }}

    .sidebar-heading {{
        display: flex;
        justify-content: space-between;
        gap: 8px;
        padding: 5px 8px 17px;
        font-size: 11px;
        font-weight: 800;
        color: #68766d;
    }}

    .sidebar-heading strong {{ color: #2e7a00; }}

    .slide-list {{
        display: flex;
        flex-direction: column;
        gap: 5px;
    }}

    .slide-nav-item {{
        width: 100%;
        display: flex;
        align-items: center;
        gap: 11px;
        padding: 10px;
        border: 0;
        border-radius: 8px;
        background: transparent;
        text-align: left;
        cursor: pointer;
        color: #58675e;
        font-size: 12px;
    }}

    .slide-nav-item:hover {{ background: #f1f8f1; }}

    .slide-nav-item.active {{
        background: #eaf5e0;
        color: #2e7a00;
        font-weight: 800;
    }}

    .nav-number {{
        flex: 0 0 30px;
        height: 30px;
        display: grid;
        place-items: center;
        background: #f0f3f0;
        border-radius: 7px;
    }}

    .slide-nav-item.active .nav-number {{
        background: #31B44A;
        color: white;
    }}

    .nav-title {{
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }}

    .deck-main {{ min-width: 0; padding: 25px; }}

    .deck-progress {{
        display: flex;
        align-items: center;
        gap: 15px;
        max-width: 1100px;
        margin: 0 auto 15px;
        color: #68766d;
        font-size: 12px;
    }}

    .progress-track {{
        flex: 1;
        height: 5px;
        overflow: hidden;
        border-radius: 10px;
        background: #dfe8e1;
    }}

    .progress-fill {{
        height: 100%;
        width: 0;
        background: #31B44A;
        transition: width .25s;
    }}

    .deck-stage {{ max-width: 1100px; margin: auto; }}

    .deck-slide {{
        display: none;
        width: 100%;
        aspect-ratio: {width} / {height};
        position: relative;
        overflow: hidden;
        background: white;
        border: 1px solid #dfe8e1;
        border-radius: 13px;
        box-shadow: 0 12px 35px rgba(20,50,25,.07);
    }}

    .deck-slide.active {{ display: block; }}

    .slide-canvas {{
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: white;
        container-type: inline-size;
    }}

    .ppt-element {{
        position: absolute;
        overflow: visible;
    }}

    .ppt-text {{
        color: #1d2922;
        line-height: 1.35;
        overflow-wrap: anywhere;
        white-space: pre-wrap;
        padding: 2px;
    }}

    .ppt-image {{
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .ppt-image img {{
        width: 100%;
        height: 100%;
        object-fit: contain;
    }}

    .ppt-table {{ overflow: auto; }}

    .ppt-table-scroll {{
        width: 100%;
        height: 100%;
        overflow: auto;
    }}

    .ppt-table table {{
        width: 100%;
        height: 100%;
        border-collapse: collapse;
        font-size: 1.4cqw;
        min-width: 0;
    }}

    .ppt-table td, .ppt-table th {{
        padding: 4px;
        border: 1px solid #dfe8e1;
        overflow-wrap: anywhere;
    }}

    .ppt-table th {{
        background: #eaf5e0;
        color: #2e7a00;
    }}

    .slide-accent {{
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 5px;
        background: linear-gradient(
            90deg, #31B44A 0%, #31B44A 70%,
            #D7982F 70%, #D7982F 100%
        );
        z-index: 1000;
    }}

    .slide-watermark {{
        position: absolute;
        bottom: 1%;
        right: 2%;
        z-index: 1001;
        color: rgba(46,122,0,.5);
        font-size: clamp(6px, .7vw, 10px);
        font-weight: 800;
        letter-spacing: 1px;
        pointer-events: none;
    }}

    .slide-index {{
        position: absolute;
        bottom: 1%;
        left: 2%;
        z-index: 1001;
        color: #9aa69c;
        font-size: clamp(7px, .8vw, 11px);
    }}

    .deck-controls {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        max-width: 1100px;
        margin: 17px auto 0;
        gap: 12px;
    }}

    .control-button {{
        min-height: 43px;
        padding: 9px 18px;
        border: 1px solid #dfe8e1;
        border-radius: 8px;
        background: white;
        color: #1d2922;
        font-weight: 700;
        cursor: pointer;
    }}

    .control-button.primary {{
        background: #31B44A;
        color: white;
        border-color: #31B44A;
    }}

    .control-button:disabled {{
        opacity: .4;
        cursor: not-allowed;
    }}

    .control-counter {{
        color: #68766d;
        font-size: 13px;
    }}

    .control-counter strong {{ color: #2e7a00; }}

    @media(max-width: 850px) {{
        .deck-shell {{ grid-template-columns: 200px minmax(0,1fr); }}
        .deck-main {{ padding: 15px; }}
        .deck-sidebar {{ padding: 15px 8px; }}
    }}

    @media(max-width: 600px) {{
        .deck-header {{ min-height: 60px; padding: 6px 12px; }}
        .deck-brand .brand-logo {{ height: 40px; }}
        .deck-brand {{ font-size: 10px; }}
        .deck-document-title {{ font-size: 10px; }}
        .deck-shell {{ display: flex; flex-direction: column; }}

        .deck-sidebar {{
            position: relative;
            top: auto;
            width: 100%;
            height: auto;
            max-height: 125px;
            overflow-y: auto;
            border-right: 0;
            border-bottom: 1px solid #dfe8e1;
            padding: 9px;
        }}

        .sidebar-heading {{ padding-bottom: 7px; }}
        .slide-list {{ flex-direction: row; overflow-x: auto; }}

        .slide-nav-item {{
            flex: 0 0 145px;
            padding: 7px;
        }}

        .deck-main {{ padding: 10px; }}
        .deck-slide {{ border-radius: 7px; }}

        .control-button {{
            padding: 8px 10px;
            font-size: 11px;
        }}
    }}
    """


def _safe_percentage(value):
    try:
        return max(-20, min(float(value), 120))
    except (TypeError, ValueError):
        return 0


def _element_position_style(position):
    left = _safe_percentage(position.get("left", 0))
    top = _safe_percentage(position.get("top", 0))
    width = _safe_percentage(position.get("width", 100))
    height = _safe_percentage(position.get("height", 10))

    try:
        order = max(1, min(int(position.get("order", 1)), 999))
    except (TypeError, ValueError):
        order = 1

    return (
        f"left:{left}%;top:{top}%;"
        f"width:{width}%;height:{height}%;z-index:{order};"
    )


def _render_pptx_elements(elements, slide_width=None):
    output = []

    for element in elements:
        kind = element.get("kind")
        position = element.get("position", {})
        style = _element_position_style(position)

        if kind == "text":
            content = escape(str(element.get("text", "")))

            try:
                points = float(element.get("font_size_pt", 18) or 18)
            except (TypeError, ValueError):
                points = 18

            # Font size is a share of the slide width, so the text
            # scales together with the slide on every screen size.
            try:
                relative = points * 12700 / float(slide_width) * 100
            except (TypeError, ValueError, ZeroDivisionError):
                relative = points / 960 * 100

            text_lines = "<br>".join(content.splitlines())

            output.append(
                f"""
                <div class="ppt-element ppt-text"
                     style="{style}font-size:{points:.1f}px;font-size:{relative:.3f}cqw;">
                    {text_lines}
                </div>
                """
            )

        elif kind == "image":
            url = escape(str(element.get("url", "")))

            if url:
                output.append(
                    f"""
                    <div class="ppt-element ppt-image" style="{style}">
                        <img src="{url}" alt="" draggable="false">
                    </div>
                    """
                )

        elif kind == "table":
            rows = []

            for row_index, row in enumerate(element.get("rows", [])):
                tag = "th" if row_index == 0 else "td"
                cells = "".join(
                    f"<{tag}>{escape(str(cell))}</{tag}>"
                    for cell in row
                )
                rows.append(f"<tr>{cells}</tr>")

            output.append(
                f"""
                <div class="ppt-element ppt-table" style="{style}">
                    <div class="ppt-table-scroll">
                        <table><tbody>{''.join(rows)}</tbody></table>
                    </div>
                </div>
                """
            )

    return "".join(output)


def _legacy_pptx_elements(page):
    elements = []
    blocks = page.get("blocks", [])
    images = page.get("images", [])
    total = max(1, len(blocks) + len(images))
    current_top = 5

    for block in blocks:
        kind = block.get("kind")

        if kind in ("heading", "paragraph"):
            text_value = str(block.get("text", ""))
            height = max(8, 75 / total)

            elements.append({
                "kind": "text",
                "text": text_value,
                "font_size_pt": 18,
                "position": {
                    "left": 5,
                    "top": current_top,
                    "width": 90,
                    "height": height,
                    "order": len(elements) + 1,
                },
            })

            current_top += height

        elif kind == "table":
            elements.append({
                "kind": "table",
                "rows": block.get("rows", []),
                "position": {
                    "left": 5,
                    "top": current_top,
                    "width": 90,
                    "height": 20,
                    "order": len(elements) + 1,
                },
            })
            current_top += 22

    for image in images:
        elements.append({
            "kind": "image",
            "url": image.get("url", ""),
            "position": {
                "left": 10,
                "top": current_top,
                "width": 80,
                "height": 20,
                "order": len(elements) + 1,
            },
        })
        current_top += 22

    return elements


def _generate_presentation_navigation(total):
    return f"""
    <script>
    (() => {{
        const slides = Array.from(
            document.querySelectorAll(".deck-slide")
        );
        const buttons = Array.from(
            document.querySelectorAll(".slide-nav-item")
        );

        const previous = document.getElementById("previous-slide");
        const next = document.getElementById("next-slide");
        const currentLabel = document.getElementById("current-slide");
        const progressLabel = document.getElementById("progress-label");
        const progressFill = document.getElementById("progress-fill");

        let current = 0;

        function showSlide(index) {{
            current = Math.max(0, Math.min(index, slides.length - 1));

            slides.forEach((slide, i) => {{
                slide.classList.toggle("active", i === current);
            }});

            buttons.forEach((button, i) => {{
                button.classList.toggle("active", i === current);
            }});

            const number = current + 1;
            currentLabel.textContent = String(number).padStart(2, "0");
            progressLabel.textContent = number + " / " + slides.length;
            progressFill.style.width =
                (number / slides.length * 100) + "%";

            previous.disabled = current === 0;
            next.disabled = current === slides.length - 1;
        }}

        previous.addEventListener("click", () => showSlide(current - 1));
        next.addEventListener("click", () => showSlide(current + 1));

        buttons.forEach(button => {{
            button.addEventListener("click", () => {{
                showSlide(Number(button.dataset.goTo) - 1);
            }});
        }});

        document.addEventListener("keydown", event => {{
            if (
                event.target instanceof HTMLInputElement ||
                event.target instanceof HTMLTextAreaElement
            ) return;

            if (event.key === "ArrowLeft") showSlide(current - 1);
            if (event.key === "ArrowRight") showSlide(current + 1);
        }});

        showSlide(0);
    }})();
    </script>
    """


def _presentation_shell(document, slides, navigation, total, slide_width, slide_height):
    logo = _brand_markup()

    body = f"""
    <header class="deck-header">
        <div class="deck-brand">{logo}</div>
        <div class="deck-document-title">
            {escape(_document_title(document))}
        </div>
    </header>

    <main class="deck-shell">
        <aside class="deck-sidebar">
            <div class="sidebar-heading">
                <span>LESSON CONTENT</span>
                <strong>{total} SLIDES</strong>
            </div>
            <nav class="slide-list">{''.join(navigation)}</nav>
        </aside>

        <section class="deck-main">
            <div class="deck-progress">
                <div class="progress-track">
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
                <span id="progress-label">1 / {total}</span>
            </div>

            <div class="deck-stage">{''.join(slides)}</div>

            <footer class="deck-controls">
                <button type="button" id="previous-slide"
                        class="control-button">&larr; Previous</button>

                <div class="control-counter">
                    <strong id="current-slide">01</strong>
                    <span> / {total:02d}</span>
                </div>

                <button type="button" id="next-slide"
                        class="control-button primary">Next &rarr;</button>
            </footer>
        </section>
    </main>

    {_generate_presentation_navigation(total)}
    """

    css = _presentation_css(slide_width, slide_height)

    return _document_shell(
        document.title, body, css, "presentation"
    )


def generate_ai_presentation_html(document, extracted_data):
    pages = extracted_data.get("pages", [])

    if not pages:
        raise ValueError("No PowerPoint slides were extracted.")

    slide_width = extracted_data.get("slide_width", 16)
    slide_height = extracted_data.get("slide_height", 9)

    slide_html = []
    sidebar_html = []

    for index, page in enumerate(pages, start=1):
        elements = page.get("elements")

        if not elements:
            elements = _legacy_pptx_elements(page)

        rendered = _render_pptx_elements(elements, slide_width)

        title = next(
            (
                str(element.get("text", ""))
                for element in elements
                if element.get("kind") == "text"
                and str(element.get("text", "")).strip()
            ),
            f"Slide {index}",
        )

        title = title.splitlines()[0][:50]
        active = " active" if index == 1 else ""

        slide_html.append(
            f"""
            <section class="deck-slide{active}" id="slide-{index}">
                <div class="slide-canvas">
                    <div class="slide-accent"></div>
                    {rendered}
                    <div class="slide-watermark">TELESOM ACADEMY</div>
                    <div class="slide-index">{index:02d}</div>
                </div>
            </section>
            """
        )

        sidebar_html.append(
            f"""
            <button class="slide-nav-item{active}"
                    type="button" data-go-to="{index}">
                <span class="nav-number">{index:02d}</span>
                <span class="nav-title">{escape(title)}</span>
            </button>
            """
        )

    return _presentation_shell(
        document,
        slide_html,
        sidebar_html,
        len(pages),
        slide_width,
        slide_height,
    )


def _generate_page_presentation_html(document, extracted_data):
    pages = extracted_data.get("pages", [])

    if not pages:
        raise ValueError("No document pages were extracted.")

    slides = []
    navigation = []

    for index, page in enumerate(pages, start=1):
        title = _page_title(page, index)
        content = _render_blocks(_page_blocks(page))
        active = " active" if index == 1 else ""

        slides.append(
            f"""
            <section class="deck-slide{active}">
                <div class="slide-canvas">
                    <div class="slide-accent"></div>
                    <div class="page-presentation-content">
                        <div class="page-presentation-label">
                            TELESOM ACADEMY &middot; SECTION {index:02d}
                        </div>
                        <h1>{escape(title)}</h1>
                        {content}
                    </div>
                    <div class="slide-watermark">TELESOM ACADEMY</div>
                </div>
            </section>
            """
        )

        navigation.append(
            f"""
            <button class="slide-nav-item{active}"
                    type="button" data-go-to="{index}">
                <span class="nav-number">{index:02d}</span>
                <span class="nav-title">{escape(title)}</span>
            </button>
            """
        )

    body_shell = _presentation_shell(
        document,
        slides,
        navigation,
        len(pages),
        16,
        9,
    )

    extra_css = """
    .page-presentation-content {
        position: absolute;
        inset: 5% 7%;
        overflow: auto;
        padding: 3% 2%;
    }

    .page-presentation-content h1 {
        font-size: clamp(22px, 3vw, 40px);
        margin: 0 0 22px;
    }

    .page-presentation-label {
        color: #aa841c;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 1.5px;
        margin-bottom: 18px;
    }

    .page-presentation-content p {
        font-size: clamp(12px, 1.4vw, 18px);
    }

    .page-presentation-content img {
        max-height: 45%;
        width: auto;
        object-fit: contain;
    }

    .page-presentation-content .document-image {
        margin: 12px auto;
    }
    """

    return body_shell.replace(
        "</style>",
        extra_css + "\n</style>",
        1,
    )


# =========================================================
# MODERN, MINIMAL, CORPORATE AND WORKBOOK RENDERERS
# =========================================================

def _generate_modern_html(document, extracted_data):
    content = _render_blocks(_all_blocks(extracted_data))

    body = f"""
    <header class="brand-header">{_brand_markup()}</header>
    <main class="modern-page">
        <section class="modern-hero">
            <div class="modern-label">TELESOM ACADEMY &middot; LEARNING MATERIAL</div>
            <h1>{escape(_document_title(document))}</h1>
        </section>
        <article class="modern-content">{content}</article>
        <footer class="academy-footer">TELESOM ACADEMY</footer>
    </main>
    """

    return _document_shell(
        document.title, body, _modern_css(), "modern"
    )


def _generate_minimal_html(document, extracted_data):
    content = _render_blocks(_all_blocks(extracted_data))

    body = f"""
    <header class="minimal-header">
        {_brand_markup()}
        <h1>{escape(_document_title(document))}</h1>
    </header>
    <main class="minimal-content">{content}</main>
    <footer class="academy-footer">TELESOM ACADEMY</footer>
    """

    return _document_shell(
        document.title, body, _minimal_css(), "minimal"
    )


def _generate_corporate_html(document, extracted_data):
    content = _render_blocks(_all_blocks(extracted_data))

    body = f"""
    <header class="corporate-banner">
        <div class="corporate-banner-inner">
            {_brand_markup()}
            <div class="corporate-label">LEARNING &amp; DEVELOPMENT</div>
        </div>
    </header>

    <div class="corporate-title">
        <h1>{escape(_document_title(document))}</h1>
    </div>

    <main class="corporate-content">{content}</main>

    <footer class="academy-footer">TELESOM ACADEMY</footer>
    """

    return _document_shell(
        document.title, body, _corporate_css(), "corporate"
    )


def _generate_workbook_html(document, extracted_data):
    content = _render_blocks(_all_blocks(extracted_data))

    body = f"""
    <main class="workbook-page">
        <header class="workbook-cover">
            {_brand_markup()}
            <h1>{escape(_document_title(document))}</h1>
        </header>

        <article class="workbook-content">
            {content}
            <div class="workbook-notes">
                <strong>STUDY NOTES</strong>
                Use this space for your own learning notes.
            </div>
        </article>

        <footer class="academy-footer">TELESOM ACADEMY</footer>
    </main>
    """

    return _document_shell(
        document.title, body, _workbook_css(), "workbook"
    )


# =========================================================
# MAIN TEMPLATE GENERATOR
# =========================================================

def generate_professional_lesson_html(
    document,
    extracted_data,
    template_key="academy",
):
    if not isinstance(extracted_data, dict):
        raise ValueError("Invalid extracted document data.")

    pages = extracted_data.get("pages", [])

    if not pages:
        raise ValueError("No document pages or slides were extracted.")

    template_key = str(template_key or "academy").lower().strip()

    if template_key not in TEMPLATE_CATALOG:
        raise ValueError(
            "Unsupported template. Available templates: "
            + ", ".join(TEMPLATE_CATALOG.keys())
        )

    if template_key == "presentation":
        if extracted_data.get("format") == "pptx":
            return generate_ai_presentation_html(
                document, extracted_data
            )

        return _generate_page_presentation_html(
            document, extracted_data
        )

    generators = {
        "academy": _generate_academy_html,
        "editorial": _generate_editorial_html,
        "interactive": _generate_interactive_html,
        "modern": _generate_modern_html,
        "minimal": _generate_minimal_html,
        "corporate": _generate_corporate_html,
        "workbook": _generate_workbook_html,
    }

    return generators[template_key](document, extracted_data)


# =========================================================
# BACKWARD-COMPATIBLE PUBLIC GENERATORS
# =========================================================

def generate_ai_lesson_html(
    document,
    extracted_data,
    template_key="academy",
):
    return generate_professional_lesson_html(
        document,
        extracted_data,
        template_key,
    )


def generate_responsive_html(document, extracted_data):
    return generate_professional_lesson_html(
        document,
        extracted_data,
        "academy",
    )


def generate_template_html(
    document,
    extracted_data,
    template_key="academy",
):
    return generate_professional_lesson_html(
        document,
        extracted_data,
        template_key,
    )