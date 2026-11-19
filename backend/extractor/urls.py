
from django.urls import path
from .views import PDFExtractionView

urlpatterns = [
    path(
        '<int:document_id>/extract/',
        PDFExtractionView.as_view(),
        name='pdf-extract'
    ),
]
