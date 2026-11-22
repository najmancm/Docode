import os
from rest_framework import serializers

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    original_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'original_file',
            'original_file_url',
            'file_type',
            'status',
            'uploaded_at',
            'updated_at',
            'extracted_data',
            'generated_html',
            'selected_template',
            'conversion_error',
        ]
        read_only_fields = [
            'id',
            'status',
            'uploaded_at',
            'updated_at',
            'extracted_data',
            'generated_html',
            'conversion_error',
            'selected_template',
            'deleted_at',
        ]

    def get_original_file_url(self, obj):
        if not obj.original_file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.original_file.url)
        return obj.original_file.url

    def validate_original_file(self, file):
        allowed_extensions = ['.pdf', '.pptx', '.ppt', '.docx', '.doc']
        extension = os.path.splitext(file.name)[1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                'Unsupported file format. Upload PDF, PowerPoint, or Word files.'
            )

        max_size = 20 * 1024 * 1024
        if file.size > max_size:
            raise serializers.ValidationError(
                'File is too large. Maximum size is 20 MB.'
            )

        return file
