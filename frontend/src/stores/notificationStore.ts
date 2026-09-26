import { create } from 'zustand';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  description?: string;
  duration?: number;
}

interface NotificationState {
  toasts: ToastItem[];
  addToast: (type: ToastType, message: string, description?: string, duration?: number) => void;
  removeToast: (id: string) => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  toasts: [],
  addToast: (type, message, description, duration = 4000) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    const newToast: ToastItem = { id, type, message, description, duration };

    set((state) => ({ toasts: [...state.toasts, newToast] }));

    if (duration > 0) {
      setTimeout(() => {
        set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
      }, duration);
    }
  },
  removeToast: (id) => {
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
  },
}));

export const toast = {
  success: (message: string, description?: string) =>
    useNotificationStore.getState().addToast('success', message, description),
  error: (message: string, description?: string) =>
    useNotificationStore.getState().addToast('error', message, description),
  info: (message: string, description?: string) =>
    useNotificationStore.getState().addToast('info', message, description),
  warning: (message: string, description?: string) =>
    useNotificationStore.getState().addToast('warning', message, description),
};
