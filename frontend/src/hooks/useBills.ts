import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Bill } from '../types';
import { billService } from '../services/billService';

const QUERY_KEY = ['bills'];

export function useBills() {
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: billService.getBills,
  });

  const create = useMutation({
    mutationFn: (data: Omit<Bill, 'id'>) => billService.createBill(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Bill> }) =>
      billService.updateBill(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  const markPaid = useMutation({
    mutationFn: (id: string) => billService.markAsPaid(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => billService.deleteBill(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  return { ...query, create, update, markPaid, remove };
}
