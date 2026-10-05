# FinPilot Database Notes

PostgreSQL is the only supported database. The schema lives entirely in Django
migrations (`backend/*/migrations/`); nothing is created by hand.

## 1. Schema at a glance

| Table | Rows (seed) | Key constraints |
|---|---|---|
| `portfolio_customer` | 120 | PK `id`; UNIQUE `email`; CHECK kyc_status, segment |
| `portfolio_account` | 167 | FK customer; CHECK account_type, status |
| `portfolio_instrument` | 80 | UNIQUE `symbol`; CHECK `last_price > 0`; CHECK enums |
| `portfolio_holding` | 982 | UNIQUE (account, instrument, snapshot_date); CHECK `quantity > 0`, `avg_cost >= 0` |
| `portfolio_transaction` | 4,550 | CHECK `amount >= 0`; CHECK trade ⇒ qty/price > 0, cash event ⇒ qty/price = 0 |
| `portfolio_goal` | 177 | CHECK `target_amount > 0`, `current_funded_amount >= 0` |
| `portfolio_riskprofile` | 120 | UNIQUE (customer, assessed_at); CHECK `risk_score <= 100` |
| `imports_importbatch` | — | partial UNIQUE (entity, file_sha256) WHERE status = 'COMPLETED' |
| `imports_importrejection` | — | FK batch; `raw` and `errors` as `jsonb` |

All money/quantities are `NUMERIC` (amount 18,2 · price 18,4 · quantity 20,6).
All foreign keys are `ON DELETE PROTECT` (enforced by Django) and deferrable FK constraints in PostgreSQL.

## 2. Reporting views (`portfolio/migrations/0003_reporting_views.py`)

| View | Purpose | Used by |
|---|---|---|
| `portfolio_position_valuation` | Each customer's latest-snapshot positions with market value, cost basis, unrealised gain | other views, SQL tasks 2 and 4 |
| `portfolio_customer_aum` | One row per customer (including those with no holdings) with snapshot AUM | SQL task 1 |
| `portfolio_monthly_net_flows` | Settled BUY / SELL / dividends / fees per month; `net_invested = BUY − SELL` | SQL task 3 |
| `portfolio_reconciliation_exception` | Unified list of issues for operations: trades before account opening, trades on closed accounts, over-funded / overdue goals, stale prices, import rejections, skipped duplicates | `GET /api/v1/admin/data-quality` (via the unmanaged model `ReconciliationException`) |

Views are plain (not materialized): the data is small and always current. Tests
assert that `portfolio_customer_aum` matches the portfolio API to the paisa.

**When to materialize:** if the portfolio query becomes a hotspot (≫100k
holdings), switch `portfolio_customer_aum` to a `MATERIALIZED VIEW` with a
unique index, and `REFRESH MATERIALIZED VIEW CONCURRENTLY` after each import.

## 3. Indexes and why

Each index serves a known query; nothing is indexed "just in case".

| Index | Serves |
|---|---|
| `txn_account_date_idx (account_id, trade_date DESC)` | Customer transaction list, newest first, paginated; also all FK lookups by account |
| `txn_trade_date_idx (trade_date)` | Monthly cash-flow reports (range scans by date) |
| `holding_unique_position_per_snapshot (account_id, instrument_id, snapshot_date)` | Uniqueness, **and** FK lookups by account |
| `holding_snapshot_date_idx (snapshot_date)` | Latest-snapshot lookups |
| `risk_profile_unique_per_day (customer_id, assessed_at)` | Uniqueness, FK lookups, and "latest assessment" (B-tree read backwards) |
| `customer_city_idx (city)` | City filter on customer search |
| FK indexes on account.customer, goal.customer, holding.instrument, transaction.instrument | Joins / FK checks |

**Removed as redundant** (migration `0002_drop_redundant_indexes`): the separate
FK indexes on `transaction.account_id`, `holding.account_id` and
`riskprofile.customer_id`, plus `(customer_id, assessed_at DESC)`, because each was
a leading-column prefix of another index. Fewer indexes = cheaper inserts and imports.

**Known overhead:** Django adds a second `varchar_pattern_ops` ("`_like`") index for
every `CharField` primary key / unique field, for `LIKE 'abc%'` queries. Our key
lookups are exact, so these are unused. Left in place to avoid fighting the framework.

**Not added yet:** customer search uses `ILIKE '%term%'`, which a B-tree can't
serve. At 120 rows a sequential scan is instant; at scale add
`CREATE EXTENSION pg_trgm` + a GIN trigram index on `full_name`, `email`.

## 4. Query plans (`EXPLAIN (ANALYZE, BUFFERS)`, Neon, seed data)

