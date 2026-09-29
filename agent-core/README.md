# AgentOS Agent Core

The Agent Core is the reasoning service behind the AgentOS assistant. It takes a student's message, works out what they need, plans, calls tools to read or change their data through the AgentOS backend, and returns a user-facing answer along with a safe execution trace.

It is a separate service. It has no database connection, serves no frontend, and can be started and tested on its own.

```text
Frontend  ──►  Backend (FastAPI, PostgreSQL)  ──►  Agent Core  ──►  LLM (Gemini or Claude)
                     ▲                                  │
                     └──────── /api/v1 (user token) ◄───┘
```

## Why it is separate from the backend

- **One owner for data.** The backend owns PostgreSQL, validation and authorization. The Agent Core only uses the backend's public API, so it can never bypass a business rule.
- **Least privilege.** Every backend call carries the signed-in user's own access token. The backend decides whose data is reachable. The Agent Core never trusts a `user_id` from a caller.
- **Independent scaling and releases.** LLM calls are slow and bursty. Keeping them out of the API process means agent changes don't redeploy the backend.
- **Testability.** The test suite runs the whole agent with a test-double LLM (`tests/mock_llm.py`) against a fake backend, with no API key and no database. The application itself has no mock mode.

## Architecture

```text
app/
├── main.py            FastAPI service: /agent/run, approvals, /health, /ready, /v1/complete
├── agent/
│   ├── graph.py       LangGraph workflow + AgentRunner (timeout, recursion limit, response shaping)
│   ├── state.py       Typed, serializable AgentState (Pydantic)
│   ├── nodes.py       One function per graph node
│   ├── router.py      Request understanding + conditional edges
│   └── prompts.py     System and planning prompts
├── llm/               LLMProvider interface, GeminiProvider, AnthropicProvider, UnconfiguredLLMProvider, factory
├── tools/             ToolRegistry + task/event/reminder/study/finance/goal/document/memory tools
├── memory/            ShortTermMemory, LongTermMemory, MemoryManager
├── rag/               Extraction, chunking, EmbeddingProvider, VectorStore, Retriever, RagService
├── backend/           BackendClient (httpx), response schemas, typed exceptions
├── approvals/         ApprovalManager + ApprovalStore
├── config/            Settings (environment variables only)
├── schemas/           Agent, tool, memory and event contracts
└── security.py        Redaction, log filter, constant-time token compare
```

## LangGraph workflow

The loop is expressed as graph edges, not a hand-written `while` loop:

```text
START
  │
validate_input ──(invalid)──────────────────────────────┐
  │                                                      │
load_context ──(auth / backend error)───────────────────┤
  │   user identity, preferences, recent conversation    │
understand_request                                       │
  │   domains, needs_documents, multi_step               │
gather_context                                           │
  │   small domain snapshot; RAG only for document asks  │
plan                                                     │
  │   LLM planning pass for multi-step requests          │
agent  ◄──────────────────────────┐                      │
  │  LLM picks tools or answers   │                      │
  ├──(tool calls)──► execute_tools│                      │
  │                      │        │                      │
  │                   observe ────┘ (continue)           │
  │                      └──(limit reached)──────────────┤
  └──(answer / refusal / error / tool limit)─────────────┤
                                                         ▼
                                                  final_response ──► END
```

- **validate_input:** checks for an empty or oversized message.
- **load_context:** confirms the user with the backend (`GET /users/me`). It then loads preferences (long-term memory) and the recent conversation (short-term memory).
- **understand_request:** deterministic intent detection. It limits the tools offered to the relevant domains and decides whether document retrieval and a planning pass are needed. The LLM still chooses which tools to call.
- **gather_context:** adds a small, bounded snapshot for narrow requests, such as bills due this week. For document questions only, it runs RAG and puts the relevant excerpts in state.
- **plan:** a tool-free LLM call that writes a short numbered plan for multi-step requests. The plan is used internally and is never returned to the client.
- **agent:** one LLM turn with the scoped tool list.
- **execute_tools:** validates each call's input and checks permissions and the approval policy. It runs independent calls concurrently and returns all results to the model in one message.
- **observe:** records compact observations, collects retrieved passages and enforces the iteration limit.
- **final_response:** sets the run status (`completed`, `approval_required`, `incomplete` or `failed`) and a user-safe message.

