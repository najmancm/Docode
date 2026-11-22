from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Document


class DocumentApiTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin-test',
            email='admin@example.com',
            password='Strong-Test-Password-2026!',
        )

    def test_document_list_requires_authentication(self):
        response = self.client.get(reverse('document-list-create'))
        self.assertEqual(response.status_code, 403)

    def test_authenticated_upload_and_soft_delete(self):
        self.client.login(username='admin-test', password='Strong-Test-Password-2026!')
        upload = SimpleUploadedFile(
            'lesson.pdf',
            b'%PDF-1.4 test document',
            content_type='application/pdf',
        )

        response = self.client.post(reverse('document-list-create'), {
            'title': 'lesson.pdf',
            'original_file': upload,
            'file_type': 'pdf',
        })
        self.assertEqual(response.status_code, 201)

        document_id = response.json()['id']
        document = Document.objects.get(id=document_id)
        self.assertIsNone(document.deleted_at)

        delete_response = self.client.delete(reverse('document-detail', args=[document_id]))
        self.assertEqual(delete_response.status_code, 204)

        document.refresh_from_db()
        self.assertIsNotNone(document.deleted_at)
        self.assertEqual(document.status, 'deleted')
        self.assertTrue(document.original_file)

    def test_extension_validation(self):
        self.client.login(username='admin-test', password='Strong-Test-Password-2026!')
        upload = SimpleUploadedFile('lesson.exe', b'MZ', content_type='application/octet-stream')

        response = self.client.post(reverse('document-list-create'), {
            'title': 'lesson.exe',
            'original_file': upload,
            'file_type': 'exe',
        })
        self.assertEqual(response.status_code, 400)
