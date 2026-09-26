import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { approvalService } from '../services/approvalService';
import { toast } from '../stores/notificationStore';

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
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['reminders'] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success(
        variables.decision === 'approved' ? 'Action Approved' : 'Action Rejected',
        `"${action.title}" was ${variables.decision}.`
      );
    },
    onError: () => toast.error('Failed to respond to approval request'),
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
