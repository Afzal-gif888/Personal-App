import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Expense } from '../types';
import { expenseService } from '../services/expenseService';

const QUERY_KEY = ['expenses'];

export function useExpenses() {
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: expenseService.getExpenses,
  });

  const create = useMutation({
    mutationFn: (data: Omit<Expense, 'id'>) => expenseService.createExpense(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => expenseService.deleteExpense(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  return { ...query, create, remove };
}
