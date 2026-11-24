import base64
import io
import mimetypes
import re
import zipfile
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document

from .services import (
    TEMPLATE_CATALOG,
    extract_document,
    generate_template_html,
)


# =========================================================
# HELPERS
# =========================================================

def get_document(document_id):
    """Return a document that has not been soft-deleted."""

    try:
        return Document.objects.get(
            id=document_id,
            deleted_at__isnull=True,
        )
    except Document.DoesNotExist:
        return None


def _safe_filename(value, fallback="lesson"):
    name = Path(str(value or fallback)).stem
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.strip(" ._")

    return name or fallback


def _json_error(message, status_code):
    return Response({"error": str(message)}, status=status_code)


def _get_logo_path():
    return (
        Path(settings.BASE_DIR)
        / "static"
        / "brand"
        / "telesom-academy-logo.png"
    )


def _get_document_image_folder(document):
    return (
        Path(settings.MEDIA_ROOT)
        / "extracted_images"
        / f"document_{document.id}"
    )


def _embed_media_images(html):
    """Turn /media/... image links into embedded images so a single
    HTML file works on its own, with no other files next to it."""

    media_url = (settings.MEDIA_URL or "/media/").rstrip("/") + "/"
    media_root = Path(settings.MEDIA_ROOT).resolve()
    pattern = re.compile(
        r'src="' + re.escape(media_url) + r'([^"]+)"'
    )

    def replace(match):
        path = (media_root / match.group(1)).resolve()

        if media_root not in path.parents or not path.is_file():
            return match.group(0)

        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = base64.b64encode(path.read_bytes()).decode("ascii")

        return f'src="data:{mime};base64,{data}"'

    return pattern.sub(replace, html)


# =========================================================
# EXTRACTION
# =========================================================

class DocumentExtractionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, document_id):
        document = get_document(document_id)

        if document is None:
            return _json_error(
                "Document not found.", status.HTTP_404_NOT_FOUND
            )

        document.status = "processing"
        document.conversion_error = None
        document.save(
            update_fields=["status", "conversion_error", "updated_at"]
        )

        try:
            extracted_data = extract_document(document)

            if (
                not isinstance(extracted_data, dict)
                or not extracted_data.get("pages")
            ):
                raise ValueError(
                    "No readable content was extracted from this document."
                )

            document.extracted_data = extracted_data
            document.generated_html = None
            document.status = "completed"
            document.conversion_error = None

            document.save(
                update_fields=[
                    "extracted_data",
                    "generated_html",
                    "status",
                    "conversion_error",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "message": "Document extracted successfully.",
                    "status": "success",
                    "progress": 100,
                    "data": extracted_data,
                    "has_generated_html": False,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as error:
            document.status = "failed"
            document.conversion_error = str(error)
            document.save(
                update_fields=["status", "conversion_error", "updated_at"]
            )

            return Response(
                {"error": str(error), "status": "failed", "progress": 0},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PDFExtractionView(DocumentExtractionView):
    """Backward-compatible extraction endpoint."""


class ExtractedDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        document = get_document(document_id)

        if document is None:
            return _json_error(
                "Document not found.", status.HTTP_404_NOT_FOUND
            )

        if not document.extracted_data:
            return _json_error(
                "This document has not been extracted yet.",
                status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "message": "Extracted data retrieved successfully.",
                "status": "success",
                "data": document.extracted_data,
            },
            status=status.HTTP_200_OK,
        )


# =========================================================
# PREVIEW AND DOWNLOADS
# =========================================================

class HTMLPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        document = get_document(document_id)

        if document is None:
            return _json_error(
                "Document not found.", status.HTTP_404_NOT_FOUND
            )

        if not document.generated_html:
            return _json_error(
                "This document has not been converted yet.",
                status.HTTP_404_NOT_FOUND,
            )

        response = HttpResponse(
            document.generated_html,
            content_type="text/html; charset=utf-8",
        )
        response["X-Content-Type-Options"] = "nosniff"

        return response


class HTMLDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        document = get_document(document_id)

        if document is None:
            return _json_error(
                "Document not found.", status.HTTP_404_NOT_FOUND
            )

        if not document.generated_html:
            return _json_error(
                "This document has not been converted yet.",
                status.HTTP_404_NOT_FOUND,
            )

        filename = _safe_filename(document.title) + ".html"

        # Images are embedded, so this one file works on its own.
        response = HttpResponse(
            _embed_media_images(document.generated_html),
            content_type="text/html; charset=utf-8",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{filename}"'
        )
        response["X-Content-Type-Options"] = "nosniff"

        return response


# =========================================================
# TEMPLATES
# =========================================================

class TemplateCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        templates = [
            {
                "key": key,
                "name": value["name"],
                "description": value["description"],
            }
            for key, value in TEMPLATE_CATALOG.items()
        ]

        return Response(
            {
                "message": "Template catalog retrieved successfully.",
                "status": "success",
                "data": templates,
            },
            status=status.HTTP_200_OK,
        )


class TemplateSelectionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, document_id):
        document = get_document(document_id)

        if document is None:
            return _json_error(
                "Document not found.", status.HTTP_404_NOT_FOUND
            )

        template_key = request.data.get("template")

        if not isinstance(template_key, str):
            return _json_error(
                "A valid template must be selected.",
                status.HTTP_400_BAD_REQUEST,
            )

        template_key = template_key.strip().lower()

        if template_key not in TEMPLATE_CATALOG:
            return Response(
                {
                    "error": "Unsupported lesson template.",
                    "available_templates": list(TEMPLATE_CATALOG.keys()),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        document.selected_template = template_key
        document.save(update_fields=["selected_template", "updated_at"])

        return Response(
            {
                "message": "Template selected successfully.",
                "status": "success",
                "data": {
                    "template": template_key,
                    "name": TEMPLATE_CATALOG[template_key]["name"],
                },
            },
            status=status.HTTP_200_OK,
        )


class GenerateDocumentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, document_id):
        document = get_document(document_id)

        if document is None:
            return _json_error(
                "Document not found.", status.HTTP_404_NOT_FOUND
            )

        if not document.extracted_data:
            return _json_error(
                "Extract the document before generating HTML.",
                status.HTTP_400_BAD_REQUEST,
            )

        template_key = request.data.get(
            "template",
            document.selected_template or "academy",
        )

        if not isinstance(template_key, str):
            return _json_error(
                "A valid template must be selected.",
                status.HTTP_400_BAD_REQUEST,
            )

        template_key = template_key.strip().lower()

        if template_key not in TEMPLATE_CATALOG:
            return Response(
                {
                    "error": "Unsupported template.",
                    "available_templates": list(TEMPLATE_CATALOG.keys()),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            generated_html = generate_template_html(
                document,
                document.extracted_data,
                template_key,
            )

            if (
                not isinstance(generated_html, str)
                or "<html" not in generated_html.lower()
            ):
                raise ValueError(
                    "The HTML generator did not return a valid HTML document."
                )

            document.selected_template = template_key
            document.generated_html = generated_html
            document.status = "completed"
            document.conversion_error = None

            document.save(
                update_fields=[
                    "selected_template",
                    "generated_html",
                    "status",
                    "conversion_error",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "message": "Document HTML generated successfully.",
                    "status": "success",
                    "template": template_key,
                    "template_name": TEMPLATE_CATALOG[template_key]["name"],
                    "progress": 100,
                    "has_generated_html": True,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as error:
            document.status = "failed"
            document.conversion_error = str(error)
            document.save(
                update_fields=["status", "conversion_error", "updated_at"]
            )

            return Response(
                {"error": str(error), "status": "failed", "progress": 0},
                status=status.HTTP_400_BAD_REQUEST,
            )


# =========================================================
# ZIP PACKAGE
# =========================================================

class AssetsDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        document = get_document(document_id)

        if document is None:
            return _json_error(
                "Document not found.", status.HTTP_404_NOT_FOUND
            )

        if not document.generated_html:
            return _json_error(
                "This document has not been converted yet.",
                status.HTTP_404_NOT_FOUND,
            )

        image_folder = _get_document_image_folder(document)
        logo_path = _get_logo_path()
        html = document.generated_html

        media_url = str(getattr(settings, "MEDIA_URL", "/media/") or "/media/")
        media_prefix = media_url.rstrip("/") + "/"

        html = html.replace('src="' + media_prefix, 'src="assets/')

        buffer = io.BytesIO()

        with zipfile.ZipFile(
            buffer, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            archive.writestr("lesson.html", html)

            if image_folder.is_dir():
                for image_path in sorted(image_folder.rglob("*")):
                    if not image_path.is_file():
                        continue

                    relative_path = image_path.relative_to(
                        Path(settings.MEDIA_ROOT)
                    )

                    archive.write(
                        image_path,
                        arcname="assets/" + relative_path.as_posix(),
                    )

            if logo_path.is_file():
                archive.write(
                    logo_path,
                    arcname="assets/telesom-academy-logo.png",
                )

        buffer.seek(0)

        filename = _safe_filename(document.title) + "-lesson.zip"

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/zip",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{filename}"'
        )
        response["X-Content-Type-Options"] = "nosniff"

        return response