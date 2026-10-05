"""
Reporting views. Plain SQL so they can be queried from psql/BI tools as well as
from Django. Each has a matching DROP so `migrate portfolio 0002` rolls back cleanly.
"""

from django.db import migrations

POSITION_VALUATION = """
CREATE VIEW portfolio_position_valuation AS
-- Every position in each customer's latest snapshot, valued at the latest price.
WITH latest AS (
    SELECT a.customer_id, MAX(h.snapshot_date) AS snapshot_date
    FROM portfolio_holding h
    JOIN portfolio_account a ON a.id = h.account_id
    GROUP BY a.customer_id
)
SELECT h.id                                 AS holding_id,
       a.customer_id,
       h.account_id,
       h.instrument_id,
       i.symbol,
       i.asset_class,
       h.snapshot_date,
       i.price_as_of,
       h.quantity,
       h.avg_cost,
       i.last_price,
       h.quantity * i.last_price              AS market_value,
       h.quantity * h.avg_cost                AS cost_basis,
       h.quantity * (i.last_price - h.avg_cost) AS unrealised_gain
FROM portfolio_holding h
JOIN portfolio_account a    ON a.id = h.account_id
JOIN portfolio_instrument i ON i.id = h.instrument_id
JOIN latest l               ON l.customer_id = a.customer_id
                           AND l.snapshot_date = h.snapshot_date;
"""

CUSTOMER_AUM = """
CREATE VIEW portfolio_customer_aum AS
-- One row per customer (including those with no holdings) with snapshot AUM.
SELECT c.id                                AS customer_id,
       c.full_name,
       c.segment,
       c.city,
       COALESCE(SUM(v.market_value), 0)    AS market_value,
       COALESCE(SUM(v.cost_basis), 0)      AS cost_basis,
       COALESCE(SUM(v.unrealised_gain), 0) AS unrealised_gain,
       COUNT(v.holding_id)                 AS position_count,
       MAX(v.snapshot_date)                AS snapshot_date
FROM portfolio_customer c
LEFT JOIN portfolio_position_valuation v ON v.customer_id = c.id
GROUP BY c.id, c.full_name, c.segment, c.city;
"""

MONTHLY_NET_FLOWS = """
CREATE VIEW portfolio_monthly_net_flows AS
-- Settled activity per calendar month. net_invested = BUY - SELL
-- (positive = money went into the market). Pending/reversed rows are excluded.
SELECT date_trunc('month', trade_date)::date                                   AS month,
       COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'BUY'), 0)       AS buy_amount,
       COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'SELL'), 0)      AS sell_amount,
       COALESCE(SUM(CASE transaction_type WHEN 'BUY' THEN amount
                                          WHEN 'SELL' THEN -amount END), 0)   AS net_invested,
       COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'DIVIDEND'), 0)  AS dividends,
       COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'FEE'), 0)       AS fees,
       COUNT(*)                                                               AS transaction_count
FROM portfolio_transaction
WHERE status = 'SETTLED'
GROUP BY 1;
"""

RECONCILIATION_EXCEPTIONS = """
CREATE VIEW portfolio_reconciliation_exception AS
-- Everything operations should review, from loaded data and from import logs.
SELECT 'TXN_BEFORE_ACCOUNT_OPENED:' || t.id AS id,
       'TXN_BEFORE_ACCOUNT_OPENED'          AS exception_type,
       'transaction'                        AS entity,
       t.id                                 AS entity_id,
       a.customer_id,
       format('Trade dated %s but account %s opened %s', t.trade_date, a.id, a.opened_at) AS detail
FROM portfolio_transaction t
JOIN portfolio_account a ON a.id = t.account_id
WHERE t.trade_date < a.opened_at

UNION ALL
SELECT 'TXN_ON_CLOSED_ACCOUNT:' || t.id, 'TXN_ON_CLOSED_ACCOUNT', 'transaction', t.id, a.customer_id,
       format('%s %s on CLOSED account %s', t.status, t.transaction_type, a.id)
FROM portfolio_transaction t
JOIN portfolio_account a ON a.id = t.account_id
WHERE a.status = 'CLOSED'

UNION ALL
SELECT 'GOAL_OVERFUNDED:' || g.id, 'GOAL_OVERFUNDED', 'goal', g.id, g.customer_id,
       format('Funded %s exceeds target %s', g.current_funded_amount, g.target_amount)
FROM portfolio_goal g
WHERE g.current_funded_amount > g.target_amount

UNION ALL
SELECT 'GOAL_OVERDUE:' || g.id, 'GOAL_OVERDUE', 'goal', g.id, g.customer_id,
       format('Target date %s passed at %s%% funded', g.target_date,
              round(g.current_funded_amount / g.target_amount * 100, 2))
FROM portfolio_goal g
WHERE g.target_date < CURRENT_DATE AND g.current_funded_amount < g.target_amount

UNION ALL
SELECT 'STALE_PRICE:' || v.holding_id, 'STALE_PRICE', 'holding', v.holding_id::text, v.customer_id,
       format('%s priced %s, older than snapshot %s', v.symbol, v.price_as_of, v.snapshot_date)
FROM portfolio_position_valuation v
WHERE v.price_as_of < v.snapshot_date

UNION ALL
SELECT 'IMPORT_REJECTED_ROW:' || r.id, 'IMPORT_REJECTED_ROW', b.entity,
       COALESCE(r.raw ->> 'transaction_id', r.raw ->> 'goal_id', r.raw ->> 'account_id',
                r.raw ->> 'instrument_id', r.raw ->> 'customer_id', 'line ' || r.row_number),
       COALESCE(r.raw ->> 'customer_id', acc.customer_id),
       format('Batch %s line %s: %s', b.id, r.row_number,
              (SELECT string_agg((e ->> 'field') || ' ' || (e ->> 'message'), '; ')
               FROM jsonb_array_elements(r.errors) e))
FROM imports_importrejection r
JOIN imports_importbatch b      ON b.id = r.batch_id
LEFT JOIN portfolio_account acc ON acc.id = r.raw ->> 'account_id'

UNION ALL
SELECT 'IMPORT_DUPLICATES_SKIPPED:' || b.id, 'IMPORT_DUPLICATES_SKIPPED', b.entity, b.file_name, NULL,
       format('Batch %s: %s duplicate row(s) skipped', b.id, b.duplicate_count)
FROM imports_importbatch b
WHERE b.duplicate_count > 0;
"""

VIEWS = [
    ("portfolio_position_valuation", POSITION_VALUATION),
    ("portfolio_customer_aum", CUSTOMER_AUM),
    ("portfolio_monthly_net_flows", MONTHLY_NET_FLOWS),
    ("portfolio_reconciliation_exception", RECONCILIATION_EXCEPTIONS),
]


class Migration(migrations.Migration):
    dependencies = [
        ("portfolio", "0002_drop_redundant_indexes"),
        ("imports", "0001_initial"),
    ]

    # Created in order (later views depend on earlier ones), dropped in reverse.
    operations = [
        migrations.RunSQL(sql=create, reverse_sql=f"DROP VIEW IF EXISTS {name};")
        for name, create in VIEWS
    ]
