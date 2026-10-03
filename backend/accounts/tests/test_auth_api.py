from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

COOKIE = settings.JWT_REFRESH_COOKIE["key"]
PASSWORD = "S3cure-Passw0rd!"


class AuthApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="viewer@example.com", password=PASSWORD)

    def login(self, email="viewer@example.com", password=PASSWORD):
        return self.client.post(reverse("auth-login"), {"email": email, "password": password}, format="json")

    def test_login_returns_access_token_and_sets_httponly_refresh_cookie(self):
        res = self.login()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertNotIn("refresh", res.data)
        self.assertEqual(res.data["user"]["role"], "VIEWER")
        self.assertTrue(res.cookies[COOKIE]["httponly"])

    def test_login_is_case_insensitive_on_email(self):
        self.assertEqual(self.login(email="VIEWER@example.com").status_code, status.HTTP_200_OK)

    def test_login_with_bad_password_is_rejected(self):
        res = self.login(password="wrong")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn(COOKIE, res.cookies)

    def test_me_requires_token(self):
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_with_token(self):
        access = self.login().data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        res = self.client.get(reverse("auth-me"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], "viewer@example.com")

    def test_refresh_rotates_cookie_and_old_token_cannot_be_reused(self):
        self.login()
        old_refresh = self.client.cookies[COOKIE].value

        res = self.client.post(reverse("auth-refresh"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertNotEqual(res.cookies[COOKIE].value, old_refresh)

        self.client.cookies[COOKIE] = old_refresh
        self.assertEqual(self.client.post(reverse("auth-refresh")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_without_cookie(self):
        self.assertEqual(self.client.post(reverse("auth-refresh")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_revokes_refresh_token(self):
        self.login()
        refresh = self.client.cookies[COOKIE].value
        self.assertEqual(self.client.post(reverse("auth-logout")).status_code, status.HTTP_204_NO_CONTENT)

        self.client.cookies[COOKIE] = refresh
        self.assertEqual(self.client.post(reverse("auth-refresh")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_register_creates_viewer_even_if_admin_role_requested(self):
        res = self.client.post(
            reverse("auth-register"),
            {"email": "New@Example.com", "password": PASSWORD, "role": "ADMIN"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["user"]["role"], "VIEWER")
        self.assertEqual(res.data["user"]["email"], "new@example.com")

    def test_register_rejects_duplicate_email_and_weak_password(self):
        res = self.client.post(
            reverse("auth-register"), {"email": "viewer@example.com", "password": "123"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["email"], ["An account with this email already exists."])

    def test_register_rejects_email_differing_only_by_case(self):
        res = self.client.post(
            reverse("auth-register"), {"email": "Viewer@Example.com", "password": PASSWORD}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
