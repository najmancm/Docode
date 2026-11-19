
from pathlib import Path

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from documents.models import Document
from .services import extract_pdf


class PDFExtractionView(APIView):

    permission_classes = [AllowAny]

    def post(self, request, document_id):

        try:
            document = Document.objects.get(id=document_id)

        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        extension = Path(document.original_file.name).suffix.lower()

        if extension != ".pdf":
            return Response(
                {"error": "Only PDF documents are supported currently."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            extracted_data = extract_pdf(document)

            return Response({
                "message": "PDF extracted successfully!",
                "status": "success",
                "data": extracted_data
            }, status=status.HTTP_200_OK)

        except Exception as error:

            print("PDF EXTRACTION ERROR:", repr(error))

            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )
