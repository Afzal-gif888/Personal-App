import { api } from './api';

export interface AppNotification {
  id: string;
  type: string;
  title: string;
  message: string;
  status: string;
  readAt: string | null;
  createdAt: string;
}

interface Page<T> {
  items: T[];
  total: number;
}

export const notificationService = {
  async getRecent(limit = 8): Promise<AppNotification[]> {
    return (await api.get<Page<AppNotification>>(`/notifications?page_size=${limit}`)).items;
  },
  async getUnreadCount(): Promise<number> {
    return (await api.get<{ unread: number }>('/notifications/unread-count')).unread;
  },
  async markRead(id: string): Promise<void> {
    await api.post(`/notifications/${id}/read`);
  },
  async markAllRead(): Promise<void> {
    await api.post('/notifications/read-all');
  },
};
