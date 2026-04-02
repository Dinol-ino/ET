# ai-sales-agent

Production-ready FastAPI backend for an AI-powered Sales Intelligence System.

## Architecture

- API layer: `app/api`
- Service layer: `app/services`
- Repository layer: `app/repositories`
- Agent layer (placeholders for LangGraph): `app/agents`
- Integration layer: `app/integrations`
- Data layer: `app/models`, `app/db`

## Features

- Prospect Intelligence: scraping, enrichment, scoring, outreach generation
- Deal Intelligence: inactivity/reply/activity-based risk scoring
- Retention Signals: activity trend drop detection for churn risk
- HubSpot sync: contacts and deals

## Endpoints

- `POST /api/hubspot/sync-contacts`
- `POST /api/hubspot/sync-deals`
- `POST /api/prospect/analyze`
- `POST /api/deal/analyze`
- `POST /api/deal/analyze-all`
- `GET /api/dashboard/summary`
- `GET /health`

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Install migration and test tooling:

```bash
pip install -r requirements-dev.txt
```

## Run API

```bash
uvicorn app.main:app --reload
```

## Database Migrations (Alembic)

```bash
alembic upgrade head
alembic downgrade -1
```

Initial production migration is in `migrations/versions/0001_initial.py`.

## Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Test suite includes:

- Unit tests for scoring and deal service logic
- Integration tests for API endpoints with an isolated SQLite test DB

## Notes

- Configure PostgreSQL in `.env` via `DATABASE_URL`.
- If `HUBSPOT_API_KEY` is missing, sync endpoints use deterministic mock data.
- Ollama generation gracefully falls back to template text when unavailable.
