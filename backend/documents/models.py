
from django.db import models


class Document(models.Model):
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    title = models.CharField(max_length=255)

    original_file = models.FileField(
        upload_to='documents/'
    )

    file_type = models.CharField(max_length=20)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='uploaded'
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