### Loop safety

| Guard | Setting | Behaviour |
| --- | --- | --- |
| Model turns | `MAX_AGENT_ITERATIONS` (10) | The loop stops with status `incomplete` and a summary of what was done |
| Tool calls per run | `MAX_TOOL_CALLS` (20) | A batch that would exceed the limit is not executed |
| Wall clock | `AGENT_TIMEOUT_SECONDS` (120) | The run is cancelled and returns `TIMEOUT` (retryable) |
| Per tool | `TOOL_TIMEOUT_SECONDS` (20) | That call fails and the model sees the error |
| Graph steps | LangGraph `recursion_limit` = 3 × iterations + 10 | Backstop for the limits above |

## LLM integration

`LLMProvider.invoke(system, messages, tools, purpose)` is the only interface the graph uses. Transcripts use the Messages API content-block shape (`text`, `tool_use` and `tool_result`), which the backend already uses. Each provider translates at its edge.

| `LLM_PROVIDER` | Provider | `LLM_API_KEY` | Default `LLM_MODEL` |
| --- | --- | --- | --- |
| `openrouter` | `OpenRouterProvider` (OpenRouter, OpenAI-compatible) | OpenRouter key from openrouter.ai/keys (free `:free` models) | `qwen/qwen3.8-27b:free` |
| `gemini` | `GeminiProvider` (Google Gemini) | Gemini API key from aistudio.google.com (free tier) | `gemini-3.8-flash` |
| `anthropic` | `AnthropicProvider` (Claude) | Claude API key from console.anthropic.com (paid) | `claude-opus-5` |

A Claude Pro or Max subscription does not include API access: the API key and its billing come from the Claude Console.

**Running for free with Gemini.** A Google AI Studio key works without billing on free-tier models (for example `gemini-3.8-flash`, `gemini-3.5-flash`). The `gemini-2.5-*` models are no longer available to new API users. Two trade-offs:

- **Privacy:** on the free tier, Google may use prompts and responses to improve its products. Assistant requests include the student's tasks, bills and document excerpts. Use a paid tier for real users' data.
- **Quota:** free-tier requests are rate-limited (see AI Studio for your limits). Each question takes 2–3 model calls, plus one for planning on multi-step requests; set `LLM_PLANNING=false` to save quota.

- **`AnthropicProvider`** uses the official `anthropic` SDK (`AsyncAnthropic`).
  - The default model is `claude-opus-5`, with adaptive thinking.
  - Planning calls are tool-free and run at low effort.
  - Tool definitions and the system prompt form a cached prefix.
  - Server-side refusal fallback (`fallbacks: "default"`) is on for models that support it, and mid-output fallback content is sanitised before it is echoed back.
  - SDK errors map to safe `LLMError`s that mark whether they are retryable or rate-limited.
