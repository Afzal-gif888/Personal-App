# AgentOS Architecture Audit

AUDIT COMPLETE: 2026-09-29, against the running system: PostgreSQL 18.6 (`agentos` at localhost:5432), backend (:8000), Agent Core (:8001) and frontend (:5173). Evidence scripts and their outputs are summarised under each section. Test data was created in dedicated `audit-*@audit-agentos.dev` users; the demo account was not modified.

Status legend: **PASS** means verified working end to end. **PARTIAL** means part of it works, or it works outside the production path. **FAIL** means verified broken or absent. **NOT VERIFIED** means it couldn't be tested (the reason is given). **MOCK / SIMULATED** means it only appears implemented.

---

## A. Executive summary

Scored against the 34 acceptance criteria in section 34 of the brief (PASS = 1, PARTIAL = 0.5, FAIL/NOT VERIFIED = 0):

| Result | Count |
| --- | --- |
| PASS | 19 |
| PARTIAL | 13 |
| FAIL | 1 |
| NOT VERIFIED | 1 |
| **Score** | **25.5 / 34 = 75%** |

| Area | Status |
| --- | --- |
| Architecture compliance | **PARTIAL**: the production chat runs the backend's own agent loop, not the Agent Core's LangGraph graph |
| Backend implementation | PASS, with the layering gaps listed below |
| Database persistence | **PASS**: 56/56 persistence, isolation and restart checks against real PostgreSQL |
| Agent Core | **PARTIAL**: LangGraph, tools, RAG and approvals work against the real backend, but the Agent Core isn't in the production path and its runs and approvals aren't persisted |
| Frontend integration | PASS for API integration; three backend features have no UI; one hard-coded list |
| Security | PARTIAL: no critical issues; medium-severity findings below |
| End-to-end functionality | PARTIAL: chat → agent → tools → PostgreSQL works via the backend loop; reminders never fire in the default setup |

**The single most important finding:** the backend runs its own non-LangGraph agent loop (`backend/app/agent/runner.py`, 17 tools). With `AGENT_CORE_MODE=http` it uses the Agent Core only as a model proxy (`/v1/complete`). The Agent Core's LangGraph graph, 42 tools, memory, RAG and approval policy are therefore **not used by the app's chat**, even though they work when called directly.

---

## 1. Architecture status

| Component | Expected | Actual | Status | Evidence |
| --- | --- | --- | --- | --- |
| Frontend | React + TS, REST only | React 19 + TS + Vite; single `api.ts` client to `/api/v1`; no DB, LLM or agent code | PASS | build and lint clean; 65 calls, all matching live backend routes |
| Backend | FastAPI + services + repositories | FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, argon2, JWT | PARTIAL | no repository layer (1 helper file, 34 lines); notification routes query the DB directly |
| Database | PostgreSQL | PostgreSQL 18.6, Alembic at head `0002`, no model/migration drift | PASS | `alembic current` = `0002 (head)`, `alembic check`: no operations |
| Agent Core | LangGraph orchestration | LangGraph graph with 9 nodes and conditional edges; works against the real backend | PARTIAL | not in the production chat path (see above) |
| Agent loop location | Agent Core only | the **backend** contains an agent loop (`app/agent/runner.py`) | **FAIL (violation)** | `services/chat.py` → `run_agent(...)` → `get_provider()` → `AgentCoreProvider` (`/v1/complete`) |
| Agent tools | Agent Core → BackendClient → API | Agent Core: 42 tools over HTTP. Backend loop: 17 tools calling services in-process | PARTIAL | both verified executing; the production path uses the backend's 17 |
| Agent Core ↔ DB | never direct | no DB driver or ORM anywhere in Agent Core | PASS | grep for sqlalchemy/psycopg/asyncpg/DATABASE_URL: none; none installed |
| Persistent chat | PostgreSQL | `conversations` + `messages` rows; readable after restart | PASS | phase 1/2 evidence |
| Approvals | backend DB | backend loop: `approvals` table ✔. Agent Core: **in-memory only** | PARTIAL | Agent Core approval `apr_bd72…`: 0 rows in `approvals` |
| Agent runs | persisted | backend loop: `agent_runs` + `tool_calls` ✔. Agent Core runs: **not persisted** | PARTIAL | 4 Agent Core runs → `agent_runs` delta 0 |
| RAG | pipeline + vector store | Agent Core: extraction, chunking, hashing embeddings, in-memory store. No pgvector (not installed or available). Backend loop has no retrieval | PARTIAL | Agent Core answered from an uploaded note; production chat can't |
| Notifications | scheduler + delivery | scheduler exists but is disabled (`SCHEDULER_ENABLED=false`) and not started by `start.ps1`; in-app rows only; no UI | PARTIAL | see §7 test N1 |

