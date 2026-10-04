from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from . import selectors
from .models import Customer, Goal, Transaction
from .pagination import StandardPagination
from .serializers import (
    CustomerDetailSerializer, CustomerListSerializer, GoalListSerializer, GoalSerializer, GoalSummarySerializer,
    PortfolioSerializer, TransactionFilterSerializer, TransactionSerializer,
)


def _customer_or_404(customer_id):
    return get_object_or_404(Customer.objects.only("id"), pk=customer_id)


@extend_schema(parameters=[
    OpenApiParameter("q", description="Matches customer ID (exact), name, email or city (contains)"),
    OpenApiParameter("kyc_status", enum=[c for c, _ in Customer.KycStatus.choices]),
    OpenApiParameter("segment", enum=[c for c, _ in Customer.Segment.choices]),
    OpenApiParameter("city"),
])
class CustomerListView(generics.ListAPIView):
    serializer_class = CustomerListSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        p = self.request.query_params
        return selectors.search_customers(
            q=p.get("q", "").strip(), kyc_status=p.get("kyc_status", ""),
            segment=p.get("segment", ""), city=p.get("city", "").strip(),
        )


class CustomerDetailView(generics.RetrieveAPIView):
    serializer_class = CustomerDetailSerializer
    queryset = Customer.objects.annotate(account_count=Count("accounts"))

    def get_serializer_context(self):
        return super().get_serializer_context() | {
            "latest_risk_profile": selectors.latest_risk_profile(self.kwargs["pk"]),
        }


class CustomerPortfolioView(APIView):
    @extend_schema(responses=PortfolioSerializer, summary="Totals, allocation and positions (latest snapshot)")
    def get(self, request, pk):
        _customer_or_404(pk)
        return Response(PortfolioSerializer(selectors.customer_portfolio(pk)).data)


class CustomerGoalsView(APIView):
    @extend_schema(responses=GoalListSerializer)
    def get(self, request, pk):
        _customer_or_404(pk)
        goals = Goal.objects.filter(customer_id=pk)
        today = timezone.localdate()
        summary = goals.aggregate(
            goal_count=Count("id"),
            total_target=Sum("target_amount", default=0),
            total_funded=Sum("current_funded_amount", default=0),
            flagged_count=Count("id", filter=Q(current_funded_amount__gt=F("target_amount"))
                                | Q(target_date__lt=today, current_funded_amount__lt=F("target_amount"))),
        )
        summary["funded_pct"] = (
            round(summary["total_funded"] / summary["total_target"] * 100, 2) if summary["total_target"] else None
        )
        return Response({
            "summary": GoalSummarySerializer(summary).data,
            "results": GoalSerializer(goals, many=True).data,
        })


@extend_schema(parameters=[TransactionFilterSerializer])
class CustomerTransactionsView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        _customer_or_404(self.kwargs["pk"])
        filters = TransactionFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        f = filters.validated_data

        qs = Transaction.objects.filter(account__customer_id=self.kwargs["pk"]).select_related("instrument")
        if "date_from" in f:
            qs = qs.filter(trade_date__gte=f["date_from"])
        if "date_to" in f:
            qs = qs.filter(trade_date__lte=f["date_to"])
        if "account" in f:
            qs = qs.filter(account_id=f["account"])
        if "instrument" in f:
            qs = qs.filter(instrument_id=f["instrument"])
        if "type" in f:
            qs = qs.filter(transaction_type=f["type"])
        if "status" in f:
            qs = qs.filter(status=f["status"])
        # Secondary key keeps pagination stable when many rows share a date.
        return qs.order_by(f["ordering"], "id")
