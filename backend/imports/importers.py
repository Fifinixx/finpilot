"""One importer per CSV file: which columns it needs, how a row maps to a model,
what identifies a record, and the business rules beyond simple types."""

import datetime as dt
from decimal import Decimal

from portfolio.models import Account, Customer, Goal, Holding, Instrument, RiskProfile, Transaction

from .parsing import RowParser

AMOUNT_TOLERANCE = Decimal("0.01")


class BaseImporter:
    entity: str
    model: type
    columns: tuple[str, ...]
    key_label: str  # column(s) that identify a record, for error messages
    compare_fields: tuple[str, ...]  # fields that must match for a re-sent row to count as a duplicate
    unique_fields: tuple[str, ...] = ()

    def __init__(self, rows: list[dict], today: dt.date):
        self.today = today
        self.prepare(rows)

    def prepare(self, rows):
        """Preload whatever lookups parse() needs, in bulk."""

    def parse(self, p: RowParser):
        raise NotImplementedError

    def key(self, obj) -> tuple:
        return (obj.pk,)

    def existing(self, keys: list[tuple]) -> dict:
        return {(pk,): obj for pk, obj in self.model.objects.in_bulk([k[0] for k in keys]).items()}

    def attach_batch(self, obj, batch):
        pass

    @staticmethod
    def _ids(model, rows, col) -> set[str]:
        """IDs referenced in the file that actually exist: one query, not one per row."""
        wanted = {(r.get(col) or "").strip() for r in rows} - {""}
        return set(model.objects.filter(pk__in=wanted).values_list("pk", flat=True))

    def _not_future(self, p, col, value):
        if value and value > self.today:
            p.error(col, f"{value} is in the future")


class CustomerImporter(BaseImporter):
    entity = "customers"
    model = Customer
    columns = ("customer_id", "full_name", "email", "phone", "city", "state",
               "date_of_birth", "onboarded_at", "kyc_status", "segment")
    key_label = "customer_id"
    compare_fields = ("full_name", "email", "phone", "city", "state",
                      "date_of_birth", "onboarded_at", "kyc_status", "segment")
    unique_fields = ("email",)

    def parse(self, p):
        obj = Customer(
            id=p.text("customer_id", 10),
            full_name=p.text("full_name", 120),
            email=p.email("email"),
            phone=p.text("phone", 20),
            city=p.text("city", 60),
            state=p.text("state", 2),
            date_of_birth=p.date("date_of_birth"),
            onboarded_at=p.date("onboarded_at"),
            kyc_status=p.enum("kyc_status", Customer.KycStatus),
            segment=p.enum("segment", Customer.Segment),
        )
        self._not_future(p, "date_of_birth", obj.date_of_birth)
        self._not_future(p, "onboarded_at", obj.onboarded_at)
        if obj.date_of_birth and obj.onboarded_at and obj.onboarded_at < obj.date_of_birth:
            p.error("onboarded_at", "is before date_of_birth")
        return obj if p.ok else None


class AccountImporter(BaseImporter):
    entity = "accounts"
    model = Account
    columns = ("account_id", "customer_id", "account_type", "provider", "opened_at", "status", "base_currency")
    key_label = "account_id"
    compare_fields = ("customer_id", "account_type", "provider", "opened_at", "status", "base_currency")

    def prepare(self, rows):
        self.customers = self._ids(Customer, rows, "customer_id")

    def parse(self, p):
        obj = Account(
            id=p.text("account_id", 10),
            customer_id=p.ref("customer_id", self.customers, "customer"),
            account_type=p.enum("account_type", Account.AccountType),
            provider=p.text("provider", 80),
            opened_at=p.date("opened_at"),
            status=p.enum("status", Account.Status),
            base_currency=p.text("base_currency", 3),
        )
        self._not_future(p, "opened_at", obj.opened_at)
        return obj if p.ok else None


class InstrumentImporter(BaseImporter):
    entity = "instruments"
    model = Instrument
    columns = ("instrument_id", "symbol", "instrument_name", "asset_class", "sector", "exchange",
               "currency", "last_price", "price_as_of", "risk_band")
    key_label = "instrument_id"
    compare_fields = ("symbol", "name", "asset_class", "sector", "exchange",
                      "currency", "last_price", "price_as_of", "risk_band")
    unique_fields = ("symbol",)

    def parse(self, p):
        obj = Instrument(
            id=p.text("instrument_id", 10),
            symbol=p.text("symbol", 20),
            name=p.text("instrument_name", 120),
            asset_class=p.enum("asset_class", Instrument.AssetClass),
            sector=p.text("sector", 60, required=False),
            exchange=p.enum("exchange", Instrument.Exchange),
            currency=p.text("currency", 3),
            last_price=p.decimal("last_price", 18, 4, gt=0),
            price_as_of=p.date("price_as_of"),
            risk_band=p.enum("risk_band", Instrument.RiskBand),
        )
        self._not_future(p, "price_as_of", obj.price_as_of)
        return obj if p.ok else None


