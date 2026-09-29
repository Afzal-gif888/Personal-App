import type { Task, TaskStatus } from '../types';
import { api } from './api';

interface TaskOut {
  id: string;
  title: string;
  description: string | null;
  category: Task['category'];
  priority: Task['priority'];
  status: TaskStatus | 'cancelled';
  dueDate: string | null;
  dueTime: string | null;
  subject: string | null;
  createdAt: string;
  updatedAt: string;
}

const toTask = (t: TaskOut): Task => ({
  id: t.id,
  title: t.title,
  description: t.description ?? undefined,
  subject: t.subject ?? undefined,
  category: t.category,
  priority: t.priority,
  dueDate: t.dueDate ?? '',
  dueTime: t.dueTime ?? undefined,
  status: t.status === 'cancelled' ? 'completed' : t.status,
  createdAt: t.createdAt,
  updatedAt: t.updatedAt,
});

function toBody(data: Partial<Task>) {
  const body: Record<string, unknown> = {};
  if (data.title !== undefined) body.title = data.title;
  if (data.description !== undefined) body.description = data.description || null;
  if (data.subject !== undefined) body.subject = data.subject || null;
  if (data.category !== undefined) body.category = data.category;
  if (data.priority !== undefined) body.priority = data.priority;
  if (data.status !== undefined) body.status = data.status;
  if (data.dueDate !== undefined) body.dueDate = data.dueDate || null;
  if (data.dueTime !== undefined) body.dueTime = data.dueTime || null;
  return body;
}

export const taskService = {
  async getTasks(): Promise<Task[]> {
    return (await api.getAll<TaskOut>('/tasks')).map(toTask);
  },

  async getTaskById(id: string): Promise<Task | undefined> {
    return toTask(await api.get<TaskOut>(`/tasks/${id}`));
  },

  async createTask(data: Omit<Task, 'id' | 'createdAt' | 'updatedAt'>): Promise<Task> {
    return toTask(await api.post<TaskOut>('/tasks', toBody(data)));
  },

  async updateTask(id: string, updates: Partial<Task>): Promise<Task> {
    return toTask(await api.patch<TaskOut>(`/tasks/${id}`, toBody(updates)));
  },

  async toggleTaskComplete(id: string): Promise<Task> {
    const current = await api.get<TaskOut>(`/tasks/${id}`);
    return taskService.updateTask(id, { status: current.status === 'completed' ? 'pending' : 'completed' });
  },

  async deleteTask(id: string): Promise<void> {
    await api.delete(`/tasks/${id}`);
  },
};
