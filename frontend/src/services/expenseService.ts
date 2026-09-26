import type { Expense } from '../types';
import { storage } from './storage';

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

export const expenseService = {
  async getExpenses(): Promise<Expense[]> {
    await delay(150);
    return storage.getExpenses();
  },

  async createExpense(data: Omit<Expense, 'id'>): Promise<Expense> {
    await delay(200);
    const expenses = storage.getExpenses();
    const newExpense: Expense = { ...data, id: `exp-${Date.now()}` };
    storage.setExpenses([...expenses, newExpense]);
    return newExpense;
  },

  async deleteExpense(id: string): Promise<void> {
    await delay(150);
    storage.setExpenses(storage.getExpenses().filter((e) => e.id !== id));
  },
};
