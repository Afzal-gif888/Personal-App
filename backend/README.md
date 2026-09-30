# Backend

The FastAPI API: accounts and login codes, tasks, calendar, reminders, finance, documents and document search (PostgreSQL + pgvector), conversations, approvals and the reminder scheduler. It calls the Agent Core for chat and never serves the website.

Self-contained: everything this service needs is in this folder (deploy it with **Root Directory = `backend`**).

## Run locally

```powershell
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env            # then fill in the values
alembic upgrade head              # needs the database: `docker compose up -d db` in the project root
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

## Test

```powershell
pytest                                                                                      # SQLite (vector-search tests skipped)
$env:TEST_DATABASE_URL="postgresql://agentos:agentos@127.0.0.1:5433/agentos_test"; pytest  # full suite on pgvector
pyright                                                                                     # type check
```

## Deploy (Railway)

| File | Role |
| --- | --- |
| `Dockerfile` | Builds the image; listens on `$PORT` (IPv4 + IPv6) |
| `docker-entrypoint.sh` | On every start: prepares `/data/storage`, runs migrations, starts the API as a non-root user |
| `railway.json` | Dockerfile build, `/health` check, one replica (the scheduler must run once) |
| `.dockerignore` | Keeps `.env`, `.venv`, uploads and tests out of the image |
| `.env.example` | Every setting, with comments |

Attach a volume at `/data`. Step by step: [../DEPLOY.md](../DEPLOY.md).
