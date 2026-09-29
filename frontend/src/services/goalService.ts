import type { Goal, GoalCategory, GoalStatus } from '../types';
import { api } from './api';

interface GoalOut {
  id: string;
  title: string;
  description: string | null;
  category: GoalCategory;
  targetValue: number | null;
  currentValue: number | null;
  unit: string | null;
  progress: number;
  deadline: string | null;
  status: GoalStatus;
}

// Goals with a numeric target (e.g. 10 applications) show that target; others keep the
// free-text target the form collects, stored as the goal's description.
function targetText(g: GoalOut): string {
  if (g.targetValue != null) {
    return `${g.targetValue.toLocaleString('en-IN')}${g.unit ? ` ${g.unit}` : ''}`;
  }
  return g.description ?? '';
}

const toGoal = (g: GoalOut): Goal => ({
  id: g.id,
  title: g.title,
  category: g.category,
  target: targetText(g),
  progress: g.progress,
  deadline: g.deadline ?? undefined,
  status: g.status,
});

function toBody(data: Partial<Goal>, existing?: GoalOut) {
  const body: Record<string, unknown> = {};
  if (data.title !== undefined) body.title = data.title;
  if (data.category !== undefined) body.category = data.category;
  if (data.status !== undefined) body.status = data.status;
  if (data.deadline !== undefined) body.deadline = data.deadline || null;
  const numeric = existing?.targetValue != null;
  if (data.target !== undefined && !numeric) body.description = data.target || null;
  if (data.progress !== undefined) {
    if (numeric && existing?.targetValue) {
      // Progress is derived from current/target for these goals, so move the current value.
      body.currentValue = Math.round(existing.targetValue * data.progress) / 100;
    } else {
      body.manualProgress = data.progress;
    }
  }
  return body;
}

export const goalService = {
  async getGoals(): Promise<Goal[]> {
    return (await api.get<GoalOut[]>('/goals')).map(toGoal);
  },

  async createGoal(data: Omit<Goal, 'id'>): Promise<Goal> {
    return toGoal(await api.post<GoalOut>('/goals', toBody(data)));
  },

  async updateGoal(id: string, data: Partial<Goal>): Promise<Goal> {
    const existing = (await api.get<GoalOut[]>('/goals')).find((g) => g.id === id);
    return toGoal(await api.patch<GoalOut>(`/goals/${id}`, toBody(data, existing)));
  },

  async deleteGoal(id: string): Promise<void> {
    await api.delete(`/goals/${id}`);
  },
};
