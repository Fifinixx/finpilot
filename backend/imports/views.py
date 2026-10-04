from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from backend.pagination import StandardPagination

from .importers import IMPORTERS
from .models import ImportBatch
from .serializers import ImportBatchDetailSerializer, ImportBatchSerializer, ImportUploadSerializer
from .services import DuplicateFileError, ImportFileError, run_import

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

EXAMPLE_RESULT = {
    "id": 7, "entity": "transactions", "file_name": "transactions.csv", "status": "COMPLETED",
    "total_rows": 4554, "imported_count": 4550, "duplicate_count": 1, "rejected_count": 3,
    "error": "", "created_by": "admin@finpilot.local", "created_at": "2026-10-05T10:00:00Z",
    "rejections": [{
        "row_number": 4553,
        "errors": [{"field": "instrument_id", "message": "instrument 'I9999' does not exist"}],
        "raw": {"transaction_id": "T0004551", "account_id": "A00001", "instrument_id": "I9999",
                "transaction_type": "BUY", "trade_date": "2026-09-15", "quantity": "10",
                "price": "100", "amount": "1000", "status": "SETTLED"},
    }],
}


class ImportUploadView(APIView):
    """Upload a CSV for one entity. Valid rows are merged; invalid rows are returned with reasons."""

    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser]

    @extend_schema(
        summary="Import a CSV file",
        description=f"`entity` is one of: {', '.join(IMPORTERS)}. Re-uploading an identical file returns 409.",
        request={"multipart/form-data": ImportUploadSerializer},
        responses={
            201: ImportBatchDetailSerializer,
            400: OpenApiResponse(description="Unreadable file or missing columns"),
            403: OpenApiResponse(description="ADMIN role required"),
            409: OpenApiResponse(description="Identical file already imported"),
        },
        examples=[OpenApiExample("Transactions import", value=EXAMPLE_RESULT, response_only=True, status_codes=["201"])],
    )
    def post(self, request, entity):
        importer = IMPORTERS.get(entity)
        if importer is None:
            raise NotFound(f"Unknown import type '{entity}'. Expected one of: {', '.join(IMPORTERS)}.")

        upload = ImportUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        file = upload.validated_data["file"]
        if file.size > MAX_UPLOAD_BYTES:
            return Response({"detail": "File is larger than 10 MB."}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        try:
            batch = run_import(importer, file.read(), file.name, user=request.user)
        except DuplicateFileError as exc:
            return Response(
                {"detail": str(exc), "previous_batch_id": exc.previous.pk}, status=status.HTTP_409_CONFLICT
            )
        except ImportFileError as exc:
            return Response(
                {"detail": str(exc), "batch_id": exc.batch.pk if exc.batch else None},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(ImportBatchDetailSerializer(batch).data, status=status.HTTP_201_CREATED)


class ImportBatchListView(generics.ListAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = ImportBatchSerializer
    pagination_class = StandardPagination
    queryset = ImportBatch.objects.select_related("created_by")


class ImportBatchDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = ImportBatchDetailSerializer
    queryset = ImportBatch.objects.select_related("created_by").prefetch_related("rejections__batch")
