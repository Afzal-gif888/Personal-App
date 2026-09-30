# It's Personal

A personal AI workspace for students. One place for coursework, calendar, bills, expenses and goals, with an assistant that **plans with you and asks before it acts**.

> Status: the React frontend talks to the FastAPI backend in [`backend/`](backend) for everything (no mock data). Run both: `uvicorn app.main:app --reload` in `backend/`, then `npm run dev` in `frontend/`; Vite proxies `/api` to `http://localhost:8000`. Set `VITE_API_URL` to point a build at a backend on another origin.

## Quick start

With Docker Desktop running and both `.env` files in place, start everything from the project root:

```powershell
.\start.ps1          # or double-click start.bat
.\stop.ps1           # stop everything
```

The script starts the database container if needed (PostgreSQL + pgvector, see below), applies database migrations, opens the backend (`:8000`), the [Agent Core](agent-core) (`:8001`) and the frontend (`:5173`) in their own windows, waits until each responds, and opens the app. It also accepts `-SkipMigrations` and `-NoBrowser`.

## Workflow

### The core loop

```
Ask  →  Agent plans  →  You approve  →  Tracked
```

1. **Ask**: describe what you need in the Assistant (e.g. “Plan my ML exam revision”).
2. **Agent plans**: the agent reads your tasks, calendar and finances, then drafts an action. Every step and tool call is logged.
3. **You approve**: the draft appears as a *proposed action*, inline in the chat or in the Approvals inbox. Nothing is created or changed until you approve it.
4. **Tracked**: the approved item lands in the right module (Tasks, Reminders, Study plan), and Home shows what needs attention next.

### End to end

| Step | Where | What happens |
| --- | --- | --- |
| Sign up / sign in | `/register`, `/login` | Create your own account; the app starts empty and holds only your data |
| Daily overview | Home `/dashboard` | Stats, the live workflow pipeline, tasks due soon, 7-day schedule, pending approvals, bills, goals |
| Make a request | Assistant `/chat` | Conversation history, starter prompts, drafts saved per conversation |
| Agent run | Agent activity `/agent-runs` | Audit log: request, status, tools, duration; drill into `/agent-runs/:id` for the step trace with tool inputs/outputs |
| Review | Inline action card, or Approvals `/approvals` | Approve or reject; decisions move to **History** |
| Result | Tasks, Reminders, Study plan | Approved items are created here and can also be managed by hand |
| Manage everything else | Calendar, Goals, Documents, Bills & payments, Expenses | Standard create / edit / delete with filters |
| Budgets | `/budgets` | Monthly limits overall or per expense category; progress, "near limit" and "over budget" status, any past month |
| Configure | Settings `/settings/*` | Profile, notification channels, assistant defaults (study window, reminder time, time zone) |

## Information architecture

Navigation follows the workflow and is defined once in [`frontend/src/config/navigation.ts`](frontend/src/config/navigation.ts). The sidebar, mobile drawer, command menu (Ctrl/⌘ K) and breadcrumbs all read from it.

- **Workspace**: Home, Assistant, Approvals
- **Planning**: Tasks, Calendar, Reminders, Goals
- **Study**: Study plan, Documents
- **Finance**: Bills & payments, Expenses, Budgets
- **Automation**: Agent activity

## Backend

FastAPI · SQLAlchemy 2 · PostgreSQL · Alembic · Pydantic v2 · Anthropic SDK

```powershell
cd backend
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env               # then set DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload        # http://localhost:8000/docs
pytest                               # SQLite by default (vector-search tests skipped)
$env:TEST_DATABASE_URL="postgresql://agentos:agentos@127.0.0.1:5433/agentos_test"; pytest   # full suite on pgvector
```

The assistant runs in the [Agent Core](agent-core) (`AGENT_CORE_MODE=agent`); set `LLM_API_KEY` in `agent-core/.env` (a free Gemini key works). There is no mock mode: without a key the assistant replies that it isn't set up.

### Layout

```
app/api/v1/routes/  →  services/  →  models/ (SQLAlchemy)
                         ↑
agent/ (remote: Agent Core client; runner: legacy local loop)  →  llm/ (agent_core | anthropic)
jobs/ (scheduler) · notifications/ · storage/ · core/ (config, errors, security, logging)
```

### API conventions

