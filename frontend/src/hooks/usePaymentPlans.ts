import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { PaymentPlan } from '../types';
import { paymentPlanService } from '../services/paymentPlanService';

const QUERY_KEY = ['payment-plans'];

export function usePaymentPlans() {
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: paymentPlanService.getPlans,
  });

  const create = useMutation({
    mutationFn: (data: Omit<PaymentPlan, 'id'>) => paymentPlanService.createPlan(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  const recordPayment = useMutation({
    mutationFn: (id: string) => paymentPlanService.recordPayment(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => paymentPlanService.deletePlan(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  return { ...query, create, recordPayment, remove };
}
