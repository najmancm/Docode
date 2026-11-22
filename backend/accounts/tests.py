from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthenticationTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin-test',
            email='admin@example.com',
            password='Strong-Test-Password-2026!',
        )

    def test_login_and_me(self):
        response = self.client.post(
            reverse('auth-login'),
            {'username': 'admin-test', 'password': 'Strong-Test-Password-2026!'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        me_response = self.client.get(reverse('auth-me'))
        self.assertEqual(me_response.status_code, 200)
        self.assertTrue(me_response.json()['authenticated'])

    def test_logout(self):
        self.client.login(username='admin-test', password='Strong-Test-Password-2026!')
        response = self.client.post(reverse('auth-logout'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['authenticated'])

    def test_me_requires_authentication(self):
        response = self.client.get(reverse('auth-me'))
        self.assertEqual(response.status_code, 403)

    def test_non_staff_user_cannot_login_as_administrator(self):
        User.objects.create_user(
            username='ordinary-user',
            password='Strong-Test-Password-2026!',
        )
        response = self.client.post(
            reverse('auth-login'),
            {'username': 'ordinary-user', 'password': 'Strong-Test-Password-2026!'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
