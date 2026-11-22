import io
import zipfile
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document
from .services import (
    TEMPLATE_CATALOG,
    extract_document,
    generate_responsive_html,
    generate_template_html,
)


class DocumentExtractionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, document_id):
        try:
            document = Document.objects.get(id=document_id, deleted_at__isnull=True)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

        document.status = 'processing'
        document.conversion_error = None
        document.save(update_fields=['status', 'conversion_error', 'updated_at'])

        try:
            extracted_data = extract_document(document)
            document.extracted_data = extracted_data
            document.generated_html = generate_responsive_html(document, extracted_data)
            document.status = 'completed'
            document.save(update_fields=['extracted_data', 'generated_html', 'status', 'updated_at'])

            return Response({
                'message': 'Document converted successfully.',
                'status': 'success',
                'progress': 100,
                'data': extracted_data,
                'has_generated_html': True,
            }, status=status.HTTP_200_OK)

        except Exception as error:
            document.status = 'failed'
            document.conversion_error = str(error)
            document.save(update_fields=['status', 'conversion_error', 'updated_at'])

            return Response({'error': str(error), 'progress': 0, 'status': 'failed'}, status=status.HTTP_400_BAD_REQUEST)


class PDFExtractionView(DocumentExtractionView):
    """Backward-compatible PDF endpoint using the shared format-safe extractor."""


class ExtractedDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        try:
            document = Document.objects.get(id=document_id, deleted_at__isnull=True)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not document.extracted_data:
            return Response({'error': 'This document has not been extracted yet.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'message': 'Extracted data retrieved successfully.',
            'status': 'success',
            'data': document.extracted_data,
        }, status=status.HTTP_200_OK)


class HTMLPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    @xframe_options_exempt
    def get(self, request, document_id):
        try:
            document = Document.objects.get(id=document_id, deleted_at__isnull=True)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not document.generated_html:
            return Response({'error': 'This document has not been converted yet.'}, status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(document.generated_html, content_type='text/html')
        response['Content-Security-Policy'] = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
        return response


class HTMLDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        try:
            document = Document.objects.get(id=document_id, deleted_at__isnull=True)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not document.generated_html:
            return Response({'error': 'This document has not been converted yet.'}, status=status.HTTP_404_NOT_FOUND)

        filename = Path(document.title).stem + '.html'
        response = HttpResponse(document.generated_html, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Security-Policy'] = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
        return response


class TemplateCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = [
            {
                'key': key,
                'name': template['name'],
                'description': template['description'],
            }
            for key, template in TEMPLATE_CATALOG.items()
        ]
        return Response({
            'message': 'Template catalog retrieved successfully.',
            'status': 'success',
            'data': data,
        }, status=status.HTTP_200_OK)


class TemplateSelectionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, document_id):
        try:
            document = Document.objects.get(id=document_id, deleted_at__isnull=True)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

        template_name = request.data.get('template')
        if template_name not in TEMPLATE_CATALOG:
            return Response({'error': 'Unsupported lesson template.'}, status=status.HTTP_400_BAD_REQUEST)

        document.selected_template = template_name
        document.save(update_fields=['selected_template', 'updated_at'])

        return Response({
            'message': 'Template selected successfully.',
            'status': 'success',
            'data': {'template': template_name},
        }, status=status.HTTP_200_OK)


class GenerateDocumentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, document_id):
        try:
            document = Document.objects.get(id=document_id, deleted_at__isnull=True)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not document.extracted_data:
            return Response({'error': 'Extract the document before selecting a template.'}, status=status.HTTP_400_BAD_REQUEST)

        template_key = request.data.get('template', document.selected_template or 'academy')
        if template_key not in TEMPLATE_CATALOG:
            template_key = 'academy'

        document.selected_template = template_key
        document.generated_html = generate_template_html(document, document.extracted_data, template_key)
        document.status = 'completed'
        document.save(update_fields=['selected_template', 'generated_html', 'status', 'updated_at'])

        return Response({
            'message': 'Lesson generated successfully.',
            'status': 'success',
            'template': template_key,
            'progress': 100,
        }, status=status.HTTP_200_OK)


class AssetsDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        try:
            document = Document.objects.get(id=document_id, deleted_at__isnull=True)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not document.generated_html:
            return Response({'error': 'This document has not been converted yet.'}, status=status.HTTP_404_NOT_FOUND)

        html = document.generated_html
        html = html.replace('/media/', 'assets/')
        html = html.replace('/static/brand/telesom-academy-logo.png', 'assets/telesom-academy-logo.png')

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('lesson.html', html)

            image_folder = Path(settings.MEDIA_ROOT) / 'extracted_images' / f'document_{document.id}'
            if image_folder.exists():
                for image_path in sorted(image_folder.iterdir()):
                    if image_path.is_file():
                        archive.write(image_path, arcname=f'assets/{image_path.name}')

            logo_path = Path(settings.BASE_DIR) / 'static' / 'brand' / 'telesom-academy-logo.png'
            if logo_path.exists():
                archive.write(logo_path, arcname='assets/telesom-academy-logo.png')

        buffer.seek(0)
        filename = Path(document.title).stem + '-lesson.zip'
        response = HttpResponse(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