## 2. Frontend status

| Feature | Mock | Real API | Status |
| --- | --- | --- | --- |
| Auth (register/login/refresh/logout) | no | yes | PASS |
| Dashboard | no | yes (composes 9 hooks; `GET /dashboard` unused) | PASS |
| Chat + inline approvals | no | yes | PASS |
| Tasks, calendar/events, reminders, goals, expenses, budgets | no | yes | PASS |
| Bills, payments, payment plans | no | yes | PASS |
| Documents | no | yes (upload/list/delete) | PASS |
| Agent runs, approvals | no | yes | PASS |
| Settings (profile, preferences, notifications) | no | yes | PASS |
| Study plan: subjects list | **HARD-CODED** (`StudyPlanPage.tsx` `SUBJECTS` constant) | `GET /subjects` never called | PARTIAL |
| Subscriptions | no UI (only mentioned in a page description) | backend has full CRUD | FAIL (missing) |
| Notification inbox | no UI | backend `GET /notifications` never called | FAIL (missing) |
| Subjects management, saved study-plan list | no UI | backend routes unused | missing |

`localStorage` holds only UI state (chat drafts, active conversation) and the auth tokens (security finding M1). There are no mock data files in `frontend/src`.

## 3. Backend status

| Feature | Endpoint | Service | Repository | Status |
| --- | --- | --- | --- | --- |
| Auth | `/auth/*`, `/users/me*` | `auth_service`, `user_service` | helper only | PASS |
| Planning (tasks, events, reminders, study, goals) | `/tasks`, `/events`, … | per-domain services | helper only | PASS |
| Finance | `/bills`, `/payments`, … | `finance`, `budgets` | helper only | PASS |
| Documents | `/documents` | `documents` + local storage | helper only | PASS |
| Chat and agent runs | `/conversations/*`, `/agent-runs` | `chat`, `agent_runs` + in-backend agent loop | helper only | PARTIAL (loop belongs in Agent Core) |
| Approvals | `/approvals/*` | `approvals` | helper only | PASS |
| Notifications | `/notifications/*` | **none: queries in routes** | – | PARTIAL (violation) |

## 4. PostgreSQL status

All 22 expected tables exist in the live database with primary keys, `created_at` and (where they apply) `updated_at`. `messages` and `tool_calls` have no direct `user_id`; they're owned through `conversations`/`agent_runs`, and the isolation tests confirm ownership is enforced. Extra tables: `budgets`, `refresh_tokens`, `alembic_version`. Extension `vector` is **not available** on this server.

| Table | Exists | Schema matches models | Persistence tested | Status |
| --- | --- | --- | --- | --- |
| users, tasks, events, reminders, bills, expenses, goals, conversations, messages | ✔ | ✔ | create → PG → restart → read → update → delete/complete | PASS |
| payments | ✔ | ✔ | bill pay → payments row | PASS |
| study_plans, study_sessions | ✔ | ✔ | approval → 1 plan + 10 sessions | PASS |
| agent_runs, tool_calls, approvals | ✔ | ✔ | backend-loop runs, calls, approvals and decisions | PASS (backend loop only) |
| notifications | ✔ | ✔ | scheduler run → row `sent` | PASS (manual scheduler) |
| documents | ✔ | ✔ | upload → row + file on disk → download identical | PASS |
| subjects, user_preferences, audit_logs, payment_plans, subscriptions | ✔ | ✔ | not individually persistence-tested | NOT VERIFIED (schema only) |

## 5. Agent Core status

