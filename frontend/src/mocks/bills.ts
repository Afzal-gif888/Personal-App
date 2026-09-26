import type { Bill } from '../types';

export const INITIAL_BILLS: Bill[] = [
  {
    id: 'bill-1',
    title: 'Electricity Bill',
    amount: 1200,
    dueDate: '2026-09-29',
    category: 'utilities',
    status: 'upcoming',
    isRecurring: true,
    frequency: 'monthly',
    paymentMethod: 'Credit Card',
  },
  {
    id: 'bill-2',
    title: 'Internet Bill',
    amount: 800,
    dueDate: '2026-10-01',
    category: 'utilities',
    status: 'upcoming',
    isRecurring: true,
    frequency: 'monthly',
  },
  {
    id: 'bill-3',
    title: 'Netflix Subscription',
    amount: 499,
    dueDate: '2026-09-15',
    category: 'entertainment',
    status: 'paid',
    isRecurring: true,
    frequency: 'monthly',
  }
];
