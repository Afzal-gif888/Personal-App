import type { Reminder, ReminderRepeat, ReminderStatus } from '../types';
import { api } from './api';
import { todayISO } from '../utils/formatters';

interface ReminderOut {
  id: string;
  title: string;
  description: string | null;
  category: NonNullable<Reminder['category']>;
  date: string;
  time: string;
  repeatRule: ReminderRepeat;
  status: 'pending' | 'completed' | 'snoozed' | 'cancelled';
  createdAt: string;
}

function toStatus(r: ReminderOut): ReminderStatus {
  if (r.status === 'completed' || r.status === 'cancelled') return 'completed';
  if (r.status === 'snoozed') return 'snoozed';
  return r.date === todayISO() ? 'today' : 'upcoming';
}

const toReminder = (r: ReminderOut): Reminder => ({
  id: r.id,
  title: r.title,
  description: r.description ?? undefined,
  date: r.date,
  time: r.time,
  repeat: r.repeatRule,
  status: toStatus(r),
  category: r.category,
  createdAt: r.createdAt,
});

function toBody(data: Partial<Reminder>) {
  const body: Record<string, unknown> = {};
  if (data.title !== undefined) body.title = data.title;
  if (data.description !== undefined) body.description = data.description || null;
  if (data.category !== undefined) body.category = data.category;
  if (data.repeat !== undefined) body.repeatRule = data.repeat;
  // The API needs date and time together to place a reminder in the user's timezone.
  if (data.date !== undefined && data.time !== undefined) {
    body.date = data.date;
    body.time = data.time;
  }
  if (data.status !== undefined) {
    body.status = data.status === 'completed' ? 'completed' : data.status === 'snoozed' ? 'snoozed' : 'pending';
  }
  return body;
}

export const reminderService = {
  async getReminders(): Promise<Reminder[]> {
    return (await api.get<ReminderOut[]>('/reminders')).map(toReminder);
  },

  async createReminder(data: Omit<Reminder, 'id' | 'createdAt'>): Promise<Reminder> {
    const { status: _status, ...rest } = data;
    return toReminder(await api.post<ReminderOut>('/reminders', toBody(rest)));
  },

  async updateReminder(id: string, updates: Partial<Reminder>): Promise<Reminder> {
    return toReminder(await api.patch<ReminderOut>(`/reminders/${id}`, toBody(updates)));
  },

  async toggleReminderComplete(id: string): Promise<Reminder> {
    const all = await api.get<ReminderOut[]>('/reminders');
    const current = all.find((r) => r.id === id);
    if (current?.status === 'completed') {
      return reminderService.updateReminder(id, { status: 'upcoming' });
    }
    return toReminder(await api.post<ReminderOut>(`/reminders/${id}/complete`));
  },

  async snoozeReminder(id: string, minutes: number = 30): Promise<Reminder> {
    return toReminder(await api.post<ReminderOut>(`/reminders/${id}/snooze`, { minutes }));
  },

  async deleteReminder(id: string): Promise<void> {
    await api.delete(`/reminders/${id}`);
  },
};
