# FinPilot

Investment portfolio and goal monitoring for wealth-management teams. FinPilot loads customer, account, holding, transaction, goal and risk-profile data from CSV files. It then gives advisors a dashboard for each customer, and gives operations staff a view of data-quality issues.

**Stack:** Django 6 + Django REST Framework · PostgreSQL · Next.js 16 (App Router) + React 19 · TanStack Query · Tailwind CSS 4 + shadcn/ui

---

## Features

- **Customer dashboard**: portfolio value, unrealised gain, asset allocation, positions, accounts, risk profile, goals and recent transactions
- **Goals**: track progress toward each goal, and create or edit goals with validation and audit logging
- **Transactions**: a paginated, filterable list. Filters are kept in the URL, so a filtered view can be shared.
- **CSV import** (admin only): validates each row, records rejected rows with their errors, and skips files that were already imported (checked by SHA-256 hash). Available from the UI or the CLI.
- **Data-quality report**: one list of reconciliation exceptions, such as trades before an account opened, trades on closed accounts, over-funded or overdue goals, stale prices, and import rejections
- **Auth**: JWT access token kept in memory, plus a rotating refresh token in an httpOnly cookie that is blacklisted after use. Two roles: `ADMIN` and `VIEWER`.
- **Reporting SQL views**: position valuation, customer AUM and monthly net flows, built in PostgreSQL
- **OpenAPI docs**: Swagger UI at `/api/v1/docs`

## Project structure

```
finpilot/
├── backend/            Django project
│   ├── accounts/       Custom user model, roles, JWT auth, user admin API
│   ├── portfolio/      Customers, accounts, holdings, transactions, goals, reporting views
│   ├── imports/        CSV parsing, importers, import batches & rejections, data-quality API
│   ├── core/           Health endpoint
│   └── backend/        Settings, URLs, pagination
├── frontend/           Next.js app (dashboard, goals, transactions, admin imports)
├── data/               Seed CSVs and data dictionary
├── docker-compose.yml  Local stack: db + api + web
└── docs/
    ├── database.md     Schema, views, indexes, query plans, ops notes
    ├── docker-walkthrough.md  How the Docker Compose stack works
    └── sql/            Standalone reporting SQL queries
```

## Getting started

There are two ways to run FinPilot locally. Docker Compose is the quickest because it needs only Docker installed.

### Option A: Docker Compose (recommended)

Prerequisite: Docker Desktop, or Docker Engine with the Compose plugin.

```bash
cp .env.example .env                # then set SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build
```

This starts three containers:

| Service | What it runs                                  | URL                                |
|---------|-----------------------------------------------|------------------------------------|
| `db`    | PostgreSQL 17, data kept in the `pgdata` volume | `localhost:5432`                 |
| `api`   | Django API on gunicorn                        | http://localhost:8000/api/v1       |
| `web`   | Next.js production build                      | http://localhost:3000              |

On every start the API container applies migrations, creates the demo users, and imports `data/*.csv`. Files that were already imported are skipped, so restarts are safe. The frontend waits until the API health check passes. If a migration fails, the API container exits before serving any requests, and the database is left unchanged.

Useful commands:

```bash
docker compose logs -f api                              # API and import logs
docker compose exec api python manage.py test           # backend tests
docker compose exec db psql -U finpilot finpilot        # SQL shell
docker compose down                                     # stop (keeps data)
docker compose down -v                                  # stop and delete the database volume
```

To skip seeding on start-up, set `SEED_ON_START=false` in `.env`.

### Option B: Run each part natively

Prerequisites: Python 3.12+, Node.js 20+, PostgreSQL 15+.

#### 1. Database

Use a local PostgreSQL install:

```bash
createuser finpilot --pwprompt      # password: finpilot (or your own)
createdb finpilot --owner finpilot
```

Or start only the database container with `docker compose up db`.

#### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env                # then set SECRET_KEY and DATABASE_URL
python manage.py migrate
python manage.py seed_demo_users    # creates the demo admin and viewer accounts
python manage.py import_data        # loads ../data/*.csv in dependency order
python manage.py runserver          # http://localhost:8000
```

To generate a secret key, run `python -c "import secrets; print(secrets.token_urlsafe(50))"`.

#### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local          # NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm run dev                         # http://localhost:3000
```

### Hosted PostgreSQL (optional)

