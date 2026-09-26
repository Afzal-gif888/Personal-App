import { create } from 'zustand';
import type { UserProfile } from '../types';
import { storage } from '../services/storage';
import { authService } from '../services/authService';

interface AuthState {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password?: string) => Promise<void>;
  register: (name: string, email: string) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (updates: Partial<UserProfile>) => Promise<void>;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: storage.getUser(),
  token: storage.getToken(),
  isAuthenticated: !!storage.getToken(),
  isLoading: false,

  initialize: async () => {
    set({ isLoading: true });
    try {
      const token = storage.getToken();
      if (token) {
        const user = storage.getUser();
        set({ user, token, isAuthenticated: true });
      } else {
        set({ user: null, token: null, isAuthenticated: false });
      }
    } finally {
      set({ isLoading: false });
    }
  },

  login: async (email: string, password?: string) => {
    set({ isLoading: true });
    try {
      const { token, user } = await authService.login(email, password);
      set({ user, token, isAuthenticated: true });
    } finally {
      set({ isLoading: false });
    }
  },

  register: async (name: string, email: string) => {
    set({ isLoading: true });
    try {
      const { token, user } = await authService.register(name, email);
      set({ user, token, isAuthenticated: true });
    } finally {
      set({ isLoading: false });
    }
  },

  updateUser: async (updates: Partial<UserProfile>) => {
    const updated = await authService.updateUserProfile(updates);
    set({ user: updated });
  },

  logout: async () => {
    await authService.logout();
    set({ user: null, token: null, isAuthenticated: false });
  },
}));
