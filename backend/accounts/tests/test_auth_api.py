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

    def test_public_registration_is_disabled(self):
        res = self.client.post("/api/v1/auth/register", {"email": "x@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class AdminUserManagementTests(APITestCase):
    URL = reverse("admin-users")

    def setUp(self):
        self.admin = User.objects.create_user(email="admin@example.com", password=PASSWORD, role=User.Role.ADMIN)
        self.viewer = User.objects.create_user(email="viewer@example.com", password=PASSWORD)

    def create(self, **data):
        return self.client.post(self.URL, {"password": PASSWORD, **data}, format="json")

    def test_anonymous_cannot_create_users(self):
        self.assertEqual(self.create(email="new@example.com").status_code, status.HTTP_401_UNAUTHORIZED)

    def test_viewer_cannot_create_users(self):
        self.client.force_authenticate(self.viewer)
        res = self.create(email="new@example.com", role="ADMIN")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_admin_creates_viewer_by_default(self):
        self.client.force_authenticate(self.admin)
        res = self.create(email="New@Example.com")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual((res.data["email"], res.data["role"]), ("new@example.com", "VIEWER"))
        self.assertNotIn("password", res.data)
        self.assertTrue(User.objects.get(email="new@example.com").check_password(PASSWORD))

    def test_admin_can_create_admin(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.create(email="ops@example.com", role="ADMIN").data["role"], "ADMIN")

    def test_creating_a_user_does_not_issue_tokens(self):
        self.client.force_authenticate(self.admin)
        res = self.create(email="new@example.com")
        self.assertNotIn("access", res.data)
        self.assertNotIn(COOKIE, res.cookies)

    def test_rejects_duplicate_email_case_insensitively(self):
        self.client.force_authenticate(self.admin)
        res = self.create(email="VIEWER@example.com")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["email"], ["An account with this email already exists."])

    def test_rejects_weak_password_and_invalid_role(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(self.URL, {"email": "a@example.com", "password": "123", "role": "ROOT"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", res.data)

    def test_admin_can_list_users(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(self.URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual([u["email"] for u in res.data], ["admin@example.com", "viewer@example.com"])

    def test_viewer_cannot_list_users(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_403_FORBIDDEN)