class HoldingImporter(BaseImporter):
    entity = "holdings"
    model = Holding
    columns = ("account_id", "instrument_id", "quantity", "avg_cost", "snapshot_date")
    key_label = "account_id/instrument_id/snapshot_date"
    compare_fields = ("quantity", "avg_cost")

    def prepare(self, rows):
        self.accounts = self._ids(Account, rows, "account_id")
        self.instruments = self._ids(Instrument, rows, "instrument_id")

    def parse(self, p):
        obj = Holding(
            account_id=p.ref("account_id", self.accounts, "account"),
            instrument_id=p.ref("instrument_id", self.instruments, "instrument"),
            quantity=p.decimal("quantity", 20, 6, gt=0),
            avg_cost=p.decimal("avg_cost", 18, 4, min_value=0),
            snapshot_date=p.date("snapshot_date"),
        )
        self._not_future(p, "snapshot_date", obj.snapshot_date)
        return obj if p.ok else None

    def key(self, obj):
        return (obj.account_id, obj.instrument_id, obj.snapshot_date)

    def existing(self, keys):
        if not keys:
            return {}
        qs = Holding.objects.filter(
            account_id__in={k[0] for k in keys}, snapshot_date__in={k[2] for k in keys}
        )
        return {self.key(h): h for h in qs}


class TransactionImporter(BaseImporter):
    entity = "transactions"
    model = Transaction
    columns = ("transaction_id", "account_id", "instrument_id", "transaction_type",
               "trade_date", "quantity", "price", "amount", "status")
    key_label = "transaction_id"
    compare_fields = ("account_id", "instrument_id", "transaction_type", "trade_date",
                      "quantity", "price", "amount", "status")

    def prepare(self, rows):
        self.accounts = self._ids(Account, rows, "account_id")
        self.instruments = self._ids(Instrument, rows, "instrument_id")

    def parse(self, p):
        obj = Transaction(
            id=p.text("transaction_id", 12),
            account_id=p.ref("account_id", self.accounts, "account"),
            instrument_id=p.ref("instrument_id", self.instruments, "instrument"),
            transaction_type=p.enum("transaction_type", Transaction.Type),
            trade_date=p.date("trade_date"),
            quantity=p.decimal("quantity", 20, 6, min_value=0),
            price=p.decimal("price", 18, 4, min_value=0),
            amount=p.decimal("amount", 18, 2, min_value=0),
            status=p.enum("status", Transaction.Status),
        )
        self._not_future(p, "trade_date", obj.trade_date)
        if not p.ok:
            return None

        if obj.transaction_type in Transaction.TRADE_TYPES:
            if obj.quantity == 0 or obj.price == 0:
                p.error("quantity", f"{obj.transaction_type} needs a quantity and price greater than 0")
            elif abs(obj.quantity * obj.price - obj.amount) > AMOUNT_TOLERANCE:
                p.error("amount", f"{obj.amount} does not equal quantity x price ({obj.quantity * obj.price:.2f})")
        elif obj.quantity != 0 or obj.price != 0:
            p.error("quantity", f"{obj.transaction_type} is a cash event; quantity and price must be 0")
        return obj if p.ok else None

    def attach_batch(self, obj, batch):
        obj.import_batch = batch


class GoalImporter(BaseImporter):
    entity = "goals"
    model = Goal
    columns = ("goal_id", "customer_id", "goal_type", "goal_name", "target_amount",
               "current_funded_amount", "target_date", "priority")
    key_label = "goal_id"
    compare_fields = ("customer_id", "goal_type", "name", "target_amount",
                      "current_funded_amount", "target_date", "priority")

    def prepare(self, rows):
        self.customers = self._ids(Customer, rows, "customer_id")

    def parse(self, p):
        # Over-funded or overdue goals are valid data; the API flags them for review.
        obj = Goal(
            id=p.text("goal_id", 10),
            customer_id=p.ref("customer_id", self.customers, "customer"),
            goal_type=p.enum("goal_type", Goal.GoalType),
            name=p.text("goal_name", 120),
            target_amount=p.decimal("target_amount", 18, 2, gt=0),
            current_funded_amount=p.decimal("current_funded_amount", 18, 2, min_value=0),
            target_date=p.date("target_date"),
            priority=p.enum("priority", Goal.Priority),
        )
        return obj if p.ok else None


class RiskProfileImporter(BaseImporter):
    entity = "risk_profiles"
    model = RiskProfile
    columns = ("customer_id", "risk_score", "risk_level", "assessed_at", "horizon_years", "liquidity_need")
    key_label = "customer_id/assessed_at"
    compare_fields = ("risk_score", "risk_level", "horizon_years", "liquidity_need")

    def prepare(self, rows):
        self.customers = self._ids(Customer, rows, "customer_id")

    def parse(self, p):
        obj = RiskProfile(
            customer_id=p.ref("customer_id", self.customers, "customer"),
            risk_score=p.integer("risk_score", 0, 100),
            risk_level=p.enum("risk_level", RiskProfile.RiskLevel),
            assessed_at=p.date("assessed_at"),
            horizon_years=p.integer("horizon_years", 0, 100),
            liquidity_need=p.enum("liquidity_need", RiskProfile.Liquidity),
        )
        self._not_future(p, "assessed_at", obj.assessed_at)
        return obj if p.ok else None

    def key(self, obj):
        return (obj.customer_id, obj.assessed_at)

    def existing(self, keys):
        if not keys:
            return {}
        qs = RiskProfile.objects.filter(customer_id__in={k[0] for k in keys})
        return {self.key(r): r for r in qs}


# Dependency order: parents before children.
IMPORTERS = {
    cls.entity: cls
    for cls in (CustomerImporter, AccountImporter, InstrumentImporter, HoldingImporter,
                TransactionImporter, GoalImporter, RiskProfileImporter)
}

# entity -> CSV file name in the data directory
DEFAULT_FILES = {
    "customers": "customers.csv",
    "accounts": "accounts.csv",
    "instruments": "instruments.csv",
    "holdings": "holdings_snapshot.csv",
    "transactions": "transactions.csv",
    "goals": "goals.csv",
    "risk_profiles": "risk_profiles.csv",
}
