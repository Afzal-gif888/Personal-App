import type { Reminder, ReminderStatus } from '../types';
import { storage } from './storage';

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

export const reminderService = {
  async getReminders(): Promise<Reminder[]> {
    await delay(150);
    return storage.getReminders();
  },

  async createReminder(reminderData: Omit<Reminder, 'id' | 'createdAt'>): Promise<Reminder> {
    await delay(200);
    const reminders = storage.getReminders();
    const newReminder: Reminder = {
      ...reminderData,
      id: `rem-${Date.now()}`,
      createdAt: new Date().toISOString(),
    };
    const updated = [newReminder, ...reminders];
    storage.setReminders(updated);
    return newReminder;
  },

  async updateReminder(id: string, updates: Partial<Reminder>): Promise<Reminder> {
    await delay(150);
    const reminders = storage.getReminders();
    let updatedReminder: Reminder | null = null;
    const updated = reminders.map((r) => {
      if (r.id === id) {
        updatedReminder = { ...r, ...updates };
        return updatedReminder;
      }
      return r;
    });
    if (!updatedReminder) throw new Error(`Reminder with id ${id} not found.`);
    storage.setReminders(updated);
    return updatedReminder;
  },

  async toggleReminderComplete(id: string): Promise<Reminder> {
    const reminders = storage.getReminders();
    const target = reminders.find((r) => r.id === id);
    if (!target) throw new Error(`Reminder with id ${id} not found.`);
    const newStatus: ReminderStatus = target.status === 'completed' ? 'upcoming' : 'completed';
    return this.updateReminder(id, { status: newStatus });
  },

  async snoozeReminder(id: string, minutes: number = 30): Promise<Reminder> {
    await delay(150);
    const reminders = storage.getReminders();
    const target = reminders.find((r) => r.id === id);
    if (!target) throw new Error(`Reminder with id ${id} not found.`);

    // Increment time by snooze duration
    const [h, m] = target.time.split(':').map(Number);
    const dateObj = new Date();
    dateObj.setHours(h, m + minutes);
    const newTimeStr = `${String(dateObj.getHours()).padStart(2, '0')}:${String(dateObj.getMinutes()).padStart(2, '0')}`;

    return this.updateReminder(id, { status: 'snoozed', time: newTimeStr });
  },

  async deleteReminder(id: string): Promise<void> {
    await delay(150);
    const reminders = storage.getReminders();
    storage.setReminders(reminders.filter((r) => r.id !== id));
  },
};
