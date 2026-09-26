import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reminderService } from '../services/reminderService';
import type { Reminder } from '../types';
import { toast } from '../stores/notificationStore';

export function useReminders() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['reminders'],
    queryFn: () => reminderService.getReminders(),
  });

  const createMutation = useMutation({
    mutationFn: (data: Omit<Reminder, 'id' | 'createdAt'>) => reminderService.createReminder(data),
    onSuccess: (newRem) => {
      queryClient.invalidateQueries({ queryKey: ['reminders'] });
      toast.success('Reminder Scheduled', `"${newRem.title}" set for ${newRem.date} at ${newRem.time}.`);
    },
    onError: () => toast.error('Failed to create reminder'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Partial<Reminder> }) => reminderService.updateReminder(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reminders'] });
      toast.success('Reminder Updated');
    },
  });

  const toggleCompleteMutation = useMutation({
    mutationFn: (id: string) => reminderService.toggleReminderComplete(id),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['reminders'] });
      if (updated.status === 'completed') {
        toast.success('Reminder Completed');
      }
    },
  });

  const snoozeMutation = useMutation({
    mutationFn: ({ id, minutes }: { id: string; minutes?: number }) => reminderService.snoozeReminder(id, minutes),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['reminders'] });
      toast.info('Reminder Snoozed', `Snoozed until ${updated.time}.`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => reminderService.deleteReminder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reminders'] });
      toast.info('Reminder Removed');
    },
  });

  return {
    reminders: query.data || [],
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
    createReminder: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    updateReminder: updateMutation.mutateAsync,
    toggleComplete: toggleCompleteMutation.mutateAsync,
    snoozeReminder: snoozeMutation.mutateAsync,
    deleteReminder: deleteMutation.mutateAsync,
  };
}
