import type { PaymentPlan } from '../types';
import { storage } from './storage';

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

export const paymentPlanService = {
  async getPlans(): Promise<PaymentPlan[]> {
    await delay(150);
    return storage.getPaymentPlans();
  },

  async createPlan(data: Omit<PaymentPlan, 'id'>): Promise<PaymentPlan> {
    await delay(200);
    const plans = storage.getPaymentPlans();
    const newPlan: PaymentPlan = { ...data, id: `plan-${Date.now()}` };
    storage.setPaymentPlans([...plans, newPlan]);
    return newPlan;
  },

  async recordPayment(id: string): Promise<PaymentPlan> {
    await delay(200);
    const plans = storage.getPaymentPlans();
    const plan = plans.find((p) => p.id === id);
    if (!plan) throw new Error('Plan not found');
    const completed = plan.completedInstallments + 1;
    const remaining = plan.remainingAmount - plan.installmentAmount;
    const status: 'active' | 'completed' = completed >= plan.totalInstallments ? 'completed' : 'active';
    const updated: PaymentPlan = {
      ...plan,
      completedInstallments: completed,
      remainingAmount: Math.max(0, remaining),
      status,
    };
    storage.setPaymentPlans(plans.map((p) => (p.id === id ? updated : p)));
    return updated;
  },

  async deletePlan(id: string): Promise<void> {
    await delay(150);
    storage.setPaymentPlans(storage.getPaymentPlans().filter((p) => p.id !== id));
  },
};
