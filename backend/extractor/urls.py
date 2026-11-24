
from django.urls import path

from .views import (
    DocumentExtractionView,
    ExtractedDataView,
    HTMLDownloadView,
    HTMLPreviewView,
    PDFExtractionView,
    AssetsDownloadView,
    GenerateDocumentView,
    TemplateCatalogView,
    TemplateSelectionView,
)


urlpatterns = [
    path(
        "<int:document_id>/extract/",
        DocumentExtractionView.as_view(),
        name="document-extract",
    ),
    path(
        "<int:document_id>/pdf-extract/",
        PDFExtractionView.as_view(),
        name="pdf-extract",
    ),
    path(
        "<int:document_id>/data/",
        ExtractedDataView.as_view(),
        name="extracted-data",
    ),
    path(
        "<int:document_id>/preview/",
        HTMLPreviewView.as_view(),
        name="html-preview",
    ),
    path(
        "<int:document_id>/download/",
        HTMLDownloadView.as_view(),
        name="html-download",
    ),
    path(
        "templates/",
        TemplateCatalogView.as_view(),
        name="template-catalog",
    ),
    path(
        "<int:document_id>/select-template/",
        TemplateSelectionView.as_view(),
        name="template-select",
    ),
    path(
        "<int:document_id>/generate/",
        GenerateDocumentView.as_view(),
        name="document-generate",
    ),
    path(
        "<int:document_id>/download-assets/",
        AssetsDownloadView.as_view(),
        name="assets-download",
    ),
]
