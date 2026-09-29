import type { CalendarEvent, EventType } from '../types';
import { api } from './api';

interface EventOut {
  id: string;
  title: string;
  description: string | null;
  eventType: string;
  date: string;
  startTime: string;
  endTime: string | null;
  location: string | null;
  createdAt: string;
}

const KNOWN_TYPES: EventType[] = ['class', 'meeting', 'appointment', 'exam', 'deadline', 'personal', 'other'];

function toType(value: string): EventType {
  if ((KNOWN_TYPES as string[]).includes(value)) return value as EventType;
  return value.endsWith('meeting') || value === 'interview' ? 'meeting' : 'other';
}

const toEvent = (e: EventOut): CalendarEvent => ({
  id: e.id,
  title: e.title,
  description: e.description ?? undefined,
  date: e.date,
  startTime: e.startTime,
  endTime: e.endTime ?? undefined,
  type: toType(e.eventType),
  location: e.location ?? undefined,
  createdAt: e.createdAt,
});

function toBody(data: Partial<CalendarEvent>) {
  const body: Record<string, unknown> = {};
  if (data.title !== undefined) body.title = data.title;
  if (data.description !== undefined) body.description = data.description || null;
  if (data.type !== undefined) body.eventType = data.type;
  if (data.location !== undefined) body.location = data.location || null;
  if (data.date !== undefined) body.date = data.date;
  if (data.startTime !== undefined) body.startTime = data.startTime;
  if (data.endTime !== undefined) body.endTime = data.endTime || null;
  return body;
}

export const eventService = {
  async getEvents(): Promise<CalendarEvent[]> {
    return (await api.get<EventOut[]>('/events')).map(toEvent);
  },

  async createEvent(data: Omit<CalendarEvent, 'id' | 'createdAt'>): Promise<CalendarEvent> {
    return toEvent(await api.post<EventOut>('/events', toBody(data)));
  },

  async updateEvent(id: string, data: Partial<CalendarEvent>): Promise<CalendarEvent> {
    return toEvent(await api.patch<EventOut>(`/events/${id}`, toBody(data)));
  },

  async deleteEvent(id: string): Promise<void> {
    await api.delete(`/events/${id}`);
  },
};