The backend reads its database only from `DATABASE_URL`, so a managed database such as Neon works without code changes. Point `DATABASE_URL` at it, and include `?sslmode=require`. FinPilot was developed against Neon. The supported reviewer setup is the local PostgreSQL described above.

### Demo accounts

| Role   | Email                   | Password        |
|--------|-------------------------|-----------------|
| Admin  | `admin@finpilot.local`  | `FinPilot@2026` |
| Viewer | `viewer@finpilot.local` | `FinPilot@2026` |

Use `python manage.py seed_demo_users --password <pw>` to set a different password.

## Configuration

Backend settings come from environment variables, or from `backend/.env`. Docker Compose sets them from the root `.env` instead (see `.env.example`):

| Variable               | Description                              | Default / example                                   |
|------------------------|------------------------------------------|-----------------------------------------------------|
| `SECRET_KEY`           | Django secret key                        | (required)                                          |
| `DEBUG`                | Debug mode. If false, cookies are `Secure`. | `True`                                           |
| `ALLOWED_HOSTS`        | Comma-separated hostnames                | `localhost,127.0.0.1`                               |
| `DATABASE_URL`         | PostgreSQL connection URL                | `postgres://finpilot:finpilot@localhost:5432/finpilot` |
| `CORS_ALLOWED_ORIGINS` | Frontend origin(s)                       | `http://localhost:3000`                             |
| `JWT_ACCESS_MINUTES`   | Access-token lifetime                    | `15`                                                |
| `JWT_REFRESH_DAYS`     | Refresh-token lifetime                   | `7`                                                 |
| `JWT_COOKIE_SECURE`    | Mark the refresh cookie `Secure`. Docker Compose sets it to false, because it serves plain HTTP. | `not DEBUG`                    |
| `LOG_LEVEL`            | Logging level                            | `INFO`                                              |

The frontend uses only `NEXT_PUBLIC_API_URL`. This value is built into the browser bundle, so never put secrets in it.

## Importing data

```bash
python manage.py import_data                          # all entities from ../data
python manage.py import_data --dir /path/to/csvs      # a different folder
python manage.py import_data --only customers goals   # selected entities only
python manage.py import_data --show-rejections        # print every rejected row
```

With Docker Compose, prefix these commands with `docker compose exec api`. Inside the container the CSVs are mounted at `/data`.

You can re-run the import safely: a file that was already imported is skipped. Admins can also upload CSVs from **Admin → Imports** in the UI, where they can see import history, rejected rows and the data-quality report.

## API overview

All endpoints are under `/api/v1/`. They require a Bearer token unless marked otherwise.

| Method | Endpoint                                  | Access        |
|--------|-------------------------------------------|---------------|
| GET    | `health`                                  | Public        |
| POST   | `auth/login`, `auth/refresh`, `auth/logout` | Public      |
| GET    | `auth/me`                                 | Authenticated |
| GET    | `customers`, `customers/{id}`             | Authenticated |
| GET    | `customers/{id}/portfolio`                | Authenticated |
| GET/POST | `customers/{id}/goals`                  | Authenticated |
| GET/PATCH | `goals/{goal_id}`                      | Authenticated |
| GET    | `customers/{id}/transactions`             | Authenticated |
| GET/POST | `admin/users`                           | Admin         |
| POST   | `admin/imports/{entity}`                  | Admin         |
| GET    | `admin/imports`, `admin/imports/batches/{id}` | Admin     |
| GET    | `admin/data-quality`                      | Admin         |

The full interactive docs are at **http://localhost:8000/api/v1/docs**.

## SQL reporting

The schema is created only by Django migrations. Reporting views are added in `portfolio/migrations/0003_reporting_views.py`. To run the standalone reporting queries:

```bash
psql "$DATABASE_URL" -f docs/sql/assignment_queries.sql
# or, with Docker Compose:
docker compose exec -T db psql -U finpilot finpilot < docs/sql/assignment_queries.sql
```

[`docs/database.md`](docs/database.md) explains the schema, constraints, indexes, query plans, and how to run the database in production.

## Running tests

```bash
cd backend
python manage.py test               # all apps
python manage.py test accounts      # a single app

cd ../frontend
npm run lint
```

The tests need a PostgreSQL database, because the reporting views and constraints are PostgreSQL-specific.
