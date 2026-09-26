import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Goal } from '../types';
import { goalService } from '../services/goalService';

const QUERY_KEY = ['goals'];

export function useGoals() {
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: goalService.getGoals,
  });

  const create = useMutation({
    mutationFn: (data: Omit<Goal, 'id'>) => goalService.createGoal(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Goal> }) =>
      goalService.updateGoal(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => goalService.deleteGoal(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  return { ...query, create, update, remove };
}
