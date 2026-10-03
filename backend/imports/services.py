"""
CSV import pipeline shared by the admin API and the `import_data` command.

Rules (identical for every entity):
  1. A file whose bytes were already imported successfully is refused (DuplicateFileError).
  2. Missing required columns or an unreadable file fails the whole file (ImportFileError).
  3. Each row is parsed and validated; all of its problems are recorded together.
  4. A row whose key appears earlier in the same file, or already exists in the
     database, is counted as a *duplicate* if identical and *rejected* if it differs.
     Existing records are never overwritten.
  5. Valid rows and the rejection log are written in a single DB transaction.
"""

import csv
import hashlib
import io
import logging
from dataclasses import dataclass, field

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import ImportBatch, ImportRejection
from .parsing import RowParser

logger = logging.getLogger("finpilot.imports")

MAX_ROWS = 200_000


class ImportFileError(Exception):
    def __init__(self, message: str, batch: ImportBatch | None = None):
        super().__init__(message)
        self.batch = batch


class DuplicateFileError(Exception):
    def __init__(self, previous: ImportBatch):
        super().__init__(f"This file was already imported (batch {previous.pk}).")
        self.previous = previous


@dataclass
class _Candidate:
    obj: object
    row_number: int
    raw: dict


@dataclass
class _Outcome:
    to_create: list = field(default_factory=list)
    rejections: list = field(default_factory=list)
    duplicates: int = 0

    def reject(self, row_number, raw, errors):
        self.rejections.append(ImportRejection(row_number=row_number, raw=raw, errors=errors))


def run_import(importer_cls, data: bytes, file_name: str, user=None, today=None) -> ImportBatch:
    entity = importer_cls.entity
    sha256 = hashlib.sha256(data).hexdigest()

    previous = ImportBatch.objects.filter(
        entity=entity, file_sha256=sha256, status=ImportBatch.Status.COMPLETED
    ).first()
    if previous:
        raise DuplicateFileError(previous)

    batch = ImportBatch(entity=entity, file_name=file_name[:255], file_sha256=sha256, created_by=user)

    try:
        rows = _read_rows(data, importer_cls.columns)
    except ImportFileError as exc:
        batch.status = ImportBatch.Status.FAILED
        batch.error = str(exc)
        batch.save()
        logger.warning("import failed entity=%s file=%s batch=%s error=%s", entity, file_name, batch.pk, exc)
        exc.batch = batch
        raise

    importer = importer_cls(rows, today=today or timezone.localdate())
    outcome = _validate(importer, rows)

    batch.status = ImportBatch.Status.COMPLETED
    batch.total_rows = len(rows)
    batch.imported_count = len(outcome.to_create)
    batch.duplicate_count = outcome.duplicates
    batch.rejected_count = len(outcome.rejections)

    try:
        with transaction.atomic():
            batch.save()
            for obj in outcome.to_create:
                importer.attach_batch(obj, batch)
            importer.model.objects.bulk_create(outcome.to_create, batch_size=1000)
            for rejection in outcome.rejections:
                rejection.batch = batch
            ImportRejection.objects.bulk_create(outcome.rejections, batch_size=1000)
    except IntegrityError:
        # Lost a race with a concurrent upload of the same file or same keys.
        previous = ImportBatch.objects.filter(
            entity=entity, file_sha256=sha256, status=ImportBatch.Status.COMPLETED
        ).first()
        if previous:
            raise DuplicateFileError(previous) from None
        raise

    logger.info(
        "import completed entity=%s file=%s batch=%s total=%d imported=%d duplicates=%d rejected=%d",
        entity, file_name, batch.pk, batch.total_rows, batch.imported_count,
        batch.duplicate_count, batch.rejected_count,
    )
    return batch


def _read_rows(data: bytes, required_columns) -> list[dict]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportFileError("File is not valid UTF-8 text.") from None

    reader = csv.DictReader(io.StringIO(text, newline=""))
    header = [h.strip() for h in (reader.fieldnames or [])]
    if not header:
        raise ImportFileError("File is empty.")
    missing = [c for c in required_columns if c not in header]
    if missing:
        raise ImportFileError(f"Missing required column(s): {', '.join(missing)}.")
    reader.fieldnames = header

    rows = []
    for raw in reader:
        if len(rows) >= MAX_ROWS:
            raise ImportFileError(f"File has more than {MAX_ROWS} rows.")
        if None in raw:  # more values than header columns
            raw = {k: v for k, v in raw.items() if k is not None} | {"__extra__": "unexpected extra values"}
        rows.append(raw)
    return rows


def _same(a, b, fields) -> bool:
    return all(getattr(a, f) == getattr(b, f) for f in fields)


def _validate(importer, rows) -> _Outcome:
    outcome = _Outcome()
    seen: dict[tuple, _Candidate] = {}

    # Pass 1: parse rows, catch duplicates within the file.
    for row_number, raw in enumerate(rows, start=2):  # line 1 is the header
        parser = RowParser(raw)
        if "__extra__" in raw:
            parser.error("row", "has more values than the header")
        obj = importer.parse(parser) if parser.ok else None
        if obj is None:
            outcome.reject(row_number, parser.raw, parser.errors)
            continue

        key = importer.key(obj)
        if key in seen:
            first = seen[key]
            if _same(obj, first.obj, importer.compare_fields):
                outcome.duplicates += 1
            else:
                outcome.reject(row_number, parser.raw, [{
                    "field": importer.key_label,
                    "message": f"duplicate key {_fmt(key)} with different values (first seen on line {first.row_number})",
                }])
            continue
        seen[key] = _Candidate(obj, row_number, parser.raw)

    # Pass 2: compare against what's already in the database (one query).
    existing = importer.existing(list(seen))
    candidates = []
    for key, cand in seen.items():
        current = existing.get(key)
        if current is None:
            candidates.append(cand)
        elif _same(cand.obj, current, importer.compare_fields):
            outcome.duplicates += 1
        else:
            outcome.reject(cand.row_number, cand.raw, [{
                "field": importer.key_label,
                "message": f"{_fmt(key)} already exists with different values; existing records are not overwritten",
            }])

    # Pass 3: secondary unique fields (e.g. customer email, instrument symbol).
    for field_name in importer.unique_fields:
        values = {getattr(c.obj, field_name) for c in candidates}
        taken = dict(
            importer.model.objects.filter(**{f"{field_name}__in": values}).values_list(field_name, "pk")
        )
        kept = []
        for cand in candidates:
            value = getattr(cand.obj, field_name)
            owner = taken.get(value)
            if owner is not None and owner != cand.obj.pk:
                outcome.reject(cand.row_number, cand.raw, [{
                    "field": field_name, "message": f"'{value}' is already used by {owner}",
                }])
                continue
            taken[value] = cand.obj.pk
            kept.append(cand)
        candidates = kept

    outcome.to_create = [c.obj for c in candidates]
    outcome.rejections.sort(key=lambda r: r.row_number)
    return outcome


def _fmt(key: tuple) -> str:
    return "/".join(str(k) for k in key)
