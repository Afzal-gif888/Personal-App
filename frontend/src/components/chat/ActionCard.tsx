import React from 'react';
import { Link } from 'react-router-dom';
import { Bell, BookOpen, CheckSquare, ShieldCheck, Check, X, ArrowRight, CircleCheck, CircleX } from 'lucide-react';
import type { ActionCardData, ActionCardType } from '../../types';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { humanizeKey, formatDetailValue } from '../../utils/formatters';

export interface ActionCardProps {
  card: ActionCardData;
  messageId: string;
  onDecision: (messageId: string, decision: 'approved' | 'rejected') => void;
  isPending?: boolean;
}

/** Where an approved action lands in the workspace. */
const DESTINATIONS: Record<ActionCardType, { label: string; module: string; path: string; icon: React.ReactNode }> = {
  create_reminder: { label: 'Create reminder', module: 'Reminders', path: '/reminders', icon: <Bell /> },
  study_plan_generated: { label: 'Add study sessions', module: 'Study plan', path: '/study-plan', icon: <BookOpen /> },
  task_created: { label: 'Create task', module: 'Tasks', path: '/tasks', icon: <CheckSquare /> },
  approval_required: { label: 'Action', module: 'Approvals', path: '/approvals', icon: <ShieldCheck /> },
};

export const ActionCard: React.FC<ActionCardProps> = ({ card, messageId, onDecision, isPending = false }) => {
  const dest = DESTINATIONS[card.type] ?? DESTINATIONS.approval_required;
  const isOpen = card.status === 'pending';
  const approved = card.status === 'approved' || card.status === 'executed';

  return (
    <div className="mt-3 w-full max-w-lg rounded-xl border border-line bg-surface shadow-xs overflow-hidden">
      <div className="flex items-start gap-3 px-4 py-3 border-b border-line bg-subtle/60">
        <span className="flex items-center justify-center size-8 shrink-0 rounded-md border border-line bg-surface text-fg-muted [&_svg]:size-4">
          {dest.icon}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-fg-subtle">Proposed action · {dest.label}</p>
          <p className="text-sm font-semibold text-fg truncate">{card.title}</p>
        </div>
        <Badge variant={isOpen ? 'warning' : approved ? 'success' : 'neutral'} dot>
          {isOpen ? 'Needs approval' : approved ? 'Approved' : 'Rejected'}
        </Badge>
      </div>

      {card.details && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2.5 px-4 py-3.5">
          {Object.entries(card.details).map(([key, value]) => (
            <div key={key} className="min-w-0">
              <dt className="text-xs text-fg-subtle">{humanizeKey(key)}</dt>
              <dd className="text-sm font-medium text-fg break-words">{formatDetailValue(value)}</dd>
            </div>
          ))}
        </dl>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-t border-line">
        {isOpen ? (
          <>
            <p className="text-xs text-fg-subtle">Nothing is saved until you approve.</p>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onDecision(messageId, 'rejected')}
                disabled={isPending}
                leftIcon={<X className="size-4" />}
              >
                Reject
              </Button>
              <Button
                size="sm"
                onClick={() => onDecision(messageId, 'approved')}
                isLoading={isPending}
                leftIcon={<Check className="size-4" />}
              >
                Approve
              </Button>
            </div>
          </>
        ) : approved ? (
          <>
            <p className="inline-flex items-center gap-1.5 text-sm text-success">
              <CircleCheck className="size-4" />
              Added to {dest.module}
            </p>
            <Link
              to={dest.path}
              className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:text-accent-hover"
            >
              Open {dest.module}
              <ArrowRight className="size-3.5" />
            </Link>
          </>
        ) : (
          <p className="inline-flex items-center gap-1.5 text-sm text-fg-subtle">
            <CircleX className="size-4" />
            Rejected — no changes were made
          </p>
        )}
      </div>
    </div>
  );
};