### Paginated transaction list for one account
```sql
SELECT id, trade_date, transaction_type, amount, status
FROM portfolio_transaction
WHERE account_id = 'A00002'
ORDER BY trade_date DESC, id
LIMIT 25;
```
```
Limit  (actual time=0.025..0.027 rows=15)
  Buffers: shared hit=3
  ->  Incremental Sort  (Sort Key: trade_date DESC, id; Presorted Key: trade_date)
        ->  Index Scan using txn_account_date_idx on portfolio_transaction
              Index Cond: (account_id = 'A00002')
Execution Time: 0.051 ms
```
**How to read it:** the composite index returns this account's rows *already in
date order*, so PostgreSQL only sorts ties on `id` (Incremental Sort), and the
`LIMIT` can stop early. 3 buffer hits, all from cache, nothing read from disk.
(Before migration 0002 the planner used the single-column FK index plus a full sort.)

### Portfolio allocation for one customer (through the view)
```sql
SELECT asset_class, SUM(market_value)
FROM portfolio_position_valuation
WHERE customer_id = 'C0002'
GROUP BY asset_class;
```
Key lines:
```
GroupAggregate  (actual time=0.130..0.134 rows=3)   Buffers: shared hit=29
  ...
  -> Seq Scan on portfolio_account a     Filter: (customer_id = 'C0002')   Rows Removed by Filter: 166
  -> Bitmap Index Scan on holding_unique_position_per_snapshot   Index Cond: (account_id = a.id)
```
**How to read it:**
- The `customer_id` filter is **pushed down** into the view, including its
  "latest snapshot" CTE, so only this customer's holdings are read.
- Holdings are found through the unique index, which confirms that dropping the
  separate FK index lost nothing.
- `portfolio_account` gets a **Seq Scan** even though `customer_id` is indexed: the
  table is 167 rows (2 pages), so scanning is cheaper than an index lookup. The
  planner switches to the index automatically as the table grows.

## 5. Operating it in production

### Connection pooling
- Django keeps connections open per worker for `CONN_MAX_AGE=60` s with
  `CONN_HEALTH_CHECKS=True` (a dead connection is replaced, not used).
- In production, put **PgBouncer in transaction mode** in front of PostgreSQL (or
  use the provider's pooler, e.g. Neon's `-pooler` host). Settings already set
  `DISABLE_SERVER_SIDE_CURSORS=True`, which transaction pooling requires.
- Size: total connections = gunicorn workers × instances; keep it well below
  `max_connections` and let the pooler multiplex.
- Run **migrations over a direct (non-pooled) connection**: DDL and advisory locks
  don't mix well with transaction pooling. Locally we use the direct host for this reason.

### Backups and restore
- Managed PostgreSQL (Neon/RDS/Cloud SQL): enable automated backups with
  **point-in-time recovery** (e.g. 7–30 days); Neon also offers instant branches for restore testing.
- Self-hosted: nightly `pg_dump -Fc` to object storage plus WAL archiving for PITR.
- **Test restores regularly**: restore into a scratch database and run
  `python manage.py migrate --check` plus the SQL task file as a smoke test.

### Migrations and rollback
- Apply: `python manage.py migrate` (to be run by the container entrypoint before the app starts, once Docker Compose is added).
- Check without applying: `python manage.py migrate --check` / `showmigrations` / `sqlmigrate <app> <n>`.
- Each migration runs in a transaction on PostgreSQL, so **a failing migration
  rolls back automatically** and leaves the schema as it was.
- Roll back a released migration: `python manage.py migrate portfolio 0002`
  (every hand-written `RunSQL` here has a `reverse_sql`, and this was tested:
  0004 → 0002 → 0004).
- Prefer **expand/contract** for risky changes: add the new column/table, deploy code
  that writes both, backfill, switch reads, then drop the old one in a later release.
- Take a backup (or a Neon branch) before applying migrations in production.

### Credentials
- Never in Git: `DATABASE_URL` and `SECRET_KEY` come from the environment
  (`.env` locally, git-ignored; `.env.example` has placeholders only).
- Production: inject from a secrets manager (AWS Secrets Manager, GCP Secret
  Manager, Doppler…) as environment variables at runtime; rotate on staff changes.
- **Least privilege:** the app role needs `SELECT/INSERT/UPDATE/DELETE` on app
  tables only. A separate migration role owns the schema and is used only by
  the deploy step. Read-only role for BI/analysts querying the views.
- Require TLS to the database (`sslmode=require`, already in the Neon URL).

## 6. Observations about the supplied data

Beyond the deliberate anomalies (see the import walkthrough):
- **Segment doesn't track wealth:** all ten highest-AUM customers are labelled `Mass`.
- **Goal names don't match goal types** (e.g. "Family Travel" with type `RETIREMENT`).
  Accepted as-is: names are free text; the type drives reporting.
- **1,069 trades predate their account's opening date; 114 sit on CLOSED accounts.**
  Accepted and surfaced through `portfolio_reconciliation_exception`.
- **Holdings don't reconcile with the transaction ledger**; the holdings snapshot is
  treated as the source of truth for valuation, as the assignment specifies.

## 7. Running the SQL tasks

```bash
psql "$DATABASE_URL" -f docs/sql/assignment_queries.sql
```
Covers every task in assignment §6.1 (top 10 AUM, allocation per customer and
overall, 12-month BUY/SELL net flow, top instruments by holders, under-funded
high-priority goals, data-quality checks) plus an `EXPLAIN (ANALYZE, BUFFERS)`.
