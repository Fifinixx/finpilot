from django.conf import settings
from django.db import models
from django.db.models import Q


class ImportBatch(models.Model):
    """One CSV file load: what was sent, by whom, and what happened to each row."""

    class Status(models.TextChoices):
        COMPLETED = "COMPLETED"  # file processed; valid rows merged, invalid rows recorded
        FAILED = "FAILED"  # file-level problem (bad header, unreadable); nothing merged

    entity = models.CharField(max_length=20)
    file_name = models.CharField(max_length=255)
    file_sha256 = models.CharField(max_length=64)
    status = models.CharField(max_length=10, choices=Status.choices)
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # The same file can only be successfully loaded once per entity.
            models.UniqueConstraint(
                fields=["entity", "file_sha256"],
                condition=Q(status="COMPLETED"),
                name="import_batch_unique_completed_file",
            ),
        ]

    def __str__(self):
        return f"{self.entity} {self.file_name} ({self.status})"


class ImportRejection(models.Model):
    """A row that failed validation, kept verbatim with the reasons."""

    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="rejections")
    row_number = models.PositiveIntegerField(help_text="1-based line number in the file, header = line 1")
    raw = models.JSONField()
    errors = models.JSONField(help_text='[{"field": "...", "message": "..."}]')

    class Meta:
        ordering = ["row_number"]
