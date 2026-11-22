from django.utils import timezone
from rest_framework import generics
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from .models import Document
from .serializers import DocumentSerializer


class DocumentListCreateView(generics.ListCreateAPIView):
    queryset = Document.objects.filter(deleted_at__isnull=True).order_by('-uploaded_at')
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    queryset = Document.objects.filter(deleted_at__isnull=True)
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.status = 'deleted'
        instance.save(update_fields=['deleted_at', 'status', 'updated_at'])