- **`OpenRouterProvider`** calls `POST https://openrouter.ai/api/v1/chat/completions`. `tool_use`/`tool_result` map to OpenAI-style `tool_calls` and `role: "tool"` messages. Backup models go in OpenRouter's `models` array, so fallback happens inside one request. A 429 is retried once only if the suggested wait is 4 seconds or less; 402 (no credits) and 401 (bad key) fail with a clear message.
- **Request budget.** `LLM_MAX_REQUESTS_PER_MINUTE` / `LLM_MAX_REQUESTS_PER_DAY` wrap any provider in `BudgetedProvider`: when a cap is reached the assistant replies "try again later" without making the call. With planning off, a question costs 2-3 calls (act, maybe act again, answer) and never more than `MAX_AGENT_ITERATIONS`.
- **`GeminiProvider`** calls `generateContent` (`https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`, `x-goog-api-key` header) with `httpx`.
  - `tool_use` maps to `functionCall` parts and `tool_result` to `functionResponse` parts. Tool schemas are converted to the OpenAPI subset Gemini accepts: `$ref`s are inlined, `Optional` becomes `nullable`, and unsupported keywords are dropped.
  - Gemini's `thoughtSignature`s are kept on each block (`gemini_part`) and sent back unchanged on the next turn, as newer models require.
  - `429 RESOURCE_EXHAUSTED` and 5xx are retried when the suggested wait is 8 seconds or less. Longer quota waits fail fast with "usage limit reached".
  - Safety blocks map to a refusal; `MALFORMED_FUNCTION_CALL` returns a "please rephrase" message.
- **No key, no fake answers.** Without `LLM_API_KEY` the factory returns `UnconfiguredLLMProvider`: every run fails with "The assistant isn't set up yet…" and `/ready` returns 503. In production the service refuses to start. The deterministic `MockLLMProvider` lives in `tests/mock_llm.py` and is used only by the test suite.

API keys come only from `LLM_API_KEY`. They are stored as `SecretStr`, never logged, and never sent to the frontend or the backend.

## Tools

Every tool declares a name, description, Pydantic input and output schemas, a domain, a risk level (which drives approvals) and a permission scope (`<domain>:read|write`). Inputs are snake_case for the LLM and camelCase for the backend. Unknown fields are rejected.

| Domain | Tools |
| --- | --- |
| Tasks | `get_tasks`, `get_task`, `create_task`, `update_task`, `complete_task`, `delete_task` |
| Events | `get_events`, `create_event`, `update_event`, `delete_event` |
| Reminders | `get_reminders`, `create_reminder`, `complete_reminder`, `snooze_reminder`, `cancel_reminder` |
| Study | `get_subjects`, `get_study_plan`, `get_study_sessions`, `create_study_plan`, `update_study_plan`, `create_study_session`, `complete_study_session` |
| Finance | `get_bills`, `create_bill`, `update_bill`, `mark_bill_paid`, `get_payments`, `get_payment_plans`, `create_payment_plan`, `get_expenses`, `get_expense_summary`, `create_expense`, `get_subscriptions`, `create_subscription` |
| Goals | `get_goals`, `create_goal`, `update_goal`, `update_goal_progress` |
| Documents | `get_documents`, `get_document`, `search_documents` |
| Memory | `remember_preference` |

Task categories are `academic`, `personal`, `financial`, `career` and `general`. Event types include classes, meetings, appointments, interviews and exams.

**Finance tools are for tracking only.** They cannot access bank accounts, move money, make payments, or store card or banking details. `mark_bill_paid` only records a payment the student already made elsewhere.

`GET /agent/tools` returns the full catalogue with its JSON schemas. `ToolRegistry.as_langchain_tools()` exposes the read-only tools as LangChain `StructuredTool`s. Mutating tools are excluded so they always go through the approval policy.

## Memory

- **Short-term:** the recent conversation and this run's working state (plan, tool results, observations).
  - The backend owns conversation storage. It either sends `history` with the request, or the Agent Core fetches `/conversations/{id}/messages`.
  - The window is limited by message count and characters, and is normalised to strict user/assistant alternation.
- **Long-term:** a whitelist of stable preferences:
  - study start and end time
  - default reminder time
  - daily study goal
  - timezone

  Values are validated and stored in the backend's user preferences. Nothing is inferred from conversation text: a preference is written only when the model calls `remember_preference`, which is subject to the approval policy.

## RAG

```text
backend document ─► download (user token) ─► text extraction (txt/md/csv/pdf) ─► paragraph chunking
                                                                                     │
question ─► strip "where to look" words ─► embed ─► VectorStore.search (per user) ◄──┘ embed + upsert
                                                        │
                                              chunks ≥ RAG_MIN_SCORE ─► agent state ─► LLM
```

