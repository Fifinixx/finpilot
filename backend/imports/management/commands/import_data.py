from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from imports.importers import DEFAULT_FILES, IMPORTERS
from imports.services import DuplicateFileError, ImportFileError, run_import


class Command(BaseCommand):
    help = "Load the supplied CSV files in dependency order. Safe to re-run: identical files are skipped."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=str(settings.BASE_DIR.parent / "data"), help="Folder containing the CSVs")
        parser.add_argument("--only", nargs="+", choices=list(IMPORTERS), help="Import only these entities")
        parser.add_argument("--show-rejections", action="store_true", help="Print every rejected row")

    def handle(self, *args, dir, only, show_rejections, **options):
        data_dir = Path(dir)
        if not data_dir.is_dir():
            raise CommandError(f"{data_dir} is not a directory")

        for entity, importer in IMPORTERS.items():
            if only and entity not in only:
                continue
            path = data_dir / DEFAULT_FILES[entity]
            if not path.exists():
                self.stdout.write(self.style.WARNING(f"{entity:<14} skipped: {path.name} not found"))
                continue
            try:
                batch = run_import(importer, path.read_bytes(), path.name)
            except DuplicateFileError as exc:
                self.stdout.write(f"{entity:<14} skipped: already imported (batch {exc.previous.pk})")
                continue
            except ImportFileError as exc:
                raise CommandError(f"{entity}: {exc}") from None

            style = self.style.WARNING if batch.rejected_count else self.style.SUCCESS
            self.stdout.write(style(
                f"{entity:<14} rows={batch.total_rows:<5} imported={batch.imported_count:<5} "
                f"duplicates={batch.duplicate_count:<3} rejected={batch.rejected_count:<3} (batch {batch.pk})"
            ))
            if show_rejections or batch.rejected_count <= 10:
                for r in batch.rejections.all():
                    reasons = "; ".join(f"{e['field']}: {e['message']}" for e in r.errors)
                    self.stdout.write(f"    line {r.row_number}: {reasons}")
