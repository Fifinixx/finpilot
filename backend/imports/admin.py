from django.contrib import admin

from .models import ImportBatch, ImportRejection


class ImportRejectionInline(admin.TabularInline):
    model = ImportRejection
    extra = 0
    can_delete = False
    readonly_fields = ["row_number", "errors", "raw"]


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ["id", "entity", "file_name", "status", "imported_count", "duplicate_count",
                    "rejected_count", "created_by", "created_at"]
    list_filter = ["entity", "status"]
    readonly_fields = [f.name for f in ImportBatch._meta.fields]
    inlines = [ImportRejectionInline]
