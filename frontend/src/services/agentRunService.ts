import type { AgentRun, AgentRunStatus, AgentStep } from '../types';
import { api } from './api';

interface AgentRunOut {
  id: string;
  runNumber: number;
  request: string;
  status: 'queued' | 'running' | 'waiting_for_approval' | 'completed' | 'failed' | 'cancelled';
  startedAt: string | null;
  completedAt: string | null;
  durationMs: number | null;
  errorMessage: string | null;
  toolsUsed: string[];
  createdAt: string;
}

interface ToolCallOut {
  id: string;
  toolName: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'waiting_for_approval' | 'skipped';
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: string | null;
  completedAt: string | null;
  createdAt: string;
}

interface AgentRunDetailOut extends AgentRunOut {
  toolCalls: ToolCallOut[];
}

const STATUS: Record<AgentRunOut['status'], AgentRunStatus> = {
  queued: 'running',
  running: 'running',
  waiting_for_approval: 'awaiting_approval',
  completed: 'completed',
  failed: 'failed',
  cancelled: 'failed',
};

function formatDuration(ms: number | null): string {
  if (ms == null) return '—';
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
}

/** "list_tasks" → "List tasks" */
const humanize = (name: string) => name.charAt(0).toUpperCase() + name.slice(1).replace(/_/g, ' ');

function toStep(c: ToolCallOut): AgentStep {
  return {
    id: c.id,
    title: c.status === 'waiting_for_approval' ? `${humanize(c.toolName)} (awaiting approval)` : humanize(c.toolName),
    status: c.status === 'failed' ? 'failed' : c.status === 'pending' || c.status === 'running' ? 'running' : 'completed',
    timestamp: c.completedAt ?? c.createdAt,
    toolName: c.toolName,
    toolInput: c.input,
    toolOutput: c.output ?? (c.error ? { error: c.error } : undefined),
  };
}

function toRun(r: AgentRunOut, steps: AgentStep[] = []): AgentRun {
  return {
    id: r.id,
    runNumber: `#${r.runNumber}`,
    request: r.request,
    status: STATUS[r.status],
    startedAt: r.startedAt ?? r.createdAt,
    completedAt: r.completedAt ?? undefined,
    duration: formatDuration(r.durationMs),
    toolsUsed: r.toolsUsed,
    steps,
    errorMessage: r.errorMessage ?? undefined,
  };
}

export const agentRunService = {
  /** Runs without their step trace; open a run for the full detail. */
  async getAgentRuns(): Promise<AgentRun[]> {
    return (await api.getAll<AgentRunOut>('/agent-runs')).map((r) => toRun(r));
  },

  async getAgentRunById(id: string): Promise<AgentRun | undefined> {
    const run = await api.get<AgentRunDetailOut>(`/agent-runs/${id}`);
    return toRun(run, run.toolCalls.map(toStep));
  },
};
