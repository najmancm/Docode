
from django.urls import path

from .views import PDFExtractionView, ExtractedDataView


urlpatterns = [
    path(
        '<int:document_id>/extract/',
        PDFExtractionView.as_view(),
        name='pdf-extract'
    ),
    path(
        '<int:document_id>/data/',
        ExtractedDataView.as_view(),
        name='extracted-data'
    ),
]
