from html import escape
from pathlib import Path

from django.conf import settings
from docx import Document as WordDocument
from pptx import Presentation
from pypdf import PdfReader


def _image_folder(document):
    image_folder = (
        Path(settings.MEDIA_ROOT)
        / "extracted_images"
        / f"document_{document.id}"
    )
    image_folder.mkdir(parents=True, exist_ok=True)
    return image_folder


def _save_image(document, filename, data):
    image_folder = _image_folder(document)
    image_path = image_folder / filename

    with open(image_path, "wb") as image_file:
        image_file.write(data)

    relative_path = image_path.relative_to(Path(settings.MEDIA_ROOT))
    return {
        "filename": filename,
        "url": settings.MEDIA_URL + relative_path.as_posix(),
    }


def extract_pdf(document):
    """Extract text, metadata and original image bytes from a PDF."""
    pdf_path = document.original_file.path
    reader = PdfReader(pdf_path)
    extracted_pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        extracted_images = []

        for image_number, image in enumerate(page.images, start=1):
            extension = Path(image.name).suffix or ".bin"
            filename = f"page_{page_number}_image_{image_number}{extension}"
            extracted_images.append(_save_image(document, filename, image.data))

        extracted_pages.append({
            "page_number": page_number,
            "text": page_text,
            "images": extracted_images,
        })

    return {
        "filename": document.title,
        "format": "pdf",
        "total_pages": len(reader.pages),
        "metadata": {
            "title": reader.metadata.title if reader.metadata else None,
            "author": reader.metadata.author if reader.metadata else None,
            "subject": reader.metadata.subject if reader.metadata else None,
        },
        "pages": extracted_pages,
    }


def extract_pptx(document):
    """Extract slide text, tables and original picture bytes from PPTX."""
    presentation = Presentation(document.original_file.path)
    extracted_pages = []

    for slide_number, slide in enumerate(presentation.slides, start=1):
        slide_parts = []
        extracted_images = []
        image_number = 0

        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                text = "\n".join(
                    paragraph.text.strip()
                    for paragraph in shape.text_frame.paragraphs
                    if paragraph.text.strip()
                )
                if text:
                    slide_parts.append(text)

            if getattr(shape, "has_table", False):
                table_rows = []
                for row in shape.table.rows:
                    table_rows.append(" | ".join(cell.text.strip() for cell in row.cells))
                if table_rows:
                    slide_parts.append("\n".join(table_rows))

            if shape.shape_type == 13:
                image_number += 1
                extension = shape.image.ext
                filename = f"slide_{slide_number}_image_{image_number}.{extension.lstrip('.')}"  # Fixed line
                extracted_images.append(_save_image(document, filename, shape.image.blob))

        extracted_pages.append({
            "page_number": slide_number,
            "text": "\n\n".join(slide_parts),
            "images": extracted_images,
        })

    return {
        "filename": document.title,
        "format": "pptx",
        "total_pages": len(presentation.slides),
        "metadata": {},
        "pages": extracted_pages,
    }


def extract_docx(document):
    """Extract Word paragraphs, tables, headings and original image bytes."""
    word_document = WordDocument(document.original_file.path)
    parts = []
    extracted_images = []

    for paragraph in word_document.paragraphs:
        text = paragraph.text.strip()
        if text:
            style_name = paragraph.style.name if paragraph.style else ""
            heading_level = None
            if style_name.lower().startswith("heading"):
                suffix = style_name.lower().replace("heading", "").strip()
                if suffix.isdigit():
                    heading_level = int(suffix)
            parts.append({"type": "heading" if heading_level else "paragraph", "text": text, "level": heading_level})

    for table_index, table in enumerate(word_document.tables, start=1):
        rows = []
        for row in table.rows:
            rows.append([cell.text.strip() for cell in row.cells])
        parts.append({"type": "table", "rows": rows, "table_number": table_index})

    for image_index, inline_shape in enumerate(word_document.inline_shapes, start=1):
        blip = inline_shape._inline.graphic.graphicData.pic.blipFill.blip
        relationship = word_document.part.related_parts[blip.embed]
        if hasattr(relationship, "blob"):
            image_bytes = relationship.blob
            content_type = getattr(relationship, "content_type", "image/png")
            extension = content_type.split("/")[-1].replace("jpeg", "jpg")
            filename = f"word_image_{image_index}.{extension}"
            extracted_images.append(_save_image(document, filename, image_bytes))

    page = {
        "page_number": 1,
        "text": "\n".join(part["text"] for part in parts if part["type"] in ("heading", "paragraph")),
        "structures": parts,
        "images": extracted_images,
    }

    return {
        "filename": document.title,
        "format": "docx",
        "total_pages": 1,
        "metadata": {},
        "pages": [page],
    }


