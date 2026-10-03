from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .factories import make_reference_data, txn_csv

URL = reverse("import-upload", kwargs={"entity": "transactions"})


def upload(data: bytes, name="transactions.csv"):
    return {"file": SimpleUploadedFile(name, data, content_type="text/csv")}


class ImportApiTests(APITestCase):
    def setUp(self):
        make_reference_data()
        self.admin = User.objects.create_user(email="admin@example.com", password="x", role=User.Role.ADMIN)
        self.viewer = User.objects.create_user(email="viewer@example.com", password="x")
        self.data = txn_csv(
            "T1,A00001,I0001,BUY,2026-09-01,10,100,1000,SETTLED",
            "T2,A00001,I9999,BUY,2026-09-01,10,100,1000,SETTLED",
        )

    def test_requires_authentication(self):
        self.assertEqual(self.client.post(URL, upload(self.data)).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_viewer_is_forbidden(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(URL, upload(self.data)).status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_upload_returns_counts_and_rejected_rows(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(URL, upload(self.data))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual((res.data["imported_count"], res.data["rejected_count"]), (1, 1))
        rejection = res.data["rejections"][0]
        self.assertEqual(rejection["row_number"], 3)
        self.assertEqual(rejection["errors"][0]["field"], "instrument_id")
        self.assertEqual(res.data["created_by"], "admin@example.com")

    def test_same_file_twice_returns_409(self):
        self.client.force_authenticate(self.admin)
        first = self.client.post(URL, upload(self.data))
        res = self.client.post(URL, upload(self.data))
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(res.data["previous_batch_id"], first.data["id"])

    def test_bad_header_returns_400(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(URL, upload(b"foo,bar\n1,2"))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Missing required column", res.data["detail"])

    def test_missing_file_returns_400(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(URL, {}).status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_entity_returns_404(self):
        self.client.force_authenticate(self.admin)
        url = reverse("import-upload", kwargs={"entity": "bananas"})
        self.assertEqual(self.client.post(url, upload(self.data)).status_code, status.HTTP_404_NOT_FOUND)

    def test_batch_detail_lists_rejections(self):
        self.client.force_authenticate(self.admin)
        batch_id = self.client.post(URL, upload(self.data)).data["id"]
        res = self.client.get(reverse("import-batch-detail", kwargs={"pk": batch_id}))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["rejections"]), 1)
