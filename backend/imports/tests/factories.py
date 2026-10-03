import datetime as dt
from decimal import Decimal

from portfolio.models import Account, Customer, Instrument

TODAY = dt.date(2026, 10, 5)


def make_reference_data():
    customer = Customer.objects.create(
        id="C0001", full_name="Test Customer", email="test@example.test", phone="+910000000000",
        city="Mumbai", state="MH", date_of_birth=dt.date(1990, 1, 1), onboarded_at=dt.date(2024, 1, 1),
        kyc_status="VERIFIED", segment="Mass",
    )
    Account.objects.create(
        id="A00001", customer=customer, account_type="BROKERAGE", provider="Test",
        opened_at=dt.date(2024, 1, 1), status="ACTIVE", base_currency="INR",
    )
    Instrument.objects.create(
        id="I0001", symbol="EQ001", name="Test Equity", asset_class="EQUITY", sector="Tech",
        exchange="NSE", currency="INR", last_price=Decimal("100"), price_as_of=dt.date(2026, 9, 18),
        risk_band="LOW",
    )


TXN_HEADER = "transaction_id,account_id,instrument_id,transaction_type,trade_date,quantity,price,amount,status"


def txn_csv(*rows: str) -> bytes:
    return "\n".join([TXN_HEADER, *rows]).encode()
