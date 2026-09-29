import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { notificationService } from '../services/notificationService';

const KEY = ['notifications'];
// Reminders are delivered by the backend scheduler; poll so they show up without a reload.
const REFRESH_MS = 60_000;

export function useNotifications() {
  const qc = useQueryClient();
  const recent = useQuery({ queryKey: [...KEY, 'recent'], queryFn: () => notificationService.getRecent(), refetchInterval: REFRESH_MS });
  const unread = useQuery({ queryKey: [...KEY, 'unread'], queryFn: notificationService.getUnreadCount, refetchInterval: REFRESH_MS });
  const invalidate = () => qc.invalidateQueries({ queryKey: KEY });

  const markRead = useMutation({ mutationFn: notificationService.markRead, onSuccess: invalidate });
  const markAllRead = useMutation({ mutationFn: notificationService.markAllRead, onSuccess: invalidate });

  return {
    notifications: recent.data ?? [],
    unreadCount: unread.data ?? 0,
    markRead: markRead.mutate,
    markAllRead: markAllRead.mutate,
  };
}