- Everything is under `/api/v1`, authenticated with `Authorization: Bearer <accessToken>`. Access tokens last 30 minutes; `POST /auth/refresh` rotates the refresh token, and replaying an old one signs out every session.
- JSON bodies are **camelCase**; query parameters are snake_case (`?page_size=20&due_from=2026-10-01`). Lists that can grow (`tasks`, `expenses`, `payments`, `documents`, `agent-runs`, `approvals`, `notifications`) return `{items, total, page, pageSize}`.
- Errors always look like `{"error": {"code", "message", "details?"}}`, e.g. `VALIDATION_ERROR` with per-field `details`.
- Timestamps are stored in UTC. Events and reminders accept either `startAt` / `scheduledAt` or a local `date` + `startTime` / `time`, interpreted in the user's timezone (`/users/me/preferences`), and return both forms. Money is a JSON number; times are `HH:MM`.

### How the assistant acts

`POST /conversations/{id}/messages` runs the agent loop. Read tools (tasks, calendar, bills, spending, budgets, goals, documents, free slots) run immediately. Write tools (`create_task`, `create_reminder`, `create_event`, `create_study_plan`, `log_expense`, `mark_bill_paid`, `complete_task`, `set_budget`) only create an **approval**. It is returned in `assistantMessage.metadata.actions` and listed at `/approvals`. `POST /approvals/{id}/approve` applies exactly the previewed payload; `reject` discards it. Pending approvals expire after `APPROVAL_TTL_HOURS`. Every run, tool call (with inputs/outputs) and decision is recorded under `/agent-runs/{id}` and in the audit log.

### Background jobs

The scheduler delivers due reminders, flags due/overdue bills, warns 30 minutes before events and expires stale approvals. Each notification carries a dedupe key, so running several schedulers never duplicates one. Enable it in-process with `SCHEDULER_ENABLED=true` (single API instance), or run `python -m scripts.run_scheduler` (add `--once` for cron). Reminder-type notifications are also emailed (EmailJS) when the user keeps "Email me reminders" on. The scheduler also indexes documents for search (pending ones, retries, and re-indexing after an embedding model change).

### Database (PostgreSQL + pgvector)

The database runs in Docker from [`docker-compose.yml`](docker-compose.yml): PostgreSQL 18 with the pgvector extension, on host port **5433** (so it can sit next to a native PostgreSQL on 5432). Data lives in the `pgdata` Docker volume.

```powershell
docker compose up -d db                                   # start (start.ps1 does this for you)
cd backend; alembic upgrade head                          # migrate (start.ps1 does this too)
docker compose stop db                                    # stop (data is kept)
docker compose exec db psql -U agentos -d agentos         # psql shell
```

`backend/.env`: `DATABASE_URL=postgresql://agentos:agentos@127.0.0.1:5433/agentos` (use `127.0.0.1`, not `localhost`: on Windows `localhost` tries IPv6 first and the container only listens on IPv4). Inspect pgvector in psql:

```sql
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
\d document_chunks
SELECT d.original_filename, d.index_status, count(c.id) AS chunks, vector_dims(min(c.embedding::text)::vector) AS dims
FROM documents d LEFT JOIN document_chunks c ON c.document_id = d.id GROUP BY d.id;
```

### Document search (RAG)

```
upload  →  extract text (per PDF page)  →  600-char chunks  →  Gemini embeddings (once)  →  document_chunks (pgvector)
question  →  Agent Core search_documents tool  →  POST /api/v1/documents/search  →  embed the question  →  cosine search  →  passages + sources  →  Gemini answer
```