- Retrieval runs only for document questions such as "according to my notes…". The model can also call `search_documents`.
- Documents are indexed on demand and re-indexed when they change. The version is tracked by size and `processedAt`.
- The store is namespaced per user, so one student's passages can never be returned to another.
- `EmbeddingProvider`, `VectorStore`, `Retriever` and `DocumentChunk` are separate abstractions.
  - The bundled `HashingEmbeddingProvider` is deterministic and needs no key, but it matches words, not meaning.
  - `InMemoryVectorStore` is in-process.
  - See "Remaining work" for pgvector.

## Approvals

| Risk | Examples | Policy |
| --- | --- | --- |
| `read` | `get_tasks`, `get_bills`, `search_documents` | Always runs |
| `mutate` | `create_task`, `create_reminder`, `create_goal`, `create_expense` | Runs directly when `MUTATION_POLICY=direct`; queued when `MUTATION_POLICY=approval` |
| `consequential` | `delete_task`, `delete_event` | Always needs approval |

When approval is needed, nothing runs:

1. The validated input is stored, and the run returns `status: "approval_required"` with `action_type`, `action_payload`, `reason` and `expires_at`.
2. `POST /agent/approvals/{id}/approve` runs exactly that payload, once, for the same user.
3. `POST /agent/approvals/{id}/reject` discards it.

Approvals belonging to another user return 404. Expired approvals can't run. A second decision on the same approval returns 409.

## Backend communication

The backend calls the Agent Core with two headers:

```http
POST /agent/run
Authorization: Bearer <AGENT_CORE_SERVICE_TOKEN>      # proves the caller is the backend
X-User-Authorization: Bearer <user's access token>    # used for every backend call
X-Agent-Scopes: tasks:read,finance:read               # optional: narrow what the agent may do
Content-Type: application/json

{"message": "What should I finish this week?", "conversation_id": "…", "user_id": "…"}
```

`user_id` is optional. If it is sent, it must match the user the token belongs to; otherwise the request returns 403.

Response:

```json
{
  "run_id": "run_…",
  "status": "completed | approval_required | incomplete | failed",
  "response": "user-facing answer",
  "tool_calls": [{"id": "…", "name": "get_bills", "input": {…}, "status": "completed", "output": {…}, "duration_ms": 12}],
  "approval_required": false,
  "approvals": [],
  "retrieved_documents": [],
  "events": [{"type": "RUN_STARTED", "run_id": "…", "timestamp": "…", "data": {}}, …],
  "error": null,
  "metadata": {"iterations": 2, "tool_call_count": 1, "plan_steps": 1, "domains": ["finance"], "model": "…"}
}
```

**Events:**

- `RUN_STARTED`
- `CONTEXT_LOADED`
- `REQUEST_UNDERSTOOD`
- `DOCUMENTS_RETRIEVED`
- `PLANNING_STARTED`
- `PLAN_CREATED`
- `TOOL_STARTED`
- `TOOL_COMPLETED`
- `TOOL_FAILED`
- `APPROVAL_REQUIRED`
- `LIMIT_REACHED`
- `RUN_COMPLETED`
- `RUN_FAILED`

Events carry only safe metadata. Prompts, reasoning and transcripts are never returned.

Errors always have the shape `{"error": {"code", "message", "details?"}}`. Stack traces are logged, never returned.

### Other endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Liveness |
| `GET /ready` | Checks the backend is reachable, and reports the LLM provider, tool count and vector store. Returns 503 if the backend is down |
| `GET /agent/tools` | Tool catalogue |
| `GET /agent/approvals/{id}`, `POST …/approve`, `POST …/reject` | Approval decisions |
| `POST /v1/complete` | Single-turn contract used by the existing backend's `AGENT_CORE_MODE=http` |

