import type { CalendarEvent } from '../types';

export const INITIAL_EVENTS: CalendarEvent[] = [
  {
    id: 'event-1',
    title: 'Machine Learning Lecture',
    date: '2026-09-27',
    startTime: '10:00',
    endTime: '11:30',
    type: 'class',
    location: 'Room 304',
    createdAt: '2026-09-20T10:00:00Z',
  },
  {
    id: 'event-2',
    title: 'DBMS Project Meeting',
    date: '2026-09-28',
    startTime: '15:00',
    endTime: '16:00',
    type: 'meeting',
    location: 'Library Group Study Room B',
    createdAt: '2026-09-25T14:00:00Z',
  },
  {
    id: 'event-3',
    title: 'Dentist Appointment',
    date: '2026-09-30',
    startTime: '09:00',
    endTime: '10:00',
    type: 'appointment',
    location: 'City Dental Clinic',
    createdAt: '2026-09-15T09:00:00Z',
  }
];