- **Embeddings**: `gemini-embedding-2` with `outputDimensionality=768` (the API default is 3072; 768 keeps the column within pgvector's 2000-dimension HNSW limit). The model ignores `taskType`, so queries and passages get the task as a text prefix (`task: search result | query: …` / `title: … | text: …`). Set in `backend/.env`: `EMBEDDING_PROVIDER`, `EMBEDDING_API_KEY` (a Gemini key; never sent to the frontend), `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`.
- **Storage**: `document_chunks` (`embedding vector(768)`, page number, content hash, metadata), foreign keys to `documents` and `users` with `ON DELETE CASCADE`, unique per (document, chunk index).
- **Search**: cosine distance, HNSW index (`vector_cosine_ops`), always filtered by the signed-in user's id; results below `DOCUMENT_SEARCH_MIN_SIMILARITY` (0.65, calibrated on real notes) are dropped, so an unrelated question returns "No relevant document content found."
- **Cost**: a document is embedded once when uploaded (100 passages per request); re-indexing unchanged text reuses the stored vectors. Each search embeds only the question. Free-tier quotas are per minute; indexing waits and retries, and failed documents are retried by the scheduler or with "Retry indexing" on the Documents page.
- **Boundaries**: Agent Core never touches the database. It calls the backend API with the user's token. The frontend only sees the indexing status.

## Frontend

React 19 · TypeScript · Vite · Tailwind CSS v4 · TanStack Query · Zustand · React Router 7

```powershell
cd frontend
npm ci
npm run dev      # http://localhost:5173
npm run build    # type-check + production build
npm run lint     # oxlint
```

### Architecture

```
pages/  →  hooks/ (React Query)  →  services/  →  api.ts  →  backend /api/v1
```

All services call the real backend through `services/api.ts`. 
### Design system

- **Tokens**: every colour, shadow and font lives in [`frontend/src/index.css`](frontend/src/index.css) under `@theme` (`bg-surface`, `text-fg-muted`, `border-line`, `bg-accent`, `text-danger`, …). Don't hard-code hex values in components.
- **Type**: Inter for UI and JetBrains Mono for code/IDs, using a 12 / 14 / 16 / 20 / 24 px scale.
- **Status colours**: defined once in [`frontend/src/utils/status.ts`](frontend/src/utils/status.ts) (priority, bill, reminder, run, approval, goal and document statuses).
- **Components**: in [`frontend/src/components/ui`](frontend/src/components/ui).
  - Layout: `PageHeader`, `Panel`, `StatCard`, `Table`, `Toolbar`, `Tabs` (underline + segmented)
  - Menus and feedback: `RowActions`, `Modal`, `ConfirmDialog`, `EmptyState`, `Badge`, `Progress`
  - Form controls: share one `Field` shell.
- **Formatting**: dates, times and INR currency via [`frontend/src/utils/formatters.ts`](frontend/src/utils/formatters.ts). Dates are local calendar dates, not UTC.

## Hosting for students

Every student signs up with their own email. **Signing in takes two steps**: the password, then a 6-digit code emailed to them through [EmailJS](https://www.emailjs.com). The session (JWT) is only issued after the code is accepted, so every signed-in student has proved they read that inbox. The code:

- expires after 5 minutes, and only a keyed hash of it is stored
- works once, and stops working after 5 wrong tries (the student then signs in again)
- is replaced by "Resend OTP", which has a 30-second cooldown and allows at most 5 codes per 15 minutes

Reminders, bill due dates and upcoming events also arrive in **the student's own inbox** (as well as in the app). Students can turn emails off in Settings > Notifications. Forgot password sends a single-use reset link valid for 30 minutes.

Before going live, set these in `backend/.env` on the server:

| Setting | Why |
| --- | --- |
| `APP_ENV=production` | Turns off the API docs and refuses to start with development secrets |
| `JWT_SECRET`, `JWT_REFRESH_SECRET` | Long random values (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) |
| `APP_BASE_URL=https://your-domain` | Links in reset and reminder emails point here |
| `CORS_ORIGINS=https://your-domain` | The only site allowed to call the API |
| `EMAILJS_SERVICE_ID`, `EMAILJS_TEMPLATE_ID`, `EMAILJS_NOTIFICATION_TEMPLATE_ID`, `EMAILJS_PUBLIC_KEY`, `EMAILJS_PRIVATE_KEY` | Sends the sign-in codes, reminders and reset links. Required: without them nobody can sign in |
| `SCHEDULER_ENABLED=true` | Sends reminders every minute. Enable it on **one** backend instance only (or run `python -m scripts.run_scheduler` as one separate process) |

**Setting up EmailJS.** In the EmailJS dashboard:

1. **Email Services**: connect the mailbox that sends the emails. Copy its Service ID.
2. **Email Templates**: create two templates and set **To Email** to `{{to_email}}` in both.
   - Login code (`EMAILJS_TEMPLATE_ID`): subject `Your AgentOS Login OTP`. Body: "Hello {{name}}, Your AgentOS verification code is: {{otp}}. This code expires in 5 minutes. If you did not attempt to log in, you can safely ignore this email. AgentOS"
   - Notifications (`EMAILJS_NOTIFICATION_TEMPLATE_ID`): subject `{{subject}}`, body `Hello {{name}},` followed by `{{message}}`.
3. **Account > General**: copy the Public Key and the Private Key.
4. **Account > Security**: enable API access for non-browser applications, since the backend calls EmailJS from the server.

The free plan has a small monthly email quota (check EmailJS's current limits). Every sign-in uses one email, so a class of students may need a paid plan.