| Capability | Implemented | Used in production chat | Tested | Status |
| --- | --- | --- | --- | --- |
| LangGraph graph | ✔ 9 nodes, conditional edges | ✘ | real backend, mock LLM; unit tests | PARTIAL |
| Structured state | ✔ Pydantic `AgentState` (every field in brief §13) | ✘ | ✔ | PARTIAL |
| Planning | ✔ `plan` node (LLM, multi-step only) | ✘ (backend loop has none) | ✔ | PARTIAL |
| Tool registry | ✔ 42 tools, schemas, risk, scopes | ✘ | ✔ | PARTIAL |
| Tool execution | ✔ real backend calls | ✘ | ✔ PG changes observed | PARTIAL |
| Observations and iteration | ✔ | ✔ (backend loop also iterates) | ✔ | PASS |
| Memory | short-term window + whitelisted long-term prefs via backend | ✘ | unit tests | PARTIAL |
| RAG | ✔ in-memory, hashing embeddings | ✘ | real document retrieved | PARTIAL |
| Approvals | ✔ policy; **store is in-memory** | ✘ | ✔ | PARTIAL |
| BackendClient | ✔ user-token scoped | ✘ | ✔ | PARTIAL |
| Error recovery | ✔ limits, timeouts, model fallback | – | ✔ | PASS |
| Real LLM (Gemini) through LangGraph | ✔ | ✘ | ✘: free-tier daily quota exhausted during audit | NOT VERIFIED |

## 6. Agent tool matrix

**Agent Core (42 tools).** All are registered with input and output schemas, a risk level and a permission, and all are executable (unit-tested against a fake backend with identical routes). Tested against the **real** backend and PostgreSQL in this audit:

| Tool | Backend API | DB effect observed |
| --- | --- | --- |
| get_tasks, get_events, get_bills, get_reminders, get_goals, get_subjects | GET list routes | read (correct items) |
| create_study_plan | POST /study-plans/generate + /study-plans | +1 plan, +4 sessions |
| create_reminder | POST /reminders | +1 reminder |
| delete_task (approval) | DELETE /tasks/{id} | only after approval: −1 task |
| search_documents / RAG | GET /documents + download | retrieved `audit-notes.txt` |

The remaining 32 Agent Core tools are unit-tested only (not tested against the real backend).

**Backend loop (17 tools, production).** Tested live: `list_calendar`, `list_tasks`, `list_bills`, `list_reminders`, `list_documents`, `list_goals`, `create_study_plan` (approved → PG), `create_reminder` (rejected → nothing). Missing compared with the brief: update/delete for tasks and events, snooze, subjects, study sessions, payments, payment plans, subscriptions, goal updates, and document search.

## 7. End-to-end tests

