"""
Read-side queries. All aggregation (sums, allocation, gains) runs in
PostgreSQL; Python only shapes the results.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Max, Min, Q, Sum, Value
from django.db.models.functions import Coalesce

from .models import Account, Customer, Holding, RiskProfile

MONEY = DecimalField(max_digits=30, decimal_places=4)
ZERO = Value(Decimal("0"), output_field=MONEY)
CENT = Decimal("0.01")


def money(value) -> Decimal:
    return (value or Decimal("0")).quantize(CENT, rounding=ROUND_HALF_UP)


def search_customers(q: str = "", kyc_status: str = "", segment: str = "", city: str = ""):
    qs = Customer.objects.annotate(account_count=Count("accounts"))
    if q:
        qs = qs.filter(
            Q(id__iexact=q) | Q(full_name__icontains=q) | Q(email__icontains=q) | Q(city__icontains=q)
        )
    if kyc_status:
        qs = qs.filter(kyc_status=kyc_status)
    if segment:
        qs = qs.filter(segment=segment)
    if city:
        qs = qs.filter(city__iexact=city)
    return qs.order_by("id")


def latest_risk_profile(customer_id: str):
    return RiskProfile.objects.filter(customer_id=customer_id).order_by("-assessed_at").first()


def _positions(customer_id: str, snapshot_date):
    market_value = ExpressionWrapper(F("quantity") * F("instrument__last_price"), output_field=MONEY)
    cost_basis = ExpressionWrapper(F("quantity") * F("avg_cost"), output_field=MONEY)
    return (
        Holding.objects.filter(account__customer_id=customer_id, snapshot_date=snapshot_date)
        .select_related("instrument")
        .annotate(market_value=market_value, cost_basis=cost_basis)
        .annotate(unrealised_gain=F("market_value") - F("cost_basis"))
    )


def customer_portfolio(customer_id: str) -> dict:
    """Customer + account totals, asset allocation and positions for the latest snapshot."""
    snapshot_date = Holding.objects.filter(account__customer_id=customer_id).aggregate(d=Max("snapshot_date"))["d"]
    accounts = list(Account.objects.filter(customer_id=customer_id).order_by("id"))

    if snapshot_date is None:
        return {
            "snapshot_date": None, "price_as_of": None, "prices_mixed_dates": False,
            "totals": _totals({}) | {"position_count": 0}, "accounts": [_account(a, {}) for a in accounts],
            "allocation": [], "positions": [],
        }

    positions = _positions(customer_id, snapshot_date)
    # Aliases must differ from the per-row annotation names they sum.
    sums = {
        "mv": Coalesce(Sum("market_value"), ZERO),
        "cost": Coalesce(Sum("cost_basis"), ZERO),
        "gain": Coalesce(Sum("unrealised_gain"), ZERO),
    }

    totals = positions.aggregate(
        **sums,
        position_count=Count("id"),
        price_from=Min("instrument__price_as_of"),
        price_to=Max("instrument__price_as_of"),
    )
    by_account = {row["account_id"]: row for row in positions.values("account_id").annotate(**sums)}
    allocation = positions.values("instrument__asset_class").annotate(**sums).order_by("-mv")

    total_mv = totals["mv"]
    return {
        "snapshot_date": snapshot_date,
        # Oldest price used, so stale prices are never hidden behind a newer one.
        "price_as_of": totals["price_from"],
        "prices_mixed_dates": totals["price_from"] != totals["price_to"],
        "totals": _totals(totals) | {"position_count": totals["position_count"]},
        "accounts": [_account(a, by_account.get(a.id, {})) for a in accounts],
        "allocation": [
            {
                "asset_class": row["instrument__asset_class"],
                "market_value": money(row["mv"]),
                "weight_pct": money(row["mv"] / total_mv * 100) if total_mv else Decimal("0.00"),
            }
            for row in allocation
        ],
        "positions": [
            {
                "account_id": h.account_id,
                "instrument_id": h.instrument_id,
                "symbol": h.instrument.symbol,
                "name": h.instrument.name,
                "asset_class": h.instrument.asset_class,
                "quantity": h.quantity.normalize(),
                "avg_cost": h.avg_cost,
                "last_price": h.instrument.last_price,
                "price_as_of": h.instrument.price_as_of,
                "market_value": money(h.market_value),
                "cost_basis": money(h.cost_basis),
                "unrealised_gain": money(h.unrealised_gain),
                "unrealised_gain_pct": money(h.unrealised_gain / h.cost_basis * 100) if h.cost_basis else None,
            }
            for h in positions.order_by("-market_value")
        ],
    }


def _totals(row: dict) -> dict:
    mv, cost, gain = (row.get(k) for k in ("mv", "cost", "gain"))
    return {
        "market_value": money(mv),
        "cost_basis": money(cost),
        "unrealised_gain": money(gain),
        "unrealised_gain_pct": money(gain / cost * 100) if cost else None,
    }


def _account(account: Account, row: dict) -> dict:
    return {
        "account_id": account.id,
        "account_type": account.account_type,
        "provider": account.provider,
        "status": account.status,
        "opened_at": account.opened_at,
        "base_currency": account.base_currency,
        **_totals(row),
    }
