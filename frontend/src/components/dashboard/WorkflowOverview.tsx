import React from 'react';
import { Link } from 'react-router-dom';
import { MessageSquare, Workflow, ShieldCheck, LayoutGrid, ChevronRight } from 'lucide-react';
import { cn } from '../../utils/cn';

interface WorkflowOverviewProps {
  runCount: number;
  pendingCount: number;
  approvedCount: number;
  openTaskCount: number;
}

/**
 * The product's core loop, shown with live numbers:
 * Ask → Agent plans → You approve → Tracked in your workspace.
 */
export const WorkflowOverview: React.FC<WorkflowOverviewProps> = ({ runCount, pendingCount, approvedCount, openTaskCount }) => {
  const steps = [
    {
      icon: MessageSquare,
      title: 'Ask',
      body: 'Describe what you need in plain language.',
      metric: 'Open assistant',
      to: '/chat',
    },
    {
      icon: Workflow,
      title: 'Agent plans',
      body: 'Checks your tasks, calendar and finances, then drafts an action.',
      metric: `${runCount} runs logged`,
      to: '/agent-runs',
    },
    {
      icon: ShieldCheck,
      title: 'You approve',
      body: 'Nothing changes in your workspace until you say so.',
      metric: pendingCount ? `${pendingCount} awaiting review` : `${approvedCount} approved`,
      to: '/approvals',
      highlight: pendingCount > 0,
    },
    {
      icon: LayoutGrid,
      title: 'Tracked',
      body: 'Approved items land in Tasks, Reminders or Study plan.',
      metric: `${openTaskCount} open tasks`,
      to: '/tasks',
    },
  ];

  return (
    <section className="rounded-xl border border-line bg-surface shadow-xs">
      <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-5 py-4 border-b border-line">
        <h2 className="text-sm font-semibold text-fg">How your assistant works</h2>
        <p className="text-xs text-fg-subtle">Every AI action is reviewed by you and logged for audit.</p>
      </header>
      <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step, i) => {
          const Icon = step.icon;
          return (
            <li
              key={step.title}
              className={cn(
                'relative p-5 border-line',
                i > 0 && 'border-t sm:border-t-0',
                i % 2 === 1 && 'sm:border-l',
                i >= 2 && 'sm:border-t lg:border-t-0',
                i > 0 && 'lg:border-l'
              )}
            >
              <div className="flex items-center gap-2.5">
                <span
                  className={cn(
                    'flex items-center justify-center size-7 rounded-md border',
                    step.highlight ? 'bg-accent text-white border-accent' : 'bg-subtle text-fg-muted border-line'
                  )}
                >
                  <Icon className="size-4" />
                </span>
                <span className="text-xs font-medium text-fg-faint tabular">Step {i + 1}</span>
              </div>
              <h3 className="mt-3 text-sm font-semibold text-fg">{step.title}</h3>
              <p className="mt-1 text-sm text-fg-subtle">{step.body}</p>
              <Link
                to={step.to}
                className={cn(
                  'mt-3 inline-flex items-center gap-1 text-sm font-medium',
                  step.highlight ? 'text-accent hover:text-accent-hover' : 'text-fg-muted hover:text-fg'
                )}
              >
                {step.metric}
                <ChevronRight className="size-3.5" />
              </Link>
            </li>
          );
        })}
      </ol>
    </section>
  );
};
