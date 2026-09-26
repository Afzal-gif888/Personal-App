import type { Goal } from '../types';
import { storage } from './storage';

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

export const goalService = {
  async getGoals(): Promise<Goal[]> {
    await delay(150);
    return storage.getGoals();
  },

  async createGoal(data: Omit<Goal, 'id'>): Promise<Goal> {
    await delay(200);
    const goals = storage.getGoals();
    const newGoal: Goal = { ...data, id: `goal-${Date.now()}` };
    storage.setGoals([...goals, newGoal]);
    return newGoal;
  },

  async updateGoal(id: string, data: Partial<Goal>): Promise<Goal> {
    await delay(200);
    const goals = storage.getGoals();
    const updated = goals.map((g) => (g.id === id ? { ...g, ...data } : g));
    storage.setGoals(updated);
    const found = updated.find((g) => g.id === id);
    if (!found) throw new Error('Goal not found');
    return found;
  },

  async deleteGoal(id: string): Promise<void> {
    await delay(150);
    storage.setGoals(storage.getGoals().filter((g) => g.id !== id));
  },
};
