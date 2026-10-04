import logging

from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("finpilot.health")

HealthResponse = inline_serializer(
    "HealthResponse",
    {"status": serializers.ChoiceField(choices=["ok", "degraded"]), "checks": serializers.DictField()},
)


class HealthView(APIView):
    """Liveness + readiness for load balancers and Docker. Public; reveals no configuration."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: HealthResponse, 503: HealthResponse}, summary="Health check")
    def get(self, request):
        checks = {"api": "ok", "database": "ok"}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            # Details go to the log, never to the (unauthenticated) caller.
            logger.exception("health check: database unreachable")
            checks["database"] = "unavailable"

        healthy = all(v == "ok" for v in checks.values())
        return Response(
            {"status": "ok" if healthy else "degraded", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
