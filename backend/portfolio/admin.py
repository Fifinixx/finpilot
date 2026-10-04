from django.contrib import admin

from .models import Account, Customer, Goal, Holding, Instrument, RiskProfile, Transaction


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["id", "full_name", "email", "city", "kyc_status", "segment"]
    list_filter = ["kyc_status", "segment", "city"]
    search_fields = ["id", "full_name", "email"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "account_type", "provider", "status", "opened_at"]
    list_filter = ["account_type", "status", "provider"]
    search_fields = ["id", "customer__id", "customer__full_name"]
    list_select_related = ["customer"]


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ["id", "symbol", "name", "asset_class", "exchange", "last_price", "price_as_of", "risk_band"]
    list_filter = ["asset_class", "exchange", "risk_band"]
    search_fields = ["id", "symbol", "name"]


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = ["account", "instrument", "quantity", "avg_cost", "snapshot_date"]
    list_filter = ["snapshot_date"]
    search_fields = ["account__id", "instrument__symbol"]
    raw_id_fields = ["account", "instrument"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "account", "instrument", "transaction_type", "trade_date", "amount", "status"]
    list_filter = ["transaction_type", "status"]
    search_fields = ["id", "account__id"]
    date_hierarchy = "trade_date"
    raw_id_fields = ["account", "instrument", "import_batch"]


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "goal_type", "name", "target_amount", "current_funded_amount", "target_date", "priority"]
    list_filter = ["goal_type", "priority"]
    search_fields = ["id", "customer__id", "name"]
    raw_id_fields = ["customer"]


@admin.register(RiskProfile)
class RiskProfileAdmin(admin.ModelAdmin):
    list_display = ["customer", "risk_level", "risk_score", "assessed_at", "liquidity_need"]
    list_filter = ["risk_level", "liquidity_need"]
    raw_id_fields = ["customer"]
