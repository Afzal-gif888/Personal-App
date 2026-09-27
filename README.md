# AgentOS

A personal AI workspace for students. One place for coursework, calendar, bills, expenses and goals, with an assistant that **plans with you and asks before it acts**.

> Status: frontend prototype. All data is served by mock services in the browser; a FastAPI backend is planned.

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
| Sign in | `/login` | Demo account is pre-filled via **Use demo account** |
| Daily overview | Home `/dashboard` | Stats, the live workflow pipeline, tasks due soon, 7-day schedule, pending approvals, bills, goals |
| Make a request | Assistant `/chat` | Conversation history, starter prompts, drafts saved per conversation |
| Agent run | Agent activity `/agent-runs` | Audit log: request, status, tools, duration; drill into `/agent-runs/:id` for the step trace with tool inputs/outputs |
| Review | Inline action card, or Approvals `/approvals` | Approve or reject; decisions move to **History** |
| Result | Tasks, Reminders, Study plan | Approved items are created here and can also be managed by hand |
| Manage everything else | Calendar, Goals, Documents, Bills & payments, Expenses | Standard create / edit / delete with filters |
| Configure | Settings `/settings/*` | Profile, notification channels, assistant defaults (study window, reminder time, time zone) |

## Information architecture

Navigation follows the workflow and is defined once in [`frontend/src/config/navigation.ts`](frontend/src/config/navigation.ts). The sidebar, mobile drawer, command menu (Ctrl/⌘ K) and breadcrumbs all read from it.

- **Workspace**: Home, Assistant, Approvals
- **Planning**: Tasks, Calendar, Reminders, Goals
- **Study**: Study plan, Documents
- **Finance**: Bills & payments, Expenses
- **Automation**: Agent activity

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
pages/  →  hooks/ (React Query)  →  services/ (mock API, FastAPI-shaped)  →  storage.ts + mocks/
```

To connect the backend, swap the service implementations for `fetch` calls against `VITE_API_BASE_URL`. Hooks and pages don't need to change. Never put secrets in `VITE_*` variables: they are embedded in the browser bundle.

### Design system

- **Tokens**: every colour, shadow and font lives in [`frontend/src/index.css`](frontend/src/index.css) under `@theme` (`bg-surface`, `text-fg-muted`, `border-line`, `bg-accent`, `text-danger`, …). Don't hard-code hex values in components.
- **Type**: Inter for UI and JetBrains Mono for code/IDs, using a 12 / 14 / 16 / 20 / 24 px scale.
- **Status colours**: defined once in [`frontend/src/utils/status.ts`](frontend/src/utils/status.ts) (priority, bill, reminder, run, approval, goal and document statuses).
- **Components**: in [`frontend/src/components/ui`](frontend/src/components/ui).
  - Layout: `PageHeader`, `Panel`, `StatCard`, `Table`, `Toolbar`, `Tabs` (underline + segmented)
  - Menus and feedback: `RowActions`, `Modal`, `ConfirmDialog`, `EmptyState`, `Badge`, `Progress`
  - Form controls: share one `Field` shell.
- **Formatting**: dates, times and INR currency via [`frontend/src/utils/formatters.ts`](frontend/src/utils/formatters.ts). Dates are local calendar dates, not UTC.
