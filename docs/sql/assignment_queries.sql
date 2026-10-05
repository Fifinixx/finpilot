-- =============================================================================
-- FinPilot: SQL tasks from assignment section 6.1
--
-- Run:   psql "$DATABASE_URL" -f docs/sql/assignment_queries.sql
-- Each query stands alone, so you can also copy one into psql/pgAdmin.
-- "Current snapshot" = each customer's latest holdings snapshot_date.
-- Money is NUMERIC end to end; round() is for display only.
-- =============================================================================

\echo '=== 1. Top 10 customers by current snapshot AUM ==='
WITH latest AS (                                   -- latest snapshot per customer
    SELECT a.customer_id, MAX(h.snapshot_date) AS snapshot_date
    FROM portfolio_holding h
    JOIN portfolio_account a ON a.id = h.account_id
    GROUP BY a.customer_id
)
SELECT c.id                                       AS customer_id,
       c.full_name,
       c.segment,
       round(SUM(h.quantity * i.last_price), 2)   AS aum,
       COUNT(*)                                   AS positions,
       l.snapshot_date
FROM portfolio_holding h
JOIN portfolio_account a    ON a.id = h.account_id
JOIN portfolio_instrument i ON i.id = h.instrument_id
JOIN portfolio_customer c   ON c.id = a.customer_id
JOIN latest l               ON l.customer_id = c.id AND l.snapshot_date = h.snapshot_date
GROUP BY c.id, c.full_name, c.segment, l.snapshot_date
ORDER BY aum DESC
LIMIT 10;
-- Same result from the reporting view:
--   SELECT * FROM portfolio_customer_aum ORDER BY market_value DESC LIMIT 10;


\echo '=== 2a. Asset-class allocation for one customer (C0002) ==='
SELECT asset_class,
       round(SUM(market_value), 2)                                       AS market_value,
       round(100 * SUM(market_value) / SUM(SUM(market_value)) OVER (), 2) AS weight_pct
FROM portfolio_position_valuation               -- view: latest-snapshot positions, valued
WHERE customer_id = 'C0002'
GROUP BY asset_class
ORDER BY market_value DESC;


\echo '=== 2b. Asset-class allocation for the whole dataset ==='
-- SUM(...) OVER () is a window over the grouped rows: the grand total, so each
-- row can show its share without a second query.
SELECT asset_class,
       round(SUM(market_value), 2)                                       AS market_value,
       round(100 * SUM(market_value) / SUM(SUM(market_value)) OVER (), 2) AS weight_pct,
       COUNT(DISTINCT customer_id)                                       AS customers
FROM portfolio_position_valuation
GROUP BY asset_class
ORDER BY market_value DESC;


\echo '=== 3. Monthly BUY/SELL net cash flow, last 12 complete months ==='
-- net_invested = BUY - SELL (positive = net money into the market).
-- SETTLED only: pending trades may not happen and reversed ones did not.
-- The current, partial month is excluded so months compare like for like.
-- generate_series makes months with no trades show as 0 instead of vanishing.
WITH months AS (
    SELECT generate_series(date_trunc('month', CURRENT_DATE) - INTERVAL '12 months',
                           date_trunc('month', CURRENT_DATE) - INTERVAL '1 month',
                           INTERVAL '1 month')::date AS month
)
SELECT m.month,
       COALESCE(SUM(t.amount) FILTER (WHERE t.transaction_type = 'BUY'), 0)  AS buys,
       COALESCE(SUM(t.amount) FILTER (WHERE t.transaction_type = 'SELL'), 0) AS sells,
       COALESCE(SUM(CASE t.transaction_type WHEN 'BUY'  THEN t.amount
                                            WHEN 'SELL' THEN -t.amount END), 0) AS net_invested,
       COUNT(t.id)                                                           AS trades
FROM months m
LEFT JOIN portfolio_transaction t
       ON t.trade_date >= m.month
      AND t.trade_date <  m.month + INTERVAL '1 month'   -- range, not date_trunc(), so the trade_date index is usable
      AND t.status = 'SETTLED'
      AND t.transaction_type IN ('BUY', 'SELL')