**How the backend uses it:** with `AGENT_CORE_MODE=agent` (the default in this project's `backend/.env`), the backend's chat calls `/agent/run` with the user's token and stores the returned run, tool calls and approvals in PostgreSQL. Approving one of those actions calls `POST /agent/actions/execute` (service token only), which runs exactly the stored payload. So approvals are durable and shared across restarts; the in-memory `ApprovalManager` is only used when the Agent Core is called directly. `AGENT_CORE_MODE=http` (model calls only, via `/v1/complete`) is still supported.

## Environment variables

See [`.env.example`](.env.example). The main ones:

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_ENV` | `development` | In `production`, the service refuses to start without `AGENT_CORE_SERVICE_TOKEN`, and without `LLM_API_KEY` when `LLM_PROVIDER` is `gemini` or `anthropic` |
| `AGENT_CORE_PORT` | `8001` | |
| `AGENT_CORE_SERVICE_TOKEN` | empty | Shared secret with the backend |
| `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_MODEL` | `gemini` / empty / provider default | `gemini` (free tier) or `anthropic`; the key must match the provider |
| `LLM_PLANNING` | `true` | `false` skips the planning call (saves free-tier quota) |
| `BACKEND_API_URL` | `http://localhost:8000` | The backend base URL, without `/api/v1` |
| `MAX_AGENT_ITERATIONS` / `MAX_TOOL_CALLS` / `AGENT_TIMEOUT_SECONDS` | 10 / 20 / 120 | |
| `MUTATION_POLICY` | `direct` | `direct` or `approval` |
| `VECTOR_STORE` / `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` | in-memory / hashing / empty | |

## Local development

```powershell
cd agent-core
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env          # then set LLM_API_KEY (Gemini key from aistudio.google.com)
uvicorn app.main:create_app --factory --port 8001
```

Start the backend first (see the root README). The Agent Core runs without it, but `/ready` returns 503 and agent runs fail with `BACKEND_UNAVAILABLE`.

## Docker

```bash
docker build -t agentos-agent-core .
docker run --rm -p 8001:8001 --env-file .env -e BACKEND_API_URL=http://host.docker.internal:8000 agentos-agent-core
```

The image uses Python 3.12-slim, runs as a non-root user and includes a `/health` healthcheck.

## Testing

```powershell
pytest            # 118 tests; no API key, database or network needed
ruff check .
```

- **`tests/tools`:** each tool on its own against `tests/fakes.py`, an in-memory backend with the same routes, camelCase JSON, per-token scoping and error shape as the real one.
- **`tests/unit`:** router, LLM layer (Anthropic against a stub client, Gemini against a stubbed API, no-key behaviour), memory rules, RAG, approvals and redaction.
- **`tests/integration`:** the full graph and the HTTP API.
  - Agent flows: simple, multi-step, study plan, reminder, RAG, and no retrieval for unrelated requests.
  - Approvals: required, accepted, rejected and expired.
  - Failures: tool failure, malformed or unknown tool calls, iteration and tool limits, timeout, LLM error and rate limit, crash with no leaked internals.
  - Security: `user_id` spoofing, per-user isolation, auth headers, scopes, and no secrets in logs.

## Remaining work

- **Verify step.** After a write, the agent trusts the backend's response; add a node that re-reads what changed before replying.
- **pgvector.** There is no backend vector API yet, so the index is in-memory and rebuilt after a restart. The backend should expose chunk upsert and search endpoints backed by pgvector, with a `VectorStore` implementation calling them.
- **Semantic embeddings.** The hashing embedder matches words, not meaning. Add a hosted embedding provider behind `EmbeddingProvider`.
- **Streaming.** Events are returned when the run finishes. Server-sent events would let the UI show progress live.
- **Real-model evaluation.** The Anthropic and Gemini paths are unit-tested against stubbed APIs. Run it with a real key and build an eval set before relying on it.
