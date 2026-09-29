import type { ApprovalAction, ApprovalStatus } from '../types';
import { api } from './api';

interface ApprovalOut {
  id: string;
  agentRunId: string | null;
  action: string;
  actionLabel: string;
  title: string;
  description: string | null;
  details: Record<string, unknown>;
  status: ApprovalStatus;
  expiresAt: string | null;
  respondedAt: string | null;
  createdAt: string;
}

const toApproval = (a: ApprovalOut): ApprovalAction => ({
  id: a.id,
  runId: a.agentRunId ?? undefined,
  action: a.action,
  type: a.actionLabel,
  title: a.title,
  description: a.description ?? '',
  details: a.details,
  status: a.status,
  requestedAt: a.createdAt,
  respondedAt: a.respondedAt ?? undefined,
  expiresAt: a.expiresAt ?? undefined,
});

export const approvalService = {
  async getApprovals(): Promise<ApprovalAction[]> {
    return (await api.getAll<ApprovalOut>('/approvals')).map(toApproval);
  },

  /** Approving applies exactly the previewed change on the server; rejecting discards it. */
  async respondToApproval(id: string, decision: 'approved' | 'rejected'): Promise<ApprovalAction> {
    const path = decision === 'approved' ? 'approve' : 'reject';
    return toApproval(await api.post<ApprovalOut>(`/approvals/${id}/${path}`));
  },
};