GROUP BY m.month
ORDER BY m.month;
-- All months, all types:  SELECT * FROM portfolio_monthly_net_flows ORDER BY month;


\echo '=== 4. Top instruments by number of distinct holders (current snapshot) ==='
SELECT i.id                          AS instrument_id,
       i.symbol,
       i.name,
       i.asset_class,
       COUNT(DISTINCT v.customer_id) AS holders,
       round(SUM(v.market_value), 2) AS total_market_value
FROM portfolio_position_valuation v
JOIN portfolio_instrument i ON i.id = v.instrument_id
GROUP BY i.id, i.symbol, i.name, i.asset_class
ORDER BY holders DESC, total_market_value DESC
LIMIT 10;


\echo '=== 5. Customers with HIGH-priority goals below 25% funded ==='
SELECT c.id                                                       AS customer_id,
       c.full_name,
       g.id                                                       AS goal_id,
       g.name                                                     AS goal_name,
       g.goal_type,
       g.target_amount,
       g.current_funded_amount,
       round(100 * g.current_funded_amount / g.target_amount, 2)  AS funded_pct,
       g.target_date
FROM portfolio_goal g
JOIN portfolio_customer c ON c.id = g.customer_id
WHERE g.priority = 'HIGH'
  AND g.current_funded_amount < 0.25 * g.target_amount   -- no division in the filter: index-friendly, no divide-by-zero
ORDER BY funded_pct, g.target_date;


\echo '=== 6a. Data quality: duplicate positions / duplicate transaction IDs in the tables ==='
-- Both return 0 rows by construction: the UNIQUE (account, instrument, snapshot_date)
-- constraint and the transaction primary key make duplicates impossible to store.
-- The importer skipped/rejected them before insert (see 6c).
SELECT account_id, instrument_id, snapshot_date, COUNT(*)
FROM portfolio_holding
GROUP BY account_id, instrument_id, snapshot_date
HAVING COUNT(*) > 1;

SELECT id, COUNT(*) FROM portfolio_transaction GROUP BY id HAVING COUNT(*) > 1;


\echo '=== 6b. Data quality: invalid references that reached the tables ==='
-- Also 0 rows by construction (foreign keys). Shown as the check you would run
-- against a raw/staging table that has no FKs.
SELECT t.id, t.instrument_id
FROM portfolio_transaction t
LEFT JOIN portfolio_instrument i ON i.id = t.instrument_id
WHERE i.id IS NULL;


\echo '=== 6c. Data quality: what the importer caught (from the import log) ==='
SELECT b.id                               AS batch,
       b.entity,
       b.file_name,
       b.total_rows,
       b.imported_count,
       b.duplicate_count,
       b.rejected_count
FROM imports_importbatch b
WHERE b.status = 'COMPLETED' AND (b.duplicate_count > 0 OR b.rejected_count > 0)
ORDER BY b.id;

SELECT b.entity,
       r.row_number                         AS line,
       r.raw ->> 'transaction_id'           AS transaction_id,
       e ->> 'field'                        AS field,
       e ->> 'message'                      AS reason
FROM imports_importrejection r
JOIN imports_importbatch b ON b.id = r.batch_id
CROSS JOIN LATERAL jsonb_array_elements(r.errors) AS e   -- one row per error
ORDER BY b.id, r.row_number;


\echo '=== 6d. Reconciliation exceptions in loaded data (summary) ==='
SELECT exception_type, COUNT(*) AS rows
FROM portfolio_reconciliation_exception
GROUP BY exception_type
ORDER BY rows DESC;


\echo '=== EXPLAIN: paginated transaction list for one account ==='
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, trade_date, transaction_type, amount, status
FROM portfolio_transaction
WHERE account_id = 'A00002'
ORDER BY trade_date DESC, id
LIMIT 25;
