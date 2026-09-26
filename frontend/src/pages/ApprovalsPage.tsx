import React, { useState } from 'react';
import { ShieldCheck, CheckCircle2, XCircle } from 'lucide-react';
import { useApprovals } from '../hooks/useApprovals';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Tabs } from '../components/ui/Tabs';
import { EmptyState } from '../components/ui/EmptyState';
import { formatRelativeTime } from '../utils/formatters';

export const ApprovalsPage: React.FC = () => {
  const { approvals, respondToApproval, isResponding } = useApprovals();
  const [activeTab, setActiveTab] = useState<'pending' | 'history'>('pending');

  const pendingApprovals = approvals.filter((a) => a.status === 'pending');
  const historyApprovals = approvals.filter((a) => a.status !== 'pending');

  const filteredApprovals = activeTab === 'pending' ? pendingApprovals : historyApprovals;

  const tabs = [
    { id: 'pending', label: 'Pending Approvals', badge: pendingApprovals.length },
    { id: 'history', label: 'Approval History', badge: historyApprovals.length },
  ];

  return (
    <div className="space-y-6 text-left max-w-4xl">
      {/* Header Bar */}
      <div className="pb-2 border-b border-[#EAEAEA]">
        <h1 className="text-lg sm:text-xl font-bold text-[#111111] tracking-tight">Pending Approvals</h1>
        <p className="text-xs text-[#666666] mt-0.5">
          Review and authorize high-impact actions drafted by your AI assistant
        </p>
      </div>

      {/* Tabs */}
      <Tabs tabs={tabs} activeTab={activeTab} onChange={(id) => setActiveTab(id as any)} variant="underline" />

      {/* Approvals List */}
      {filteredApprovals.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck className="w-8 h-8 text-[#8A8A8A]" />}
          title={`No ${activeTab} approvals`}
          description="There are currently no AI actions requiring your authorization."
        />
      ) : (
        <div className="space-y-4">
          {filteredApprovals.map((action) => (
            <Card key={action.id} className="space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded bg-[#F7F7F7] border border-[#EAEAEA]">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-[#8A8A8A] uppercase tracking-wider">
                      {action.type}
                    </span>
                    <h3 className="text-xs sm:text-sm font-semibold text-[#111111]">{action.title}</h3>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Badge
                    variant={
                      action.status === 'pending'
                        ? 'warning'
                        : action.status === 'approved'
                        ? 'success'
                        : 'error'
                    }
                    size="sm"
                  >
                    {action.status}
                  </Badge>
                  <span className="text-[11px] text-[#8A8A8A]">
                    {formatRelativeTime(action.requestedAt)}
                  </span>
                </div>
              </div>

              <p className="text-xs text-[#666666] leading-relaxed">{action.description}</p>

              {action.details && (
                <div className="rounded-md bg-[#F7F7F7] border border-[#EAEAEA] p-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                  {Object.entries(action.details).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between">
                      <span className="text-[#8A8A8A] font-medium">{k}:</span>
                      <span className="font-semibold text-[#111111]">{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}

              {action.status === 'pending' ? (
                <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#EAEAEA]">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => respondToApproval({ id: action.id, decision: 'rejected' })}
                    isLoading={isResponding}
                    leftIcon={<XCircle className="w-3.5 h-3.5 text-rose-600" />}
                  >
                    Reject
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => respondToApproval({ id: action.id, decision: 'approved' })}
                    isLoading={isResponding}
                    leftIcon={<CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                  >
                    Approve Action
                  </Button>
                </div>
              ) : (
                <div className="pt-2 border-t border-[#EAEAEA] text-[11px] text-[#8A8A8A] flex items-center justify-between">
                  <span>
                    Status:{' '}
                    <strong className={action.status === 'approved' ? 'text-emerald-700' : 'text-rose-600'}>
                      {action.status.toUpperCase()}
                    </strong>
                  </span>
                  {action.respondedAt && <span>Responded {formatRelativeTime(action.respondedAt)}</span>}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
