import { useQuery } from '@tanstack/react-query';
import { agentRunService } from '../services/agentRunService';

export function useAgentRuns() {
  const query = useQuery({
    queryKey: ['agentRuns'],
    queryFn: () => agentRunService.getAgentRuns(),
  });

  return {
    agentRuns: query.data || [],
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}

export function useAgentRunDetail(id: string) {
  const query = useQuery({
    queryKey: ['agentRun', id],
    queryFn: () => agentRunService.getAgentRunById(id),
    enabled: !!id,
  });

  return {
    run: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
