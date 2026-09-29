import type { Expense, ExpenseCategory } from '../types';
import { api } from './api';

interface ExpenseOut {
  id: string;
  title: string;
  description: string | null;
  category: ExpenseCategory;
  amount: number;
  expenseDate: string;
}

// The API uses lowercase categories ("food"); the Expenses page shows and filters by "Food".
const toLabel = (c: string) => c.charAt(0).toUpperCase() + c.slice(1);
const toCategory = (label: string) => label.toLowerCase() as ExpenseCategory;

const toExpense = (e: ExpenseOut): Expense => ({
  id: e.id,
  title: e.title,
  amount: e.amount,
  category: toLabel(e.category),
  date: e.expenseDate,
  description: e.description ?? undefined,
});

export const expenseService = {
  async getExpenses(): Promise<Expense[]> {
    return (await api.getAll<ExpenseOut>('/expenses')).map(toExpense);
  },

  async createExpense(data: Omit<Expense, 'id'>): Promise<Expense> {
    const res = await api.post<ExpenseOut>('/expenses', {
      title: data.title,
      amount: data.amount,
      category: toCategory(data.category),
      expenseDate: data.date,
      description: data.description || null,
    });
    return toExpense(res);
  },

  async deleteExpense(id: string): Promise<void> {
    await api.delete(`/expenses/${id}`);
  },
};
