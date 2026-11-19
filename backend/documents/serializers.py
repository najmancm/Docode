
from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'original_file',
            'file_type',
            'status',
            'uploaded_at',
        ]
        read_only_fields = ['id', 'status', 'uploaded_at']
