import type { Task, TaskStatus } from '../types';
import { storage } from './storage';

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

export const taskService = {
  async getTasks(): Promise<Task[]> {
    await delay(150);
    return storage.getTasks();
  },

  async getTaskById(id: string): Promise<Task | undefined> {
    await delay(100);
    const tasks = storage.getTasks();
    return tasks.find((t) => t.id === id);
  },

  async createTask(newTaskData: Omit<Task, 'id' | 'createdAt' | 'updatedAt'>): Promise<Task> {
    await delay(200);
    const tasks = storage.getTasks();
    const newTask: Task = {
      ...newTaskData,
      id: `task-${Date.now()}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    const updatedTasks = [newTask, ...tasks];
    storage.setTasks(updatedTasks);
    return newTask;
  },

  async updateTask(id: string, updates: Partial<Task>): Promise<Task> {
    await delay(200);
    const tasks = storage.getTasks();
    let updatedTask: Task | null = null;
    const updatedTasks = tasks.map((t) => {
      if (t.id === id) {
        updatedTask = { ...t, ...updates, updatedAt: new Date().toISOString() };
        return updatedTask;
      }
      return t;
    });
    if (!updatedTask) throw new Error(`Task with id ${id} not found.`);
    storage.setTasks(updatedTasks);
    return updatedTask;
  },

  async toggleTaskComplete(id: string): Promise<Task> {
    const tasks = storage.getTasks();
    const target = tasks.find((t) => t.id === id);
    if (!target) throw new Error(`Task with id ${id} not found.`);
    const newStatus: TaskStatus = target.status === 'completed' ? 'pending' : 'completed';
    return this.updateTask(id, { status: newStatus });
  },

  async deleteTask(id: string): Promise<void> {
    await delay(150);
    const tasks = storage.getTasks();
    const updatedTasks = tasks.filter((t) => t.id !== id);
    storage.setTasks(updatedTasks);
  },
};