| Test | Expected | Actual | Status |
| --- | --- | --- | --- |
| Auth: register/login/refresh/replay/expired/tampered/no token | correct accept/reject | 13/13 | PASS |
| User isolation (B → A's 7 entity types, messages, runs) | 404, rows intact | 20/20 | PASS |
| Persistence: create → PG → restart → read → update → delete | all reflected in PG | 33 + 23 checks | PASS |
| Chat persistence ("Hello, remember…") → restart | conversation + messages survive | ✔ | PASS |
| **Organize my week** (production path) | reads, plans, creates, approvals | 4 read tools; good plan text; **no writes proposed** | PARTIAL |
| **DBMS plan with reminders** (production path) | reads → create sessions + reminders → approval | 5 reads + 3 writes → 3 PG approvals → approve: +1 plan +10 sessions; reject: nothing | PASS (one earlier run failed: cause NOT VERIFIED) |
| Observation loop (water bill that doesn't exist) | adapts, doesn't pretend | searched twice, reported not found, offered options | PASS |
| Approval flow in backend DB | pending → approve/reject → effect | ✔ | PASS |
| Agent Core LangGraph → real backend (mock LLM) | tools change PG | ✔ see §6 | PASS (LLM mocked) |
| Agent Core with real Gemini | – | quota exhausted (20 requests/day/model) | NOT VERIFIED |
| N1: due reminder → notification | fires automatically | nothing until `run_scheduler --once` run by hand; then row `sent`; no UI shows it | PARTIAL |
| Document upload/validation/download | stored + validated | ✔ `.exe` and fake PDF → 415 | PASS |
| Frontend UI interaction | – | no browser automation available; verified at the API/proxy level only | NOT VERIFIED |

## 8. Security findings

| Severity | Finding |
| --- | --- |
| CRITICAL | none found |
| HIGH | none found |
| MEDIUM | M1: access and refresh tokens stored in `localStorage` (readable by any injected script) |
| MEDIUM | M2: Agent Core approvals are in-memory: lost on restart, not auditable in PostgreSQL |
| MEDIUM | M3: the API sends no `X-Frame-Options`/CSP (`nosniff` and `no-referrer` are present) |
| LOW | L1: `APP_ENV=development` in `backend/.env` (docs enabled) — fine locally, must change for deployment |
| LOW | L2: `start.ps1` log files are UTF-16 (harder to search) |
| OK | argon2 hashing; JWT validation (tampered/expired rejected); refresh rotation with replay detection; CORS limited to `localhost:5173` (evil-origin preflight refused); login rate limit (429 at attempt 19); parameterised queries; upload type and content validation; no secrets in git, the frontend build or the logs |

## 9. Architecture violations

1. The backend contains the agent reasoning loop (`backend/app/agent/runner.py`); the Agent Core is only a model proxy in production.
2. The Agent Core's LangGraph graph, tools, memory, RAG and approval policy are not in the production chat path.
3. Agent Core approvals are not stored in the backend database.
4. Agent Core runs and tool calls are not persisted.
5. Notification routes access the database directly (no service).
6. No repository layer (services query SQLAlchemy directly).

## 10. Missing features

Subscriptions UI; notification inbox UI; subjects UI; saved study-plan list UI; pgvector storage; document search in the production agent; a scheduler running by default; an agent "verify" step; frontend automated tests; `docker-compose.yml`.

## 11. Broken features

1. Reminders never trigger in the default setup (scheduler off and not started).
2. On the Gemini free tier the assistant fails when Google reports overload (3 failed runs recorded, before the model-fallback fix).
3. Free-tier capacity is about 20 requests per model per day, a few assistant questions each, so heavier use exhausts it quickly.

## 12. Fake / mock / simulated

- `StudyPlanPage.tsx` `SUBJECTS`: **HARD-CODED** subject list.
- Agent Core `InMemoryApprovalStore` and `InMemoryVectorStore`: **IN-MEMORY**.
- `MockLLMProvider`: intentional development mock, used only when no LLM key is configured.
- The backend's `app/llm/mock.py`: intentional keyword mock for `AGENT_CORE_MODE=local` with no key.

## 13. Database evidence (sample)

```text
POST /api/v1/tasks {"title":"AUDIT task",…} → 201 id=…
SELECT id,user_id FROM tasks WHERE id=… → 1 row, user_id = audit user A
stop.ps1 / start.ps1 (all services restarted)
GET /api/v1/tasks (via frontend proxy :5173) → contains the task
PATCH priority=low → SELECT priority → 'low'
PATCH status=completed → SELECT status, completed_at → 'completed', timestamp set
```

The same sequence passed for events, reminders, bills (plus the payments row), expenses, goals, conversations and messages.

## 14. Agent execution evidence (production path)

```text
Request:   "I have not studied DBMS yet and my exam is Monday. Check my schedule and create a realistic study plan with reminders."
Run:       agent_runs b0fd1cde…  status waiting_for_approval
Tools:     1 list_calendar {start 09-29, end 10-05}   completed
           2 list_tasks {status open}                 completed
           3 list_documents {}                        completed
           4 list_goals {}                            completed
           5 list_reminders {}                        completed
           6 create_study_plan {DBMS, 5 days, 120 min/day, topics…}  waiting_for_approval
           7 create_reminder {daily 09:00 from 09-30}                  waiting_for_approval
           8 create_reminder {exam day 08:00}                          waiting_for_approval
DB:        approvals +3 (pending)
Approve #1 → approvals.status=approved, study_plans +1, study_sessions +10
Reject  #2 → approvals.status=rejected, no reminder created
Response:  summary of the schedule, the drafted plan (5 days, avoiding the project meeting and ML exam) and the reminders awaiting approval
```

## 15. Final verdict

**PARTIALLY IMPLEMENTED.** Persistence, authentication, isolation, the API contract and a genuinely tool-using agent with database-backed approvals all work against real PostgreSQL. However, the production agent is the backend's own loop rather than the Agent Core's LangGraph graph. Agent Core approvals and runs aren't persisted, reminders never fire by default, and the free-tier LLM is capacity-limited.

---

## Remediation plan

| Phase | Problem | Root cause | Files | Change | How to test |
| --- | --- | --- | --- | --- | --- |
| 1 | Backend runs the agent loop; LangGraph unused | chat calls `run_agent` → `/v1/complete` | backend `services/chat.py`, `llm/agent_core.py`, `core/config.py`, `api/deps.py`, route | new `AGENT_CORE_MODE=agent`: chat calls Agent Core `/agent/run` with the user's token; the backend persists the returned run, tool calls and approvals | chat → `agent_runs`/`tool_calls` rows whose tool names are Agent Core tools |
| 1/2 | Agent Core approvals in memory | `InMemoryApprovalStore` | Agent Core `main.py`; backend `services/approvals.py` | backend stores every approval in PostgreSQL; approving calls Agent Core `POST /agent/actions/execute` (service-token only) to run exactly that payload | approve → approvals row `approved` + PG effect; survives Agent Core restart |
| 3 | Notification routes query the DB | no service | backend `routes/platform.py`, new `services/notifications.py` | move the queries into a service | existing tests + API check |
| 3 | Reminders never fire | scheduler disabled / not started | `backend/.env`, docs | enable the in-process scheduler for the single local instance | due reminder → notification within a minute |
| 4 | Free-tier quota exhausted quickly | 20 requests/day/model; extra planning call | `agent-core/.env` | `LLM_PLANNING=false` on the free tier (fallback chain already added) | fewer calls per question |
| 5 | Hard-coded subjects | constant in page | `StudyPlanPage.tsx`, new subject service/hook | load from `GET /subjects` | page shows DB subjects |
| 5 | No notification inbox | no UI | new hook + header bell | list, unread count, mark read | reminder → visible in app |
| 6 | Missing security headers | middleware | backend `main.py` | `X-Frame-Options: DENY`, `Content-Security-Policy: frame-ancestors 'none'` for API responses | header check |
| 6 | Tokens in localStorage | client design | frontend auth | deferred: needs httpOnly-cookie auth (backend + frontend) | – |
| 7 | UTF-16 logs | PS 5.1 `Tee-Object` | `start.ps1` | write UTF-8 | grep works |
| 8 | No repository layer; subscriptions UI; pgvector; docker-compose; frontend tests | scope | several | deferred (see "Missing features") | – |

Fixes already made during the audit (verified problems):
- **Gemini model fallback chain.** Google returned 503/429 for single models; the provider now moves to the next free model with a per-attempt timeout, and stays on the one that worked.
- **Thought-signature fix.** Gemini rejects function calls that lack a valid signature ("missing"/"corrupted"). History from another model now uses Google's placeholder signature (verified: 400 → 200).
- **`start.ps1` logs.** The Python services' logs are now saved to `logs/`.

---

## Re-verification after fixes (same day)

### What changed

| Fix | Files | Test |
| --- | --- | --- |
| Production chat now runs the **Agent Core LangGraph agent** (`AGENT_CORE_MODE=agent`). The backend forwards the user's token and persists the run, tool calls and approvals | backend `agent/remote.py` (new), `services/chat.py`, `api/deps.py` (`AccessToken`), `routes/platform.py`, `core/config.py`, `llm/__init__.py`, `.env` | `tests/test_agent_remote.py` (6 tests) |
| Approvals for Agent Core actions live in **PostgreSQL**. Approving validates owner/pending/expiry in the backend, then calls Agent Core `POST /agent/actions/execute` (service token only) with exactly the stored payload | backend `services/approvals.py`; Agent Core `main.py` | 2 Agent Core API tests + backend tests |
| "Asks before it acts" kept: Agent Core `MUTATION_POLICY=approval` | `agent-core/.env` | re-verification |
| Notification DB access moved from routes to a service | backend `services/notifications.py` (new), `routes/platform.py` | no DB calls left in any route file |
| Reminders fire automatically: `SCHEDULER_ENABLED=true` (single local instance) | `backend/.env` | re-verification |
| Notification inbox in the header (bell, unread badge, mark read / all) | frontend `services/notificationService.ts`, `hooks/useNotifications.ts`, `layout/Header.tsx` | build + lint |
| Hard-coded subjects and hard-coded "Machine Learning" plan generation replaced by `GET /subjects` | frontend `services/subjectService.ts`, `hooks/useSubjects.ts`, `pages/StudyPlanPage.tsx` | build + lint |
| `X-Frame-Options: DENY` and a strict CSP on API responses | backend `main.py` | `test_security_headers` |
| Gemini model fallback chain and thought-signature placeholder | Agent Core `llm/gemini.py`, `config/settings.py` | 4 new tests |
| Free-tier quota saving: `LLM_PLANNING=false` | `agent-core/.env` | – |
| `start.ps1` saves UTF-8 logs to `logs/` | `start.ps1` | logs searchable |

Test suites: Agent Core **124 passed**, backend **46 passed**, pyright 0 errors (both), ruff clean, frontend build and lint clean.

### Live re-verification (full stack; Agent Core on the mock model because the Gemini daily quota was exhausted)

```text
chat (via :5173 proxy) → backend agent mode → Agent Core LangGraph → backend tools → PostgreSQL
[PASS] chat HTTP 201 and run persisted in agent_runs
[PASS] run executed by the LangGraph Agent Core                 (metadata.engine = langgraph)
[PASS] Agent Core tool calls persisted in tool_calls            (get_tasks, get_events, get_bills, get_reminders, get_goals)
[PASS] assistant message carries the tool steps
[PASS] create_study_plan held for approval and stored in PostgreSQL
[PASS] nothing created before approval
[PASS] delete_task held for approval in PostgreSQL
[PASS] approvals survive a full restart (stop.ps1 / start.ps1)
[PASS] another user cannot approve it (404)
[PASS] approve → executed by the Agent Core → study_plans=1, study_sessions=4
[PASS] reject → task untouched
[PASS] second approve refused (409)
[PASS] in-process scheduler created the reminder notification (visible via GET /notifications)
13/13
```

The real-Gemini run of "Organize my week" on the new path returned a clean "busy" error: `3.7` was overloaded, and `3.8`, `3.6` and `3.5` hit `GenerateRequestsPerDayPerProjectPerModel-FreeTier = 20`. **NOT VERIFIED (quota)**. Retry after the daily reset.

### Acceptance criteria after fixes

PASS 27 · PARTIAL 6 · FAIL 1 · NOT VERIFIED 0 → **30/34 = 88%** (was 75%).

| Still PARTIAL / FAIL | Why |
| --- | --- |
| Frontend works: PARTIAL | build, lint and API contract verified; no browser-level UI tests exist |
| Agent Core works: PARTIAL | verified end to end with the mock model and with single real Gemini calls; a full real-Gemini run on the new path wasn't possible (quota) |
| Agent can plan: PARTIAL | planning node exists but is turned off (`LLM_PLANNING=false`) to save free-tier quota |
| RAG: PARTIAL | now in the production path, but the index is in memory with keyword-style embeddings; pgvector isn't installed on this PostgreSQL |
| Security: PARTIAL | tokens still in `localStorage` (needs httpOnly-cookie auth) |
| End-to-end workflows: PARTIAL | pass with the mock model; real-model workflow NOT VERIFIED today |
| Agent verifies actions: **FAIL** | there's no verify step: the agent relies on the backend's success response and doesn't re-read what it changed |

**Verdict after fixes: PARTIALLY IMPLEMENTED.** The architecture now matches the design: the production chat runs the LangGraph Agent Core, which acts only through the backend API, and runs, tool calls and approvals are persisted in PostgreSQL and survive restarts. What keeps it from READY is listed in the table above.
