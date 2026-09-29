import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, X, Inbox, Bell, CheckSquare, BookOpen, ShieldCheck, ArrowUpRight } from 'lucide-react';
import { useApprovals } from '../hooks/useApprovals';
import type { ApprovalAction } from '../types';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Tabs } from '../components/ui/Tabs';
import { EmptyState } from '../components/ui/EmptyState';
import { Table, THead, TBody, TR, TH, TD } from '../components/ui/Table';
import { DesktopOnly, MobileList, MobileRow } from '../components/ui/ResponsiveList';
import { formatRelativeTime, humanizeKey, formatDetailValue } from '../utils/formatters';
import { APPROVAL_STATUS_STYLES, statusStyle } from '../utils/status';

function destinationFor(type: string): { module: string; icon: React.ReactNode } {
  const t = type.toLowerCase();
  if (t.includes('reminder')) return { module: 'Reminders', icon: <Bell /> };
  if (t.includes('task')) return { module: 'Tasks', icon: <CheckSquare /> };
  if (t.includes('study')) return { module: 'Study plan', icon: <BookOpen /> };
  return { module: 'your workspace', icon: <ShieldCheck /> };
}

const runLink = (runId?: string) => (runId ? `/agent-runs/${runId.replace('run-', '')}` : undefined);

export const ApprovalsPage: React.FC = () => {
  const { approvals, respondToApproval, isResponding } = useApprovals();
  const [activeTab, setActiveTab] = useState<'pending' | 'history'>('pending');

  const pending = approvals.filter((a) => a.status === 'pending');
  const history = approvals
    .filter((a) => a.status !== 'pending')
    .sort((a, b) => (b.respondedAt || b.requestedAt).localeCompare(a.respondedAt || a.requestedAt));

  return (
    <Page>
      <PageHeader
        title="Approvals"
        description="Actions proposed by the assistant. Nothing is created or changed until you approve it."
      />

      <Tabs
        activeTab={activeTab}
        onChange={(id) => setActiveTab(id as 'pending' | 'history')}
        tabs={[
          { id: 'pending', label: 'Needs review', badge: pending.length },
          { id: 'history', label: 'History', badge: history.length },
        ]}
      />

      {activeTab === 'pending' ? (
        pending.length === 0 ? (
          <EmptyState
            icon={<Inbox />}
            title="You're all caught up"
            description="When the assistant proposes an action — like creating a reminder or task — it will appear here for review."
          />
        ) : (
          <div className="space-y-4">
            {pending.map((action) => (
              <ApprovalCard
                key={action.id}
                action={action}
                disabled={isResponding}
                onDecide={(decision) => respondToApproval({ id: action.id, decision })}
              />
            ))}
          </div>
        )
      ) : history.length === 0 ? (
        <EmptyState icon={<Inbox />} title="No decisions yet" description="Approved and rejected actions will be listed here." />
      ) : (
        <Card flush className="overflow-hidden">
          <MobileList>
            {history.map((a) => {
              const s = statusStyle(APPROVAL_STATUS_STYLES, a.status);
              return (
                <MobileRow
                  key={a.id}
                  title={a.title}
                  subtitle={`${a.type} · decided ${a.respondedAt ? formatRelativeTime(a.respondedAt) : '—'}`}
                  meta={
                    <Badge variant={s.variant} dot>
                      {s.label}
                    </Badge>
                  }
                />
              );
            })}
          </MobileList>
          <DesktopOnly>
          <Table>
            <THead>
              <tr>
                <TH>Action</TH>
                <TH className="hidden md:table-cell">Type</TH>
                <TH>Decision</TH>
                <TH className="hidden sm:table-cell">Requested</TH>
                <TH className="hidden sm:table-cell">Decided</TH>
              </tr>
            </THead>
            <TBody>
              {history.map((a) => {
                const s = statusStyle(APPROVAL_STATUS_STYLES, a.status);
                return (
                  <TR key={a.id}>
                    <TD className="w-full max-w-0 font-medium truncate">{a.title}</TD>
                    <TD className="hidden md:table-cell text-fg-muted">{a.type}</TD>
                    <TD>
                      <Badge variant={s.variant} dot>
                        {s.label}
                      </Badge>
                    </TD>
                    <TD className="hidden sm:table-cell text-fg-muted whitespace-nowrap">{formatRelativeTime(a.requestedAt)}</TD>
                    <TD className="hidden sm:table-cell text-fg-muted whitespace-nowrap">
                      {a.respondedAt ? formatRelativeTime(a.respondedAt) : '—'}
                    </TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>
          </DesktopOnly>
        </Card>
      )}
    </Page>
  );
};

const ApprovalCard: React.FC<{
  action: ApprovalAction;
  disabled: boolean;
  onDecide: (decision: 'approved' | 'rejected') => void;
}> = ({ action, disabled, onDecide }) => {
  const dest = destinationFor(action.type);
  const link = runLink(action.runId);

  return (
    <Card flush className="overflow-hidden">
      <div className="flex items-start gap-4 p-5">
        <span className="hidden sm:flex items-center justify-center size-10 shrink-0 rounded-lg border border-line bg-subtle text-fg-muted [&_svg]:size-5">
          {dest.icon}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-xs font-medium text-fg-subtle">{action.type}</span>
            <span className="text-xs text-fg-faint">Requested {formatRelativeTime(action.requestedAt)}</span>
            {link && (
              <Link to={link} className="inline-flex items-center gap-0.5 text-xs font-medium text-accent hover:text-accent-hover">
                From run {action.runId?.replace('run-', '#')}
                <ArrowUpRight className="size-3" />
              </Link>
            )}
          </div>
          <h2 className="mt-1 text-base font-semibold text-fg">{action.title}</h2>
          <p className="mt-1 text-sm text-fg-subtle">{action.description}</p>

          {action.details && Object.keys(action.details).length > 0 && (
            <dl className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-x-6 gap-y-3 rounded-lg border border-line bg-subtle/50 px-4 py-3">
              {Object.entries(action.details).map(([k, v]) => (
                <div key={k} className="min-w-0">
                  <dt className="text-xs text-fg-subtle">{humanizeKey(k)}</dt>
                  <dd className="text-sm font-medium text-fg break-words">{formatDetailValue(v)}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>
      <div className="flex flex-col-reverse sm:flex-row sm:items-center justify-between gap-3 px-5 py-3 border-t border-line bg-subtle/40">
        <p className="text-xs text-fg-subtle">Approving will add this to {dest.module}.</p>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" disabled={disabled} onClick={() => onDecide('rejected')} leftIcon={<X className="size-4" />}>
            Reject
          </Button>
          <Button size="sm" disabled={disabled} onClick={() => onDecide('approved')} leftIcon={<Check className="size-4" />}>
            Approve
          </Button>
        </div>
      </div>
    </Card>
  );
};
