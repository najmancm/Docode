
import os
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

    def validate_original_file(self, file):
        allowed_extensions = [
            '.pdf',
            '.pptx',
            '.ppt',
            '.docx',
            '.doc',
        ]

        extension = os.path.splitext(file.name)[1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                'Unsupported file format. Upload PDF, PowerPoint, or Word files.'
            )

        max_size = 20 * 1024 * 1024  # 20 MB

        if file.size > max_size:
            raise serializers.ValidationError(
                'File is too large. Maximum size is 20 MB.'
            )

        return file
