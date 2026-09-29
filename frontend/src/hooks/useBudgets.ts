import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { budgetService, type BudgetInput } from '../services/budgetService';
import { errorMessage } from '../services/api';
import { toast } from '../stores/notificationStore';

const QUERY_KEY = ['budgets'];

/** Budgets with spending progress for `month` (YYYY-MM); defaults to the current month. */
export function useBudgets(month?: string) {
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: [...QUERY_KEY, month ?? 'current'],
    queryFn: () => budgetService.getBudgets(month),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: QUERY_KEY });

  const create = useMutation({
    mutationFn: (data: BudgetInput) => budgetService.createBudget(data),
    onSuccess: () => {
      invalidate();
      toast.success('Budget created');
    },
    onError: (err) => toast.error('Could not create budget', errorMessage(err)),
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Pick<BudgetInput, 'amount' | 'alertThreshold'> }) =>
      budgetService.updateBudget(id, data),
    onSuccess: () => {
      invalidate();
      toast.success('Budget updated');
    },
    onError: (err) => toast.error('Could not update budget', errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: string) => budgetService.deleteBudget(id),
    onSuccess: () => {
      invalidate();
      toast.info('Budget removed');
    },
    onError: (err) => toast.error('Could not remove budget', errorMessage(err)),
  });

  return { ...query, create, update, remove };
}
