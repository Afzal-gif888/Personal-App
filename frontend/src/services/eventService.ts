import type { CalendarEvent } from '../types';
import { storage } from './storage';

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

export const eventService = {
  async getEvents(): Promise<CalendarEvent[]> {
    await delay(150);
    return storage.getEvents();
  },

  async createEvent(data: Omit<CalendarEvent, 'id' | 'createdAt'>): Promise<CalendarEvent> {
    await delay(200);
    const events = storage.getEvents();
    const newEvent: CalendarEvent = {
      ...data,
      id: `event-${Date.now()}`,
      createdAt: new Date().toISOString(),
    };
    storage.setEvents([...events, newEvent]);
    return newEvent;
  },

  async updateEvent(id: string, data: Partial<CalendarEvent>): Promise<CalendarEvent> {
    await delay(200);
    const events = storage.getEvents();
    const updated = events.map((e) => (e.id === id ? { ...e, ...data } : e));
    storage.setEvents(updated);
    const found = updated.find((e) => e.id === id);
    if (!found) throw new Error('Event not found');
    return found;
  },

  async deleteEvent(id: string): Promise<void> {
    await delay(150);
    const events = storage.getEvents();
    storage.setEvents(events.filter((e) => e.id !== id));
  },
};
