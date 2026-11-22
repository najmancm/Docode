from django.db import models


class Document(models.Model):
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('deleted', 'Deleted'),
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
    updated_at = models.DateTimeField(auto_now=True)

    extracted_data = models.JSONField(
        null=True,
        blank=True
    )

    generated_html = models.TextField(
        null=True,
        blank=True
    )

    conversion_error = models.TextField(
        null=True,
        blank=True,
        default=None,
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    selected_template = models.CharField(
        max_length=20,
        choices=[
            ('academy', 'Academy'),
            ('editorial', 'Editorial'),
            ('interactive', 'Interactive'),
            ('presentation', 'Presentation'),
        ],
        default='academy',
    )

    def soft_delete(self):
        from django.utils import timezone

        self.deleted_at = timezone.now()
        self.status = 'deleted'
        self.save(update_fields=['deleted_at', 'status', 'updated_at'])

    def __str__(self):
        return self.title
