from rest_framework import serializers

from .models import ImportBatch, ImportRejection


class ImportRejectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRejection
        fields = ["row_number", "errors", "raw"]


class ImportBatchSerializer(serializers.ModelSerializer):
    created_by = serializers.EmailField(source="created_by.email", default=None, read_only=True)

    class Meta:
        model = ImportBatch
        fields = ["id", "entity", "file_name", "status", "total_rows", "imported_count",
                  "duplicate_count", "rejected_count", "error", "created_by", "created_at"]


class ImportBatchDetailSerializer(ImportBatchSerializer):
    rejections = ImportRejectionSerializer(many=True, read_only=True)

    class Meta(ImportBatchSerializer.Meta):
        fields = ImportBatchSerializer.Meta.fields + ["rejections"]


class ImportUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
