import datetime as dt
from decimal import Decimal

from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import Account, Customer, Goal, Holding, Instrument, RiskProfile, Transaction

SNAP = dt.date(2026, 9, 18)


def make_customer(cid, name="Test", city="Pune", email=None):
    return Customer.objects.create(
        id=cid, full_name=name, email=email or f"{cid.lower()}@example.test", phone="1", city=city, state="MH",
        date_of_birth=dt.date(1990, 1, 1), onboarded_at=dt.date(2024, 1, 1), kyc_status="VERIFIED", segment="Mass",
    )


def make_instrument(iid, asset_class, price):
    return Instrument.objects.create(
        id=iid, symbol=iid, name=f"Inst {iid}", asset_class=asset_class, exchange="NSE", currency="INR",
        last_price=Decimal(price), price_as_of=SNAP, risk_band="LOW",
    )


class PortfolioApiTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(User.objects.create_user(email="v@example.com", password="x"))
        self.c = make_customer("C1", name="Asha Rao", city="Mumbai")
        make_customer("C2", name="Ravi Iyer", city="Pune")
        self.a1 = Account.objects.create(id="A1", customer=self.c, account_type="BROKERAGE", provider="P",
                                         opened_at=dt.date(2024, 1, 1), status="ACTIVE", base_currency="INR")
        self.a2 = Account.objects.create(id="A2", customer=self.c, account_type="RETIREMENT", provider="P",
                                         opened_at=dt.date(2024, 1, 1), status="ACTIVE", base_currency="INR")
        eq, bond = make_instrument("EQ1", "EQUITY", "150"), make_instrument("BD1", "BOND", "100")
        # A1: 10 x EQ1 bought at 100 (now 150) -> MV 1500, gain 500
        Holding.objects.create(account=self.a1, instrument=eq, quantity=10, avg_cost=100, snapshot_date=SNAP)
        # A2: 5 x BD1 bought at 120 (now 100) -> MV 500, loss 100
        Holding.objects.create(account=self.a2, instrument=bond, quantity=5, avg_cost=120, snapshot_date=SNAP)
        # Older snapshot must be ignored
        Holding.objects.create(account=self.a1, instrument=bond, quantity=99, avg_cost=1,
                               snapshot_date=SNAP - dt.timedelta(days=1))
        RiskProfile.objects.create(customer=self.c, risk_score=40, risk_level="Moderate",
                                   assessed_at=dt.date(2025, 1, 1), horizon_years=5, liquidity_need="LOW")
        RiskProfile.objects.create(customer=self.c, risk_score=80, risk_level="Aggressive",
                                   assessed_at=dt.date(2026, 1, 1), horizon_years=10, liquidity_need="HIGH")

    def test_portfolio_totals_allocation_and_positions(self):
        res = self.client.get(reverse("customer-portfolio", args=["C1"]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        d = res.data
        self.assertEqual(d["snapshot_date"], "2026-09-18")
        self.assertEqual(d["price_as_of"], "2026-09-18")
        self.assertEqual(d["totals"]["market_value"], "2000.00")
        self.assertEqual(d["totals"]["cost_basis"], "1600.00")
        self.assertEqual(d["totals"]["unrealised_gain"], "400.00")
        self.assertEqual(d["totals"]["unrealised_gain_pct"], "25.00")
        self.assertEqual(d["totals"]["position_count"], 2)
        self.assertEqual(
            [(a["asset_class"], a["market_value"], a["weight_pct"]) for a in d["allocation"]],
            [("EQUITY", "1500.00", "75.00"), ("BOND", "500.00", "25.00")],
        )
        by_account = {a["account_id"]: a for a in d["accounts"]}
        self.assertEqual(by_account["A1"]["unrealised_gain"], "500.00")
        self.assertEqual(by_account["A2"]["unrealised_gain"], "-100.00")
        self.assertEqual(d["positions"][0]["symbol"], "EQ1")

    def test_portfolio_query_count_is_constant(self):
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("customer-portfolio", args=["C1"]))
        self.assertLessEqual(len(ctx), 8)

    def test_customer_without_holdings_gets_empty_portfolio(self):
        res = self.client.get(reverse("customer-portfolio", args=["C2"]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["totals"]["market_value"], "0.00")
        self.assertEqual(res.data["positions"], [])

    def test_unknown_customer_is_404(self):
        self.assertEqual(self.client.get(reverse("customer-portfolio", args=["NOPE"])).status_code, 404)

    def test_customer_detail_includes_latest_risk_profile(self):
        res = self.client.get(reverse("customer-detail", args=["C1"]))
        self.assertEqual(res.data["latest_risk_profile"]["risk_level"], "Aggressive")
        self.assertEqual(res.data["account_count"], 2)

    def test_customer_search(self):
        url = reverse("customer-list")
        self.assertEqual([c["id"] for c in self.client.get(url, {"q": "mumbai"}).data["results"]], ["C1"])
        self.assertEqual([c["id"] for c in self.client.get(url, {"q": "ravi"}).data["results"]], ["C2"])
        self.assertEqual([c["id"] for c in self.client.get(url, {"q": "c2"}).data["results"]], ["C2"])
        self.assertEqual(self.client.get(url).data["count"], 2)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("customer-list")).status_code, 401)


class GoalsAndTransactionsApiTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(User.objects.create_user(email="v@example.com", password="x"))
        c = make_customer("C1")
        acc = Account.objects.create(id="A1", customer=c, account_type="BROKERAGE", provider="P",
                                     opened_at=dt.date(2024, 1, 1), status="ACTIVE", base_currency="INR")
        inst = make_instrument("EQ1", "EQUITY", "10")
        Goal.objects.create(id="G1", customer=c, goal_type="TRAVEL", name="Trip", target_amount=1000,
                            current_funded_amount=250, target_date=dt.date(2030, 1, 1), priority="HIGH")
        Goal.objects.create(id="G2", customer=c, goal_type="EDUCATION", name="Old", target_amount=1000,
                            current_funded_amount=100, target_date=dt.date(2020, 1, 1), priority="LOW")
        for i, (ttype, day, st) in enumerate([("BUY", 1, "SETTLED"), ("SELL", 2, "PENDING"),
                                              ("BUY", 3, "REVERSED"), ("FEE", 4, "SETTLED")]):
            trade = ttype in ("BUY", "SELL")
            Transaction.objects.create(
                id=f"T{i}", account=acc, instrument=inst, transaction_type=ttype, trade_date=dt.date(2026, 1, day),
                quantity=1 if trade else 0, price=10 if trade else 0, amount=10, status=st,
            )

    def test_goals_have_funded_pct_and_flags(self):
        res = self.client.get(reverse("customer-goals", args=["C1"]))
        goals = {g["id"]: g for g in res.data["results"]}
        self.assertEqual(goals["G1"]["funded_pct"], 25.0)
        self.assertTrue(goals["G2"]["is_overdue"])
        self.assertFalse(goals["G1"]["is_overdue"])
        self.assertEqual(res.data["summary"]["goal_count"], 2)
        self.assertEqual(res.data["summary"]["flagged_count"], 1)
        self.assertEqual(res.data["summary"]["funded_pct"], "17.50")

    def test_transactions_are_paginated_newest_first(self):
        res = self.client.get(reverse("customer-transactions", args=["C1"]), {"page_size": 2})
        self.assertEqual((res.data["count"], res.data["total_pages"]), (4, 2))
        self.assertEqual([t["id"] for t in res.data["results"]], ["T3", "T2"])

    def test_transaction_filters(self):
        url = reverse("customer-transactions", args=["C1"])
        ids = lambda **p: [t["id"] for t in self.client.get(url, p).data["results"]]
        self.assertEqual(ids(type="BUY"), ["T2", "T0"])
        self.assertEqual(ids(status="PENDING"), ["T1"])
        self.assertEqual(ids(date_from="2026-01-02", date_to="2026-01-03"), ["T2", "T1"])
        self.assertEqual(ids(ordering="trade_date"), ["T0", "T1", "T2", "T3"])

    def test_invalid_filters_return_400(self):
        url = reverse("customer-transactions", args=["C1"])
        self.assertEqual(self.client.get(url, {"type": "SWAP"}).status_code, 400)
        self.assertEqual(self.client.get(url, {"date_from": "nope"}).status_code, 400)
        self.assertEqual(self.client.get(url, {"date_from": "2026-02-01", "date_to": "2026-01-01"}).status_code, 400)


class GoalWriteApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="v@example.com", password="x")
        self.client.force_authenticate(self.user)
        self.customer = make_customer("C1")
        Goal.objects.create(id="G00177", customer=self.customer, goal_type="TRAVEL", name="Trip",
                            target_amount=1000, current_funded_amount=100, target_date=dt.date(2020, 1, 1),
                            priority="LOW")
        self.url = reverse("customer-goals", args=["C1"])
        self.valid = {"goal_type": "EDUCATION", "name": "College", "target_amount": "500000",
                      "current_funded_amount": "50000", "target_date": "2035-06-01", "priority": "HIGH"}

    def test_viewer_can_create_goal_with_next_id(self):
        res = self.client.post(self.url, self.valid, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["id"], "G00178")
        self.assertEqual(res.data["funded_pct"], 10.0)
        self.assertEqual(Goal.objects.get(pk="G00178").customer_id, "C1")

    def test_ids_keep_increasing(self):
        ids = [self.client.post(self.url, self.valid, format="json").data["id"] for _ in range(2)]
        self.assertEqual(ids, ["G00178", "G00179"])

    def test_create_validation_messages(self):
        res = self.client.post(self.url, {**self.valid, "target_amount": "0", "current_funded_amount": "-1",
                                          "target_date": "2020-01-01", "goal_type": "YACHT", "name": "  "},
                               format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["target_amount"], ["Target amount must be greater than 0."])
        self.assertEqual(res.data["current_funded_amount"], ["Funded amount can't be negative."])
        self.assertEqual(res.data["target_date"], ["Target date must be in the future."])
        self.assertIn("goal_type", res.data)
        self.assertIn("name", res.data)

    def test_create_for_unknown_customer_is_404(self):
        res = self.client.post(reverse("customer-goals", args=["NOPE"]), self.valid, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_updates_only_given_fields(self):
        url = reverse("goal-detail", args=["G00177"])
        res = self.client.patch(url, {"current_funded_amount": "400"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["funded_pct"], 40.0)
        goal = Goal.objects.get(pk="G00177")
        self.assertEqual((goal.name, goal.current_funded_amount), ("Trip", Decimal("400")))

    def test_patch_keeps_existing_past_date_but_rejects_new_past_date(self):
        url = reverse("goal-detail", args=["G00177"])
        # Overdue goal: editing another field while re-sending its date is fine.
        ok = self.client.patch(url, {"name": "Trip 2", "target_date": "2020-01-01"}, format="json")
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        bad = self.client.patch(url, {"target_date": "2021-01-01"}, format="json")
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_cannot_move_goal_to_another_customer(self):
        make_customer("C2")
        url = reverse("goal-detail", args=["G00177"])
        self.client.patch(url, {"customer": "C2", "id": "G99999"}, format="json")
        goal = Goal.objects.get(pk="G00177")
        self.assertEqual(goal.customer_id, "C1")

    def test_patch_unknown_goal_is_404(self):
        self.assertEqual(self.client.patch(reverse("goal-detail", args=["G0"]), {}, format="json").status_code, 404)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(self.url, self.valid, format="json").status_code, 401)


class TransactionInstrumentFilterTests(APITestCase):
    def test_instrument_filter_accepts_id_or_symbol(self):
        self.client.force_authenticate(User.objects.create_user(email="v@example.com", password="x"))
        c = make_customer("C1")
        acc = Account.objects.create(id="A1", customer=c, account_type="BROKERAGE", provider="P",
                                     opened_at=dt.date(2024, 1, 1), status="ACTIVE", base_currency="INR")
        inst = Instrument.objects.create(id="I0001", symbol="EQ001", name="E", asset_class="EQUITY", exchange="NSE",
                                         currency="INR", last_price=1, price_as_of=SNAP, risk_band="LOW")
        Transaction.objects.create(id="T1", account=acc, instrument=inst, transaction_type="BUY",
                                   trade_date=dt.date(2026, 1, 1), quantity=1, price=1, amount=1, status="SETTLED")
        url = reverse("customer-transactions", args=["C1"])
        for value in ("I0001", "eq001"):
            self.assertEqual(self.client.get(url, {"instrument": value}).data["count"], 1, value)
        self.assertEqual(self.client.get(url, {"instrument": "EQ999"}).data["count"], 0)
