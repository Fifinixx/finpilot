from unittest import mock

from django.urls import reverse
from rest_framework.test import APITestCase


class HealthTests(APITestCase):
    def test_healthy_without_authentication(self):
        res = self.client.get(reverse("health"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, {"status": "ok", "checks": {"api": "ok", "database": "ok"}})

    def test_database_down_returns_503_without_details(self):
        with mock.patch("core.views.connection.cursor", side_effect=Exception("password=secret")), \
                self.assertLogs("finpilot.health", level="ERROR"):
            res = self.client.get(reverse("health"))
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.data["checks"]["database"], "unavailable")
        self.assertNotIn("secret", str(res.content))
