from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.test import TestCase

from imports.importers import DEFAULT_FILES, IMPORTERS, CustomerImporter, TransactionImporter
from imports.models import ImportBatch
from imports.services import DuplicateFileError, ImportFileError, run_import
from portfolio.models import Holding, Transaction

from .factories import TODAY, make_reference_data, txn_csv

VALID = "T1,A00001,I0001,BUY,2026-09-01,10,100,1000,SETTLED"


def messages(batch):
    return [e["message"] for r in batch.rejections.all() for e in r.errors]


class TransactionImportTests(TestCase):
    def setUp(self):
        make_reference_data()

    def run_txns(self, *rows):
        return run_import(TransactionImporter, txn_csv(*rows), "t.csv", today=TODAY)

    def test_valid_rows_are_imported_and_linked_to_batch(self):
        batch = self.run_txns(VALID, "T2,A00001,I0001,DIVIDEND,2026-09-02,0,0,55.5,SETTLED")
        self.assertEqual((batch.imported_count, batch.rejected_count, batch.duplicate_count), (2, 0, 0))
        self.assertEqual(Transaction.objects.get(pk="T1").import_batch, batch)

    def test_unknown_instrument_is_rejected(self):
        batch = self.run_txns("T1,A00001,I9999,BUY,2026-09-01,10,100,1000,SETTLED")
        self.assertEqual(batch.rejected_count, 1)
        self.assertIn("instrument 'I9999' does not exist", messages(batch))
        self.assertFalse(Transaction.objects.exists())

    def test_negative_amount_is_rejected(self):
        batch = self.run_txns("T1,A00001,I0001,FEE,2026-09-01,0,0,-75,SETTLED")
        self.assertIn("must not be negative", messages(batch))

    def test_future_trade_date_is_rejected(self):
        batch = self.run_txns("T1,A00001,I0001,BUY,2027-01-05,2,210,420,PENDING")
        self.assertIn("2027-01-05 is in the future", messages(batch))

    def test_all_errors_in_a_row_are_reported_together(self):
        batch = self.run_txns("T1,A99999,I0001,SWAP,not-a-date,x,100,1000,SETTLED")
        fields = {e["field"] for e in batch.rejections.get().errors}
        self.assertEqual(fields, {"account_id", "transaction_type", "trade_date", "quantity"})

    def test_trade_amount_must_match_quantity_times_price(self):
        batch = self.run_txns("T1,A00001,I0001,BUY,2026-09-01,10,100,999,SETTLED")
        self.assertEqual(batch.rejected_count, 1)

    def test_cash_event_with_quantity_is_rejected(self):
        batch = self.run_txns("T1,A00001,I0001,FEE,2026-09-01,1,10,10,SETTLED")
        self.assertEqual(batch.rejected_count, 1)

    def test_too_many_decimal_places_is_rejected_not_rounded(self):
        batch = self.run_txns("T1,A00001,I0001,DIVIDEND,2026-09-01,0,0,10.123,SETTLED")
        self.assertIn("'10.123' has more than 2 decimal places", messages(batch))

    def test_exact_duplicate_in_file_is_skipped(self):
        batch = self.run_txns(VALID, VALID)
        self.assertEqual((batch.imported_count, batch.duplicate_count, batch.rejected_count), (1, 1, 0))

    def test_conflicting_duplicate_in_file_is_rejected(self):
        batch = self.run_txns(VALID, "T1,A00001,I0001,BUY,2026-09-01,20,100,2000,SETTLED")
        self.assertEqual((batch.imported_count, batch.rejected_count), (1, 1))
        self.assertEqual(batch.rejections.get().row_number, 3)

    def test_existing_record_is_never_overwritten(self):
        self.run_txns(VALID)
        batch = self.run_txns("T1,A00001,I0001,BUY,2026-09-01,20,100,2000,SETTLED")
        self.assertEqual(batch.rejected_count, 1)
        self.assertEqual(Transaction.objects.get(pk="T1").quantity, Decimal("10"))

    def test_resending_existing_rows_in_a_new_file_counts_duplicates(self):
        self.run_txns(VALID)
        batch = self.run_txns(VALID, "T2,A00001,I0001,BUY,2026-09-01,1,100,100,SETTLED")
        self.assertEqual((batch.imported_count, batch.duplicate_count), (1, 1))

    def test_identical_file_is_refused(self):
        first = self.run_txns(VALID)
        with self.assertRaises(DuplicateFileError) as ctx:
            self.run_txns(VALID)
        self.assertEqual(ctx.exception.previous, first)

    def test_missing_column_fails_whole_file(self):
        with self.assertRaises(ImportFileError) as ctx:
            run_import(TransactionImporter, b"transaction_id,account_id\nT1,A00001", "t.csv", today=TODAY)
        self.assertIn("instrument_id", str(ctx.exception))
        self.assertEqual(ctx.exception.batch.status, ImportBatch.Status.FAILED)
        self.assertFalse(Transaction.objects.exists())


class CustomerImportTests(TestCase):
    HEADER = "customer_id,full_name,email,phone,city,state,date_of_birth,onboarded_at,kyc_status,segment"

    def test_duplicate_email_is_rejected(self):
        data = "\n".join([
            self.HEADER,
            "C1,A,same@example.test,1,Pune,MH,1990-01-01,2024-01-01,VERIFIED,Mass",
            "C2,B,SAME@example.test,2,Pune,MH,1990-01-01,2024-01-01,VERIFIED,Mass",
        ]).encode()
        batch = run_import(CustomerImporter, data, "c.csv", today=TODAY)
        self.assertEqual((batch.imported_count, batch.rejected_count), (1, 1))
        self.assertIn("'same@example.test' is already used by C1", messages(batch))


class SuppliedDatasetTests(TestCase):
    """Loads the real CSVs and pins down how each deliberate anomaly is handled."""

    def test_supplied_files_import_with_expected_anomalies(self):
        data_dir = Path(settings.BASE_DIR.parent / "data")
        results = {}
        for entity, importer in IMPORTERS.items():
            data = (data_dir / DEFAULT_FILES[entity]).read_bytes()
            results[entity] = run_import(importer, data, DEFAULT_FILES[entity], today=TODAY)

        holdings, txns = results["holdings"], results["transactions"]
        self.assertEqual((holdings.imported_count, holdings.duplicate_count, holdings.rejected_count), (982, 3, 0))
        self.assertEqual((txns.imported_count, txns.duplicate_count, txns.rejected_count), (4550, 1, 3))
        rejected_ids = sorted(r.raw["transaction_id"] for r in txns.rejections.all())
        self.assertEqual(rejected_ids, ["T0004551", "T0004552", "T0004553"])
        for entity in ("customers", "accounts", "instruments", "goals", "risk_profiles"):
            self.assertEqual(results[entity].rejected_count, 0, entity)
        self.assertEqual(Holding.objects.count(), 982)
