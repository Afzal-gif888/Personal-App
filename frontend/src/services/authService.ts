import type { UserProfile } from '../types';
import { storage } from './storage';

const delay = (ms = 200) => new Promise((resolve) => setTimeout(resolve, ms));

export const authService = {
  async login(email: string, _password?: string): Promise<{ token: string; user: UserProfile }> {
    await delay(300);
    // Standard mock authentication
    const user = storage.getUser();
    if (email && email.trim() !== '') {
      user.email = email;
    }
    const token = 'mock-jwt-token-agentos-alex-101';
    storage.setToken(token);
    storage.setUser(user);
    return { token, user };
  },

  async register(name: string, email: string): Promise<{ token: string; user: UserProfile }> {
    await delay(350);
    const user: UserProfile = {
      ...storage.getUser(),
      name,
      email,
    };
    const token = `mock-jwt-token-${Date.now()}`;
    storage.setToken(token);
    storage.setUser(user);
    return { token, user };
  },

  async forgotPassword(email: string): Promise<{ success: boolean; message: string }> {
    await delay(300);
    return {
      success: true,
      message: `Password reset instructions sent to ${email}`,
    };
  },

  async getCurrentUser(): Promise<UserProfile | null> {
    await delay(100);
    const token = storage.getToken();
    if (!token) return null;
    return storage.getUser();
  },

  async updateUserProfile(updates: Partial<UserProfile>): Promise<UserProfile> {
    await delay(250);
    const current = storage.getUser();
    const updated = { ...current, ...updates };
    storage.setUser(updated);
    return updated;
  },

  async logout(): Promise<void> {
    await delay(100);
    storage.setToken(null);
  },
};
