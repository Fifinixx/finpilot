from rest_framework import serializers

from .importers import IMPORTERS
from .models import ImportBatch, ImportRejection


class ImportRejectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRejection
        fields = ["row_number", "errors", "raw"]

    def to_representation(self, obj):
        data = super().to_representation(obj)
        # jsonb doesn't preserve key order; present values in the file's column order.
        importer = IMPORTERS.get(obj.batch.entity)
        if importer:
            raw = data["raw"]
            ordered = {c: raw[c] for c in importer.columns if c in raw}
            data["raw"] = ordered | {k: v for k, v in raw.items() if k not in ordered}
        return data


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


class ReconciliationExceptionSerializer(serializers.Serializer):
    exception_type = serializers.CharField()
    entity = serializers.CharField()
    entity_id = serializers.CharField()
    customer_id = serializers.CharField(allow_null=True)
    detail = serializers.CharField()
