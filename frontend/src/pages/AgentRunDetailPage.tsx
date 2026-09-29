import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { ChevronRight, CircleCheck, CircleX, Loader2, MessageSquare, Circle } from 'lucide-react';
import { useAgentRunDetail } from '../hooks/useAgentRuns';
import type { AgentStep } from '../types';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Card, Panel } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { Skeleton } from '../components/ui/Skeleton';
import { formatDate } from '../utils/formatters';
import { RUN_STATUS_STYLES, statusStyle } from '../utils/status';
import { cn } from '../utils/cn';

const STEP_ICONS: Record<AgentStep['status'], React.ReactNode> = {
  completed: <CircleCheck className="size-4 text-success" />,
  failed: <CircleX className="size-4 text-danger" />,
  running: <Loader2 className="size-4 text-accent animate-spin" />,
  pending: <Circle className="size-4 text-fg-faint" />,
};

export const AgentRunDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { run, isLoading } = useAgentRunDetail(id || '');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (stepId: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(stepId)) next.delete(stepId);
      else next.add(stepId);
      return next;
    });

  if (isLoading) {
    return (
      <Page>
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-72 w-full" />
      </Page>
    );
  }

  if (!run) {
    return (
      <Page>
        <PageHeader title="Run not found" back={{ to: '/agent-runs', label: 'Agent activity' }} />
        <EmptyState title="This run doesn't exist" description="It may have been removed, or the link is incorrect." />
      </Page>
    );
  }

  const s = statusStyle(RUN_STATUS_STYLES, run.status);
  const meta = [
    { label: 'Status', value: <Badge variant={s.variant} dot>{s.label}</Badge> },
    { label: 'Duration', value: <span className="font-mono">{run.duration}</span> },
    { label: 'Started', value: formatDate(run.startedAt) },
    { label: 'Steps', value: run.steps.length },
  ];

  return (
    <Page>
      <PageHeader
        back={{ to: '/agent-runs', label: 'Agent activity' }}
        title={`Run ${run.runNumber}`}
        description={run.request}
      />

      <Card flush>
        <dl className="grid grid-cols-2 md:grid-cols-4 divide-line [&>div]:border-line">
          {meta.map((m, i) => (
            <div
              key={m.label}
              className={cn('px-5 py-4', i % 2 === 1 && 'border-l', i >= 2 && 'border-t md:border-t-0', i === 2 && 'md:border-l')}
            >
              <dt className="text-xs text-fg-subtle">{m.label}</dt>
              <dd className="mt-1 text-sm font-medium text-fg">{m.value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Panel title="Execution trace" description="Each step the agent took, with tool inputs and outputs.">
        <ol className="px-5 py-5">
          <li className="relative flex gap-3 pb-6">
            <span className="absolute left-[7.5px] top-6 bottom-0 w-px bg-line" />
            <MessageSquare className="size-4 text-fg-subtle mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-fg">Request received</p>
              <p className="text-sm text-fg-subtle mt-0.5">“{run.request}”</p>
            </div>
          </li>

          {run.steps.map((step, idx) => {
            const isOpen = expanded.has(step.id);
            const hasPayload = !!(step.toolInput || step.toolOutput);
            const isLast = idx === run.steps.length - 1;
            return (
              <li key={step.id} className={cn('relative flex gap-3', !isLast && 'pb-4')}>
                {!isLast && <span className="absolute left-[7.5px] top-6 bottom-0 w-px bg-line" />}
                <span className="mt-2.5 shrink-0 bg-surface">{STEP_ICONS[step.status]}</span>
                <div className="min-w-0 flex-1 rounded-lg border border-line">
                  <button
                    onClick={() => hasPayload && toggle(step.id)}
                    aria-expanded={hasPayload ? isOpen : undefined}
                    className={cn(
                      'w-full flex items-center gap-3 px-3.5 py-2.5 text-left rounded-lg',
                      hasPayload ? 'hover:bg-subtle/70' : 'cursor-default'
                    )}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-fg truncate">{step.title}</p>
                      {step.toolName && <code className="font-mono text-xs text-fg-subtle">{step.toolName}</code>}
                    </div>
                    <span className="font-mono text-xs text-fg-faint shrink-0">{step.timestamp}</span>
                    {hasPayload && (
                      <ChevronRight className={cn('size-4 text-fg-faint shrink-0 transition-transform', isOpen && 'rotate-90')} />
                    )}
                  </button>
                  {isOpen && hasPayload && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 px-3.5 pb-3.5 animate-fade-in">
                      {step.toolInput && <Payload label="Input" data={step.toolInput} />}
                      {step.toolOutput && <Payload label="Output" data={step.toolOutput} />}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </Panel>
    </Page>
  );
};

const Payload: React.FC<{ label: string; data: Record<string, unknown> }> = ({ label, data }) => (
  <div className="min-w-0">
    <p className="text-xs font-medium text-fg-subtle mb-1.5">{label}</p>
    <pre className="font-mono text-xs leading-relaxed text-fg bg-subtle border border-line rounded-md p-3 overflow-x-auto">
      {JSON.stringify(data, null, 2)}
    </pre>
  </div>
);
