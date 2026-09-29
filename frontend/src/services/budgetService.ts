import type { Budget, ExpenseCategory } from '../types';
import { api } from './api';

export interface BudgetInput {
  category: ExpenseCategory | null; // null = one overall budget for all spending
  amount: number;
  alertThreshold: number;
}

export const budgetService = {
  /** Every budget with its spending progress for `month` (YYYY-MM, default this month). */
  async getBudgets(month?: string): Promise<Budget[]> {
    return api.get<Budget[]>('/budgets', { month });
  },

  async createBudget(data: BudgetInput): Promise<Budget> {
    return api.post<Budget>('/budgets', data);
  },

  async updateBudget(id: string, data: Pick<BudgetInput, 'amount' | 'alertThreshold'>): Promise<Budget> {
    return api.patch<Budget>(`/budgets/${id}`, data);
  },

  async deleteBudget(id: string): Promise<void> {
    await api.delete(`/budgets/${id}`);
  },
};
