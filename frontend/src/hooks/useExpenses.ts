import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Expense } from '../types';
import { expenseService } from '../services/expenseService';
import { errorMessage } from '../services/api';
import { toast } from '../stores/notificationStore';

const QUERY_KEY = ['expenses'];

export function useExpenses() {
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: expenseService.getExpenses,
  });

  // Budget progress is computed from expenses, so it changes with them.
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: QUERY_KEY });
    qc.invalidateQueries({ queryKey: ['budgets'] });
  };

  const create = useMutation({
    mutationFn: (data: Omit<Expense, 'id'>) => expenseService.createExpense(data),
    onSuccess: invalidate,
    onError: (err) => toast.error('Could not save expense', errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: string) => expenseService.deleteExpense(id),
    onSuccess: invalidate,
    onError: (err) => toast.error('Could not delete expense', errorMessage(err)),
  });

  return { ...query, create, remove };
}
