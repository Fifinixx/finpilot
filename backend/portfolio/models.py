"""
Core domain tables. Natural keys from the source system (C0001, A00001, ...)
are used as primary keys: they are stable, already unique in the source, and
make imports and debugging straightforward.
"""

from django.db import models
from django.db.models import Q


def _in(field, choices):
    return Q(**{f"{field}__in": [value for value, _ in choices.choices]})


class CustomerKycStatus(models.TextChoices):
    VERIFIED = "VERIFIED"
    PENDING = "PENDING"
    REVIEW = "REVIEW"


class CustomerSegment(models.TextChoices):
    MASS = "Mass"
    AFFLUENT = "Affluent"
    HNI = "HNI"


class AccountType(models.TextChoices):
    BROKERAGE = "BROKERAGE"
    MUTUAL_FUND = "MUTUAL_FUND"
    RETIREMENT = "RETIREMENT"


class AccountStatus(models.TextChoices):
    ACTIVE = "ACTIVE"
    DORMANT = "DORMANT"
    CLOSED = "CLOSED"


class InstrumentAssetClass(models.TextChoices):
    EQUITY = "EQUITY"
    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    BOND = "BOND"
    REIT = "REIT"
    GSEC = "GSEC"


class InstrumentExchange(models.TextChoices):
    NSE = "NSE"
    BSE = "BSE"
    OTC = "OTC"


class InstrumentRiskBand(models.TextChoices):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TransactionType(models.TextChoices):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    FEE = "FEE"


class TransactionStatus(models.TextChoices):
    SETTLED = "SETTLED"
    PENDING = "PENDING"
    REVERSED = "REVERSED"


class GoalType(models.TextChoices):
    RETIREMENT = "RETIREMENT"
    EDUCATION = "EDUCATION"
    HOME_PURCHASE = "HOME_PURCHASE"
    EMERGENCY_FUND = "EMERGENCY_FUND"
    WEALTH_CREATION = "WEALTH_CREATION"
    TRAVEL = "TRAVEL"


class GoalPriority(models.TextChoices):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskProfileRiskLevel(models.TextChoices):
    CONSERVATIVE = "Conservative"
    MODERATE = "Moderate"
    GROWTH = "Growth"
    AGGRESSIVE = "Aggressive"


class RiskProfileLiquidity(models.TextChoices):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Customer(models.Model):
    KycStatus = CustomerKycStatus
    Segment = CustomerSegment
    id = models.CharField(primary_key=True, max_length=10)
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    city = models.CharField(max_length=60)
    state = models.CharField(max_length=2)
    date_of_birth = models.DateField()
    onboarded_at = models.DateField()
    kyc_status = models.CharField(max_length=10, choices=KycStatus.choices)
    segment = models.CharField(max_length=10, choices=Segment.choices)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["city"], name="customer_city_idx")]
        constraints = [
            models.CheckConstraint(condition=_in("kyc_status", CustomerKycStatus), name="customer_kyc_status_valid"),
            models.CheckConstraint(condition=_in("segment", CustomerSegment), name="customer_segment_valid"),
        ]

    def __str__(self):
        return f"{self.id} {self.full_name}"


class Account(models.Model):
    AccountType = AccountType
    Status = AccountStatus
    id = models.CharField(primary_key=True, max_length=10)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="accounts")
    account_type = models.CharField(max_length=12, choices=AccountType.choices)
    provider = models.CharField(max_length=80)
    opened_at = models.DateField()
    status = models.CharField(max_length=8, choices=Status.choices)
    base_currency = models.CharField(max_length=3)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=_in("account_type", AccountType), name="account_type_valid"),
            models.CheckConstraint(condition=_in("status", AccountStatus), name="account_status_valid"),
        ]

    def __str__(self):
        return self.id


class Instrument(models.Model):
    AssetClass = InstrumentAssetClass
    Exchange = InstrumentExchange
    RiskBand = InstrumentRiskBand
    id = models.CharField(primary_key=True, max_length=10)
    symbol = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    asset_class = models.CharField(max_length=12, choices=AssetClass.choices)
    sector = models.CharField(max_length=60, blank=True, default="")
    exchange = models.CharField(max_length=3, choices=Exchange.choices)
    currency = models.CharField(max_length=3)
    last_price = models.DecimalField(max_digits=18, decimal_places=4)
    price_as_of = models.DateField()
    risk_band = models.CharField(max_length=6, choices=RiskBand.choices)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=_in("asset_class", InstrumentAssetClass), name="instrument_asset_class_valid"),
            models.CheckConstraint(condition=_in("exchange", InstrumentExchange), name="instrument_exchange_valid"),
            models.CheckConstraint(condition=_in("risk_band", InstrumentRiskBand), name="instrument_risk_band_valid"),
            models.CheckConstraint(condition=Q(last_price__gt=0), name="instrument_last_price_positive"),
        ]

    def __str__(self):
        return f"{self.id} {self.symbol}"


