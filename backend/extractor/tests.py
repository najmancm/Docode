from django.test import TestCase

# Create your tests here.

import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.base import File
from django.test import TestCase, override_settings
from django.urls import reverse
from docx import Document as WordDocument
from pptx import Presentation

from documents.models import Document


class ExtractorApiTests(TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=Path(self.tempdir.name))
        self.settings_override.enable()

        self.admin = User.objects.create_superuser(
            username='admin-test',
            email='admin@example.com',
            password='Strong-Test-Password-2026!',
        )
        self.client.login(username='admin-test', password='Strong-Test-Password-2026!')

    def tearDown(self):
        self.settings_override.disable()
        self.tempdir.cleanup()

    def create_document(self, name, content=b'test'):
        path = Path(self.tempdir.name) / name
        path.write_bytes(content)
        document = Document(title=name, file_type=Path(name).suffix.lower().lstrip('.'))
        with path.open('rb') as source:
            document.original_file.save(name, File(source), save=True)
        return document

    def test_pptx_conversion(self):
        source = Path(self.tempdir.name) / 'lesson.pptx'
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.placeholders[0].text = 'TELESOM Lesson'
        slide.placeholders[1].text = 'Responsive training content'
        presentation.save(source)

        document = Document(title='lesson.pptx', file_type='pptx')
        with source.open('rb') as upload:
            document.original_file.save('lesson.pptx', File(upload), save=True)

        response = self.client.post(reverse('document-extract', args=[document.id]))
        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertEqual(document.status, 'completed')
        self.assertIn('TELESOM Lesson', document.generated_html)

    def test_docx_conversion(self):
        source = Path(self.tempdir.name) / 'lesson.docx'
        word_document = WordDocument()
        word_document.add_heading('TELESOM Lesson', level=1)
        word_document.add_paragraph('Training paragraph')
        word_document.save(source)

        document = Document(title='lesson.docx', file_type='docx')
        with source.open('rb') as upload:
            document.original_file.save('lesson.docx', File(upload), save=True)

        response = self.client.post(reverse('document-extract', args=[document.id]))
        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertEqual(document.status, 'completed')
        self.assertIn('Training paragraph', document.generated_html)

    def test_legacy_ppt_and_doc_are_explicitly_not_claimed(self):
        for name in ('lesson.ppt', 'lesson.doc'):
            document = self.create_document(name)
            response = self.client.post(reverse('document-extract', args=[document.id]))
            self.assertEqual(response.status_code, 400)
            self.assertIn('verified Office conversion component', response.json()['error'])

    def test_preview_and_download_security(self):
        document = self.create_document('lesson.docx')
        document.generated_html = '<!doctype html><html><body><h1>Lesson</h1><script>bad()</script></body></html>'
        document.status = 'completed'
        document.save()

        preview = self.client.get(reverse('html-preview', args=[document.id]))
        self.assertEqual(preview.status_code, 200)
        self.assertIn('default-src', preview.headers['Content-Security-Policy'])

        download = self.client.get(reverse('html-download', args=[document.id]))
        self.assertEqual(download.status_code, 200)
        self.assertIn('attachment', download.headers['Content-Disposition'])
