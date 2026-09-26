import type { PaymentPlan } from '../types';

export const INITIAL_PAYMENT_PLANS: PaymentPlan[] = [
  {
    id: 'plan-1',
    title: 'Hostel Fees',
    totalAmount: 60000,
    installmentAmount: 10000,
    frequency: 'monthly',
    nextPaymentDate: '2026-10-05',
    remainingAmount: 40000,
    totalInstallments: 6,
    completedInstallments: 2,
    status: 'active',
  },
  {
    id: 'plan-2',
    title: 'Laptop EMI',
    totalAmount: 80000,
    installmentAmount: 6666,
    frequency: 'monthly',
    nextPaymentDate: '2026-10-10',
    remainingAmount: 53336,
    totalInstallments: 12,
    completedInstallments: 4,
    status: 'active',
  }
];
