import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { CalendarEvent } from '../types';
import { eventService } from '../services/eventService';

const QUERY_KEY = ['events'];

export function useEvents() {
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: eventService.getEvents,
  });

  const create = useMutation({
    mutationFn: (data: Omit<CalendarEvent, 'id' | 'createdAt'>) => eventService.createEvent(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CalendarEvent> }) =>
      eventService.updateEvent(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => eventService.deleteEvent(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  return { ...query, create, update, remove };
}
