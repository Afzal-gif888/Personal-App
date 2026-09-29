import { create } from 'zustand';
import type { UserProfile } from '../types';
import { authService } from '../services/authService';
import { setUnauthorizedHandler, tokenStore } from '../services/api';

interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** Password step; resolves with the address the code was sent to. Doesn't sign in. */
  login: (email: string, password: string) => Promise<string>;
  /** Code step; signs in only if the server accepts the code. */
  verifyOtp: (email: string, otp: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<string>;
  logout: () => Promise<void>;
  updateUser: (updates: Partial<UserProfile>) => Promise<void>;
  initialize: () => Promise<void>;
}

const hasSession = () => Boolean(tokenStore.access || tokenStore.refresh);

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  // Optimistic until initialize() confirms the stored session with the server.
  isAuthenticated: hasSession(),
  isLoading: hasSession(),

  initialize: async () => {
    if (!hasSession()) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      return;
    }
    set({ isLoading: true });
    try {
      const user = await authService.getCurrentUser();
      set({ user, isAuthenticated: Boolean(user) });
    } catch {
      tokenStore.clear();
      set({ user: null, isAuthenticated: false });
    } finally {
      set({ isLoading: false });
    }
  },

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      return (await authService.login(email, password)).email;
    } finally {
      set({ isLoading: false });
    }
  },

  verifyOtp: async (email, otp) => {
    const user = await authService.verifyOtp(email, otp);
    set({ user, isAuthenticated: true });
  },

  register: async (name, email, password) => {
    set({ isLoading: true });
    try {
      return (await authService.register(name, email, password)).email;
    } finally {
      set({ isLoading: false });
    }
  },

  updateUser: async (updates) => {
    const updated = await authService.updateUserProfile(updates);
    set({ user: updated });
  },

  logout: async () => {
    await authService.logout();
    set({ user: null, isAuthenticated: false });
  },
}));

// An expired session that can't be refreshed signs the user out (AppLayout then redirects to /login).
setUnauthorizedHandler(() => useAuthStore.setState({ user: null, isAuthenticated: false }));
