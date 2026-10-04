from django.utils import timezone
from rest_framework import serializers

from .models import Account, Customer, Goal, RiskProfile, Transaction


class RiskProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskProfile
        fields = ["risk_score", "risk_level", "assessed_at", "horizon_years", "liquidity_need"]


class CustomerListSerializer(serializers.ModelSerializer):
    account_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "full_name", "email", "city", "state", "kyc_status", "segment", "account_count"]


class CustomerDetailSerializer(serializers.ModelSerializer):
    account_count = serializers.IntegerField(read_only=True)
    latest_risk_profile = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ["id", "full_name", "email", "phone", "city", "state", "date_of_birth", "onboarded_at",
                  "kyc_status", "segment", "account_count", "latest_risk_profile"]

    def get_latest_risk_profile(self, obj) -> RiskProfileSerializer(allow_null=True):
        risk = self.context.get("latest_risk_profile")
        return RiskProfileSerializer(risk).data if risk else None


# --- Portfolio (response-only; documents the shape built in selectors.customer_portfolio) ---

class _MoneyTotals(serializers.Serializer):
    market_value = serializers.DecimalField(max_digits=30, decimal_places=2)
    cost_basis = serializers.DecimalField(max_digits=30, decimal_places=2)
    unrealised_gain = serializers.DecimalField(max_digits=30, decimal_places=2)
    unrealised_gain_pct = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)


class PortfolioTotalsSerializer(_MoneyTotals):
    position_count = serializers.IntegerField()


class PortfolioAccountSerializer(_MoneyTotals):
    account_id = serializers.CharField()
    account_type = serializers.ChoiceField(choices=Account.AccountType.choices)
    provider = serializers.CharField()
    status = serializers.ChoiceField(choices=Account.Status.choices)
    opened_at = serializers.DateField()
    base_currency = serializers.CharField()


class AllocationSerializer(serializers.Serializer):
    asset_class = serializers.CharField()
    market_value = serializers.DecimalField(max_digits=30, decimal_places=2)
    weight_pct = serializers.DecimalField(max_digits=6, decimal_places=2)


class PositionSerializer(serializers.Serializer):
    account_id = serializers.CharField()
    instrument_id = serializers.CharField()
    symbol = serializers.CharField()
    name = serializers.CharField()
    asset_class = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=20, decimal_places=6, normalize_output=True)
    avg_cost = serializers.DecimalField(max_digits=18, decimal_places=4, normalize_output=True)
    last_price = serializers.DecimalField(max_digits=18, decimal_places=4, normalize_output=True)
    price_as_of = serializers.DateField()
    market_value = serializers.DecimalField(max_digits=30, decimal_places=2)
    cost_basis = serializers.DecimalField(max_digits=30, decimal_places=2)
    unrealised_gain = serializers.DecimalField(max_digits=30, decimal_places=2)
    unrealised_gain_pct = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)


class PortfolioSerializer(serializers.Serializer):
    snapshot_date = serializers.DateField(allow_null=True)
    price_as_of = serializers.DateField(allow_null=True)
    prices_mixed_dates = serializers.BooleanField()
    totals = PortfolioTotalsSerializer()
    accounts = PortfolioAccountSerializer(many=True)
    allocation = AllocationSerializer(many=True)
    positions = PositionSerializer(many=True)


# --- Goals ---

class GoalSerializer(serializers.ModelSerializer):
    funded_pct = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    is_overfunded = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = ["id", "goal_type", "name", "target_amount", "current_funded_amount", "funded_pct",
                  "target_date", "priority", "is_overdue", "is_overfunded"]

    def get_funded_pct(self, obj) -> float:
        return round(float(obj.current_funded_amount / obj.target_amount * 100), 2)

    def get_is_overdue(self, obj) -> bool:
        return obj.target_date < timezone.localdate() and obj.current_funded_amount < obj.target_amount

    def get_is_overfunded(self, obj) -> bool:
        return obj.current_funded_amount > obj.target_amount


class GoalSummarySerializer(serializers.Serializer):
    goal_count = serializers.IntegerField()
    total_target = serializers.DecimalField(max_digits=30, decimal_places=2)
    total_funded = serializers.DecimalField(max_digits=30, decimal_places=2)
    funded_pct = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    flagged_count = serializers.IntegerField()


class GoalListSerializer(serializers.Serializer):
    summary = GoalSummarySerializer()
    results = GoalSerializer(many=True)


# --- Transactions ---

class TransactionSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="instrument.symbol")
    instrument_name = serializers.CharField(source="instrument.name")
    quantity = serializers.DecimalField(max_digits=20, decimal_places=6, normalize_output=True)
    price = serializers.DecimalField(max_digits=18, decimal_places=4, normalize_output=True)

    class Meta:
        model = Transaction
        fields = ["id", "account_id", "instrument_id", "symbol", "instrument_name", "transaction_type",
                  "trade_date", "quantity", "price", "amount", "status"]


class TransactionFilterSerializer(serializers.Serializer):
    """Validates query parameters so bad filters get a 400, not a 500 or a silent no-op."""

    ORDERING = ["trade_date", "-trade_date", "amount", "-amount"]

    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    account = serializers.CharField(required=False, max_length=10)
    instrument = serializers.CharField(required=False, max_length=10)
    type = serializers.ChoiceField(choices=Transaction.Type.choices, required=False)
    status = serializers.ChoiceField(choices=Transaction.Status.choices, required=False)
    ordering = serializers.ChoiceField(choices=ORDERING, required=False, default="-trade_date")

    def validate(self, attrs):
        if attrs.get("date_from") and attrs.get("date_to") and attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError({"date_to": "must be on or after date_from"})
        return attrs