def extract_document(document):
    extension = Path(document.original_file.name).suffix.lower()

    if extension == ".pdf":
        return extract_pdf(document)
    if extension == ".pptx":
        return extract_pptx(document)
    if extension == ".docx":
        return extract_docx(document)

    if extension in (".ppt", ".doc"):
        raise ValueError(
            f"The {extension} format requires a verified Office conversion component and cannot be safely claimed as supported yet."
        )

    raise ValueError("Unsupported document format.")


def generate_responsive_html(document, extracted_data):
    title = escape(document.title)
    sections = []

    for page in extracted_data.get("pages", []):
        page_number = page.get("page_number")
        structures = page.get("structures")

        if structures:
            content = []
            for part in structures:
                if part["type"] == "heading":
                    level = max(1, min(part.get("level") or 2, 6))
                    content.append(f"<h{level}>{escape(part['text'])}</h{level}>")
                elif part["type"] == "paragraph":
                    content.append(f"<p>{escape(part['text'])}</p>")
                elif part["type"] == "table":
                    rows = []
                    for row in part.get("rows", []):
                        cells = "".join(f"<td>{escape(cell)}</td>" for cell in row)
                        rows.append(f"<tr>{cells}</tr>")
                    content.append("<table><tbody>" + "".join(rows) + "</tbody></table>")
            for image in page.get("images", []):
                content.append(f'<figure><img src="{escape(image["url"])}" alt="" style="object-fit:contain;width:100%;height:auto"></figure>')
            sections.append(f'<article class="lesson-page"><header><span>Page {page_number}</span></header>{"".join(content)}</article>')
        else:
            paragraphs = [paragraph.strip() for paragraph in (page.get("text") or "").split("\n") if paragraph.strip()]
            content = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
            for image in page.get("images", []):
                content += f'<figure><img src="{escape(image["url"])}" alt="" style="object-fit:contain;width:100%;height:auto"></figure>'
            sections.append(f'<article class="lesson-page"><header><span>Page {page_number}</span></header>{content}</article>')

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ --green:#00843D; --gold:#D4AF37; --ink:#152419; --muted:#66736b; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:#edf3ef; color:var(--ink); font-family:Inter,Segoe UI,Arial,sans-serif; line-height:1.65; }}
    main {{ width:min(100% - 32px, 960px); margin:32px auto; }}
    .lesson-page {{ background:white; border:1px solid #dde6df; border-radius:14px; padding:clamp(24px,5vw,56px); margin-bottom:24px; box-shadow:0 12px 35px rgba(16,70,39,.07); }}
    .lesson-page header {{ border-left:4px solid var(--gold); padding-left:12px; color:var(--muted); font-size:.85rem; margin-bottom:24px; }}
    h1,h2,h3,h4,h5,h6 {{ color:var(--green); line-height:1.25; }}
    p {{ margin:.25em 0 1em; }}
    table {{ width:100%; border-collapse:collapse; margin:20px 0; }}
    td,th {{ border:1px solid #dce5df; padding:10px; text-align:left; }}
    figure {{ margin:24px 0; text-align:center; }}
    .lesson-brand {{ display:flex; justify-content:center; padding:18px 16px 0; }}
    .lesson-brand img {{ width:220px; max-width:70%; height:auto; object-fit:contain; }}
    img {{ max-width:100%; height:auto !important; }}
    @media(max-width:600px) {{ main{{width:min(100% - 20px,960px);margin:10px auto}}.lesson-page{{border-radius:8px;padding:20px 16px}} }}
  </style>
</head>
<body>
  <header class="lesson-brand"><img src="/static/brand/telesom-academy-logo.png" alt="Telesom Academy"></header>
  <main>{''.join(sections)}</main>
</body>
</html>'''

TEMPLATE_CATALOG = {
    'academy': {
        'name': 'Academy',
        'description': 'Structured lesson with navigation and section progress.',
    },
    'editorial': {
        'name': 'Editorial',
        'description': 'Elegant reading layout for refined document-led lessons.',
    },
    'interactive': {
        'name': 'Interactive',
        'description': 'Sectioned lesson with expandable learning elements.',
    },
    'presentation': {
        'name': 'Presentation',
        'description': 'Slide-inspired lesson with previous and next controls.',
    },
}


def _escaped_blocks(extracted_data, preserve_structures=True):
    blocks = []
    for page in extracted_data.get('pages', []):
        page_number = page.get('page_number')
        structures = page.get('structures') if preserve_structures else None
        if structures:
            for part in structures:
                if part['type'] == 'heading':
                    level = max(1, min(part.get('level') or 2, 6))
                    blocks.append({'kind': 'heading', 'level': level, 'text': part['text'], 'page': page_number})
                elif part['type'] == 'paragraph':
                    blocks.append({'kind': 'paragraph', 'text': part['text'], 'page': page_number})
                elif part['type'] == 'table':
                    blocks.append({'kind': 'table', 'rows': part.get('rows', []), 'page': page_number})
        else:
            for paragraph in [item.strip() for item in (page.get('text') or '').split('\n') if item.strip()]:
                blocks.append({'kind': 'paragraph', 'text': paragraph, 'page': page_number})

        for image in page.get('images', []):
            blocks.append({'kind': 'image', 'url': image['url'], 'filename': image['filename'], 'page': page_number})
    return blocks


def _render_blocks(blocks, style='paragraph'):
    output = []
    for block in blocks:
        if block['kind'] == 'heading':
            level = block['level']
            output.append(f'<h{level}>{escape(block["text"])}</h{level}>')
        elif block['kind'] == 'paragraph':
            output.append(f'<p>{escape(block["text"])}</p>')
        elif block['kind'] == 'table':
            rows = []
            for row in block['rows']:
                rows.append('<tr>' + ''.join(f'<td>{escape(cell)}</td>' for cell in row) + '</tr>')
            output.append('<div class="table-wrap"><table><tbody>' + ''.join(rows) + '</tbody></table></div>')
        elif block['kind'] == 'image':
            output.append(
                f'<figure><img src="{escape(block["url"])}" alt="" loading="lazy" '
                'style="object-fit:contain;width:100%;height:auto;max-width:100%"></figure>'
            )
    return ''.join(output)


def _template_shell(title, body, template_key):
    logo = '/static/brand/telesom-academy-logo.png'
    common = '''
      :root { --green:#31B44A; --gold:#D7982F; --ink:#1b241f; --muted:#69756f; --line:#dde5df; }
      * { box-sizing:border-box; }
      body { margin:0; color:var(--ink); font-family:Inter,Segoe UI,Arial,sans-serif; line-height:1.65; }
      img { max-width:100%; height:auto; object-fit:contain; }
      table { width:100%; border-collapse:collapse; margin:20px 0; }
      td,th { border:1px solid var(--line); padding:10px 12px; text-align:left; }
      figure { margin:24px 0; text-align:center; }
      .brand-header { display:flex; justify-content:center; padding:18px 20px 8px; }
      .brand-header img { height:58px; width:auto; max-width:220px; object-fit:contain; }
    '''

    if template_key == 'academy':
        css = common + '''
          body { background:#f3f6f4; }
          .academy { min-height:100vh; display:grid; grid-template-columns:230px minmax(0,1fr); }
          .academy-nav { background:#fff; border-right:1px solid var(--line); padding:28px 20px; }
          .academy-nav strong { color:var(--green); }
          .academy-progress { height:6px; border-radius:999px; background:#edf1ee; margin:20px 0; overflow:hidden; }
          .academy-progress span { display:block; width:68%; height:100%; background:var(--green); }
          .academy-main { width:min(820px,calc(100% - 48px)); margin:28px auto 60px; }
          .academy-content { background:#fff; border:1px solid var(--line); border-radius:14px; padding:48px; }
          h1,h2,h3 { color:var(--green); line-height:1.25; }
          @media(max-width:720px){.academy{display:block}.academy-nav{display:none}.academy-main{width:calc(100% - 24px);margin:12px auto}.academy-content{padding:24px 18px}}
        '''
    elif template_key == 'editorial':
        css = common + '''
          body { background:#f8f8f5; }
          .editorial { width:min(820px,calc(100% - 32px)); margin:0 auto 60px; }
          .editorial-top { border-bottom:1px solid var(--line); }
          .editorial article { background:#fff; border:1px solid #ebece8; border-radius:3px; margin-top:24px; padding:48px 64px 56px; }
          .editorial h1 { font-family:Georgia,serif; font-size:42px; line-height:1.12; color:#233128; }
          .editorial h2,.editorial h3 { font-family:Georgia,serif; color:var(--green); }
          .editorial p { font-family:Georgia,serif; font-size:17px; }
          @media(max-width:720px){.editorial article{padding:28px 20px}.editorial h1{font-size:32px}}
        '''
    elif template_key == 'interactive':
        css = common + '''
          body { background:#edf5f0; }
          .interactive { width:min(980px,calc(100% - 32px)); margin:0 auto 60px; }
          .interactive .learning-card { background:#fff; border:1px solid var(--line); border-radius:14px; margin:16px 0; padding:18px 22px; }
          .interactive summary { color:var(--green); font-weight:800; cursor:pointer; }
          .interactive h1,h2,h3 { color:var(--green); }
          .interactive .key-point { border-left:4px solid var(--gold); background:#fffaf0; padding:14px 18px; }
          @media(max-width:720px){.interactive{width:calc(100% - 20px)}}
        '''
    else:
        css = common + '''
          body { background:#18251d; }
          .presentation { width:min(980px,calc(100% - 32px)); margin:0 auto 40px; }
          .presentation .slides { position:relative; }
          .presentation input { position:absolute; opacity:0; }
          .presentation .slide { display:none; min-height:520px; background:#fff; border-radius:16px; border-top:8px solid var(--green); padding:52px 64px; }
          .presentation input:nth-of-type(1):checked ~ .slides .slide-1,
          .presentation input:nth-of-type(2):checked ~ .slides .slide-2,
          .presentation input:nth-of-type(3):checked ~ .slides .slide-3 { display:block; }
          .presentation h1 { color:var(--green); font-size:38px; }
          .presentation .controls { display:flex; justify-content:center; gap:8px; margin-top:18px; }
          .presentation label { width:36px; height:36px; border:1px solid #d6ded8; border-radius:50%; background:#fff; display:grid; place-items:center; cursor:pointer; }
          @media(max-width:720px){.presentation{width:calc(100% - 20px)}.presentation .slide{min-height:420px;padding:28px 20px}.presentation h1{font-size:28px}}
        '''

    escaped_title = escape(title)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escaped_title}</title>
<style>{css}</style>
</head>
<body>
<header class="brand-header"><img src="{logo}" alt="Telesom Academy"></header>
{body}
</body>
</html>'''


def generate_template_html(document, extracted_data, template_key):
    if template_key not in TEMPLATE_CATALOG:
        template_key = 'academy'

    blocks = _escaped_blocks(extracted_data)
    title = document.title

    if template_key == 'academy':
        body = f'''<div class="academy"><aside class="academy-nav"><strong>Lesson</strong><div class="academy-progress"><span></span></div><small>Section overview</small></aside><main class="academy-main"><article class="academy-content"><h1>{escape(title)}</h1>{_render_blocks(blocks)}</article></main></div>'''
    elif template_key == 'editorial':
        body = f'''<main class="editorial"><article><h1>{escape(title)}</h1>{_render_blocks(blocks)}</article></main>'''
    elif template_key == 'interactive':
        body = f'''<main class="interactive"><article class="learning-card"><h1>{escape(title)}</h1></article><details class="learning-card" open><summary>Lesson content</summary>{_render_blocks(blocks)}</details><aside class="learning-card key-point"><strong>Key point</strong><p>Review the content and original images below.</p></aside></main>'''
    else:
        pages = extracted_data.get('pages', [])
        if not pages:
            pages = [{'page_number': 1, 'text': 'No extractable content was found.', 'images': []}]

        slide_bodies = []
        inputs = []
        labels = []
        selectors = []
        for index, page in enumerate(pages, start=1):
            page_blocks = _escaped_blocks({'pages': [page]})
            slide_bodies.append(f'<section class="slide slide-{index}"><h1>{escape(title)}</h1><h2>Page {index}</h2>{_render_blocks(page_blocks)}</section>')
            checked = ' checked' if index == 1 else ''
            inputs.append(f'<input type="radio" name="slide" id="slide{index}"{checked}>')
            labels.append(f'<label for="slide{index}">{index}</label>')
            selectors.append(f'.presentation input:nth-of-type({index}):checked ~ .slides .slide-{index} {{ display:block; }}')

        dynamic_css = '<style>' + ''.join(selectors) + '</style>'
        body = '<main class="presentation">' + dynamic_css + ''.join(inputs) + '<div class="slides">' + ''.join(slide_bodies) + '</div><div class="controls">' + ''.join(labels) + '</div></main>'

    return _template_shell(title, body, template_key)