class Holding(models.Model):
    """One end-of-day position: (account, instrument, snapshot_date) is unique."""

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="holdings")
    instrument = models.ForeignKey(Instrument, on_delete=models.PROTECT, related_name="holdings")
    quantity = models.DecimalField(max_digits=20, decimal_places=6)
    avg_cost = models.DecimalField(max_digits=18, decimal_places=4)
    snapshot_date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account", "instrument", "snapshot_date"], name="holding_unique_position_per_snapshot"
            ),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="holding_quantity_positive"),
            models.CheckConstraint(condition=Q(avg_cost__gte=0), name="holding_avg_cost_non_negative"),
        ]
        indexes = [models.Index(fields=["snapshot_date"], name="holding_snapshot_date_idx")]


class Transaction(models.Model):
    Type = TransactionType
    Status = TransactionStatus
    TRADE_TYPES = (Type.BUY, Type.SELL)
    CASH_TYPES = (Type.DIVIDEND, Type.FEE)

    id = models.CharField(primary_key=True, max_length=12)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="transactions")
    instrument = models.ForeignKey(Instrument, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=8, choices=Type.choices)
    trade_date = models.DateField()
    quantity = models.DecimalField(max_digits=20, decimal_places=6)
    price = models.DecimalField(max_digits=18, decimal_places=4)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=8, choices=Status.choices)
    import_batch = models.ForeignKey(
        "imports.ImportBatch", on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions"
    )

    class Meta:
        ordering = ["-trade_date", "id"]
        indexes = [
            # Customer transaction list: filter by account(s), newest first.
            models.Index(fields=["account", "-trade_date"], name="txn_account_date_idx"),
            # Monthly cash-flow reports scan by date.
            models.Index(fields=["trade_date"], name="txn_trade_date_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=_in("transaction_type", TransactionType), name="txn_type_valid"),
            models.CheckConstraint(condition=_in("status", TransactionStatus), name="txn_status_valid"),
            models.CheckConstraint(condition=Q(amount__gte=0), name="txn_amount_non_negative"),
            # Trades need a quantity and price; cash events carry neither.
            models.CheckConstraint(
                condition=(Q(transaction_type__in=["BUY", "SELL"]) & Q(quantity__gt=0) & Q(price__gt=0))
                | (Q(transaction_type__in=["DIVIDEND", "FEE"]) & Q(quantity=0) & Q(price=0)),
                name="txn_quantity_price_match_type",
            ),
        ]

    def __str__(self):
        return self.id


class Goal(models.Model):
    GoalType = GoalType
    Priority = GoalPriority
    id = models.CharField(primary_key=True, max_length=10)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="goals")
    goal_type = models.CharField(max_length=16, choices=GoalType.choices)
    name = models.CharField(max_length=120)
    target_amount = models.DecimalField(max_digits=18, decimal_places=2)
    current_funded_amount = models.DecimalField(max_digits=18, decimal_places=2)
    target_date = models.DateField()
    priority = models.CharField(max_length=6, choices=Priority.choices)

    class Meta:
        ordering = ["target_date", "id"]
        constraints = [
            models.CheckConstraint(condition=_in("goal_type", GoalType), name="goal_type_valid"),
            models.CheckConstraint(condition=_in("priority", GoalPriority), name="goal_priority_valid"),
            models.CheckConstraint(condition=Q(target_amount__gt=0), name="goal_target_positive"),
            models.CheckConstraint(condition=Q(current_funded_amount__gte=0), name="goal_funded_non_negative"),
        ]

    def __str__(self):
        return f"{self.id} {self.name}"


class RiskProfile(models.Model):
    """Risk assessments over time; the latest per customer is the current one."""

    RiskLevel = RiskProfileRiskLevel
    Liquidity = RiskProfileLiquidity
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="risk_profiles")
    risk_score = models.PositiveSmallIntegerField()
    risk_level = models.CharField(max_length=12, choices=RiskLevel.choices)
    assessed_at = models.DateField()
    horizon_years = models.PositiveSmallIntegerField()
    liquidity_need = models.CharField(max_length=6, choices=Liquidity.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["customer", "assessed_at"], name="risk_profile_unique_per_day"),
            models.CheckConstraint(condition=Q(risk_score__lte=100), name="risk_score_max_100"),
            models.CheckConstraint(condition=_in("risk_level", RiskProfileRiskLevel), name="risk_level_valid"),
            models.CheckConstraint(condition=_in("liquidity_need", RiskProfileLiquidity), name="risk_liquidity_valid"),
        ]
        indexes = [models.Index(fields=["customer", "-assessed_at"], name="risk_customer_latest_idx")]
