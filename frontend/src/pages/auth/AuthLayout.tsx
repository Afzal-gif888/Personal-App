import React from 'react';
import { MessageSquare, ShieldCheck, LayoutGrid } from 'lucide-react';
import { Logo } from '../../components/ui/Logo';

const WORKFLOW = [
  {
    icon: MessageSquare,
    title: 'Ask in plain language',
    body: '“Plan my ML exam revision” or “What bills are due this week?”',
  },
  {
    icon: ShieldCheck,
    title: 'Review before anything changes',
    body: 'The assistant drafts reminders, tasks and study sessions. You approve or reject each one.',
  },
  {
    icon: LayoutGrid,
    title: 'Track everything in one place',
    body: 'Coursework, calendar, bills, expenses and goals — with a full log of every agent run.',
  },
];

export const AuthLayout: React.FC<{ title: string; description: string; children: React.ReactNode }> = ({
  title,
  description,
  children,
}) => (
  <div className="min-h-screen flex bg-surface">
    <div className="flex-1 flex flex-col px-6 sm:px-10 py-8">
      <Logo size="sm" withText />
      <div className="flex-1 flex items-center justify-center py-10">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold tracking-tight text-fg">{title}</h1>
          <p className="mt-1.5 text-sm text-fg-subtle">{description}</p>
          <div className="mt-8">{children}</div>
        </div>
      </div>
      <p className="text-xs text-fg-faint">© {new Date().getFullYear()} AgentOS · Demo environment — data is stored in your browser.</p>
    </div>

    <aside className="hidden lg:flex w-[46%] max-w-2xl flex-col justify-center px-14 xl:px-20 bg-canvas border-l border-line">
      <p className="text-sm font-medium text-accent">Personal AI workspace for students</p>
      <h2 className="mt-3 text-3xl font-semibold tracking-tight text-fg leading-tight">
        An assistant that plans with you — and asks before it acts.
      </h2>
      <ol className="mt-10 space-y-6">
        {WORKFLOW.map(({ icon: Icon, title, body }, i) => (
          <li key={title} className="flex gap-4">
            <span className="flex items-center justify-center size-9 shrink-0 rounded-lg border border-line bg-surface shadow-xs text-fg-muted">
              <Icon className="size-4" />
            </span>
            <div>
              <p className="text-sm font-semibold text-fg">
                <span className="text-fg-faint tabular mr-1.5">0{i + 1}</span>
                {title}
              </p>
              <p className="mt-1 text-sm text-fg-subtle">{body}</p>
            </div>
          </li>
        ))}
      </ol>
    </aside>
  </div>
);
