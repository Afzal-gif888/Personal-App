import { useQuery, useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { approvalService } from '../services/approvalService';
import { errorMessage } from '../services/api';
import { toast } from '../stores/notificationStore';

/** An approved action can land in any module, so refresh everything it might have changed. */
export function invalidateAfterApproval(queryClient: QueryClient) {
  for (const key of [
    'approvals',
    'agentRuns',
    'tasks',
    'reminders',
    'events',
    'studySessions',
    'expenses',
    'bills',
    'budgets',
  ]) {
    queryClient.invalidateQueries({ queryKey: [key] });
  }
}

export function useApprovals() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['approvals'],
    queryFn: () => approvalService.getApprovals(),
  });

  const respondMutation = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: 'approved' | 'rejected' }) =>
      approvalService.respondToApproval(id, decision),
    onSuccess: (action, variables) => {
      invalidateAfterApproval(queryClient);
      queryClient.invalidateQueries({ queryKey: ['chatMessages'] });
      toast.success(
        variables.decision === 'approved' ? 'Action Approved' : 'Action Rejected',
        `"${action.title}" was ${variables.decision}.`
      );
    },
    onError: (err) => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      toast.error('Failed to respond to approval request', errorMessage(err));
    },
  });

  return {
    approvals: query.data || [],
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
    respondToApproval: respondMutation.mutateAsync,
    isResponding: respondMutation.isPending,
  };
}
