import type { PaymentPlan } from '../types';
import { api } from './api';
import { todayISO } from '../utils/formatters';

interface PaymentPlanOut {
  id: string;
  title: string;
  totalAmount: number;
  installmentAmount: number;
  frequency: string;
  nextPaymentDate: string | null;
  remainingAmount: number;
  totalInstallments: number;
  completedInstallments: number;
  status: 'active' | 'paused' | 'completed' | 'cancelled';
}

const toPlan = (p: PaymentPlanOut): PaymentPlan => ({
  id: p.id,
  title: p.title,
  totalAmount: p.totalAmount,
  installmentAmount: p.installmentAmount,
  frequency: p.frequency,
  nextPaymentDate: p.nextPaymentDate ?? '',
  remainingAmount: p.remainingAmount,
  totalInstallments: p.totalInstallments,
  completedInstallments: p.completedInstallments,
  status: p.status === 'completed' || p.status === 'cancelled' ? 'completed' : 'active',
});

export const paymentPlanService = {
  async getPlans(): Promise<PaymentPlan[]> {
    return (await api.get<PaymentPlanOut[]>('/payment-plans')).map(toPlan);
  },

  async createPlan(data: Omit<PaymentPlan, 'id'>): Promise<PaymentPlan> {
    const start = data.nextPaymentDate || todayISO();
    const res = await api.post<PaymentPlanOut>('/payment-plans', {
      title: data.title,
      totalAmount: data.totalAmount,
      installmentAmount: data.installmentAmount,
      frequency: data.frequency,
      startDate: start,
      nextPaymentDate: start,
      totalInstallments: data.totalInstallments,
      completedInstallments: data.completedInstallments,
    });
    return toPlan(res);
  },

  async recordPayment(id: string): Promise<PaymentPlan> {
    return toPlan(await api.post<PaymentPlanOut>(`/payment-plans/${id}/payments`));
  },

  async deletePlan(id: string): Promise<void> {
    await api.delete(`/payment-plans/${id}`);
  },
};
