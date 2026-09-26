import React from 'react';
import { Calendar, Bell, CheckCircle2, XCircle, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { ActionCardData } from '../../types';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { cn } from '../../utils/cn';

export interface ActionCardProps {
  card: ActionCardData;
  messageId: string;
  onDecision: (messageId: string, decision: 'approved' | 'rejected') => void;
  isPending?: boolean;
}

export const ActionCard: React.FC<ActionCardProps> = ({
  card,
  messageId,
  onDecision,
  isPending = false,
}) => {
  const navigate = useNavigate();

  return (
    <div className="mt-3 w-full max-w-sm rounded-lg border border-[#EAEAEA] bg-white p-3.5 text-left shadow-xs transition-all">
      <div className="flex items-center justify-between border-b border-[#EAEAEA] pb-2.5 mb-2.5">
        <div className="flex items-center gap-2">
          {card.type === 'create_reminder' && <Bell className="w-4 h-4 text-[#111111]" />}
          {card.type === 'study_plan_generated' && <Calendar className="w-4 h-4 text-[#111111]" />}
          <span className="text-xs font-semibold text-[#111111]">{card.title}</span>
        </div>
        <Badge
          variant={
            card.status === 'approved'
              ? 'success'
              : card.status === 'rejected'
              ? 'error'
              : 'warning'
          }
          size="sm"
        >
          {card.status === 'pending'
            ? 'Requires Approval'
            : card.status === 'approved'
            ? 'Approved'
            : 'Rejected'}
        </Badge>
      </div>

      {card.subtitle && <p className="text-xs text-[#666666] mb-2">{card.subtitle}</p>}

      {card.details && (
        <div className="rounded bg-[#F7F7F7] border border-[#EAEAEA] p-2.5 space-y-1 mb-3 text-[11px]">
          {Object.entries(card.details).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-[#8A8A8A] font-medium">{key}:</span>
              <span className="text-[#111111] font-semibold">{String(value)}</span>
            </div>
          ))}
        </div>
      )}

      {card.status === 'pending' ? (
        <div className="flex items-center justify-end gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onDecision(messageId, 'rejected')}
            isLoading={isPending}
            leftIcon={<XCircle className="w-3.5 h-3.5 text-rose-600" />}
          >
            Reject
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => onDecision(messageId, 'approved')}
            isLoading={isPending}
            leftIcon={<CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
          >
            Approve
          </Button>
        </div>
      ) : (
        <div className="flex items-center justify-between pt-1 text-xs">
          <span
            className={cn(
              'font-medium text-[11px]',
              card.status === 'approved' ? 'text-emerald-700' : 'text-rose-600'
            )}
          >
            {card.status === 'approved' ? '✓ Action executed successfully' : '✕ Action cancelled'}
          </span>
          {card.type === 'study_plan_generated' && card.status === 'approved' && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => navigate('/study-plan')}
              rightIcon={<ArrowRight className="w-3 h-3" />}
            >
              View Plan
            </Button>
          )}
        </div>
      )}
    </div>
  );
};
