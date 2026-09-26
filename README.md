# AgentOS

AgentOS is organized as three independent components with API boundaries:

- [`frontend/`](frontend/README.md): the existing React and TypeScript application.
- [`backend/`](backend/README.md): FastAPI authentication, persistence, REST APIs, and Agent Core client. This is now bootstrapped; see its README for implemented scope and schema limitations.
- [`agent-core/`](agent-core/README.md): the AI runtime, prompts, tools, memory, and workflows. No Agent Core implementation existed in this checkout when the separation was made.

## Communication boundaries

```text
Browser (frontend) -- REST/JSON --> Backend -- Agent API --> Agent Core
                                            <-- result -----
                                             |
                                        PostgreSQL
```

The frontend must not hold database credentials, LLM credentials, or agent implementation. Agent Core must call backend-owned capabilities through an authenticated service interface; it must not connect to PostgreSQL. The Agent Core client contract is described in the backend README. The frontend API contract is still evolving; do not import source code between folders.

## Run what exists

```powershell
cd frontend
npm ci
npm run dev
```

The frontend currently uses its existing mock services. The backend can run independently with Docker. `agent-core/` remains a boundary/documentation directory and is not a runnable service yet. The backend uses a development mock response until Agent Core is configured; end-to-end integration is not complete.

## Environment

Keep frontend variables limited to public browser configuration (for example, a future `VITE_API_BASE_URL`). Never put secrets in `VITE_*` variables. Backend and Agent Core secrets belong in their respective local environment files, which must be ignored by Git; commit only `.env.example` templates.

## Component ownership

See each component README for scope, setup status, and the contract still required to make the whole system runnable.
