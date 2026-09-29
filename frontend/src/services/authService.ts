import type { UserProfile } from '../types';
import { api, tokenStore } from './api';

interface UserOut {
  id: string;
  name: string;
  email: string;
  avatarUrl: string | null;
  university: string | null;
  major: string | null;
  academicYear: string | null;
  bio: string | null;
}

interface TokenOut {
  accessToken: string;
  refreshToken: string;
  user: UserOut;
}

export function toUser(u: UserOut): UserProfile {
  return {
    id: u.id,
    name: u.name,
    email: u.email,
    avatarUrl: u.avatarUrl ?? undefined,
    university: u.university ?? '',
    major: u.major ?? '',
    academicYear: u.academicYear ?? '',
    bio: u.bio ?? undefined,
  };
}

function browserTimezone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return undefined;
  }
}

async function startSession(res: TokenOut): Promise<UserProfile> {
  tokenStore.set(res);
  return toUser(res.user);
}

export const authService = {
  /** Step 1 of sign-in: checks the password; the server emails a 6-digit code. No session yet. */
  async login(email: string, password: string): Promise<{ email: string; message: string }> {
    const res = await api.post<{ requiresOtp: boolean; message: string; email: string }>(
      '/auth/login',
      { email, password },
      { anonymous: true }
    );
    return { email: res.email, message: res.message };
  },

  /** Step 2: the emailed code. The server issues the session only if it is correct. */
  async verifyOtp(email: string, otp: string): Promise<UserProfile> {
    return startSession(await api.post<TokenOut>('/auth/verify-otp', { email, otp }, { anonymous: true }));
  },

  async resendOtp(email: string): Promise<string> {
    return (await api.post<{ message: string }>('/auth/resend-otp', { email }, { anonymous: true })).message;
  },

  /** Creates the account. No session: the user signs in (password + emailed code) next. */
  async register(name: string, email: string, password: string): Promise<{ email: string; message: string }> {
    const body = { name, email, password, timezone: browserTimezone() };
    const res = await api.post<{ user: UserOut; message: string }>('/auth/register', body, { anonymous: true });
    return { email: res.user.email, message: res.message };
  },

  async forgotPassword(email: string): Promise<{ success: boolean; message: string }> {
    const res = await api.post<{ message: string }>('/auth/forgot-password', { email }, { anonymous: true });
    return { success: true, message: res.message };
  },

  async resetPassword(token: string, newPassword: string): Promise<void> {
    await api.post('/auth/reset-password', { token, newPassword }, { anonymous: true });
  },

  async getCurrentUser(): Promise<UserProfile | null> {
    if (!tokenStore.access && !tokenStore.refresh) return null;
    return toUser(await api.get<UserOut>('/users/me'));
  },

  async updateUserProfile(updates: Partial<UserProfile>): Promise<UserProfile> {
    // Email can't be changed through the profile endpoint.
    const { name, avatarUrl, university, major, academicYear, bio } = updates;
    return toUser(await api.patch<UserOut>('/users/me', { name, avatarUrl, university, major, academicYear, bio }));
  },

  async logout(): Promise<void> {
    const refreshToken = tokenStore.refresh;
    tokenStore.clear();
    if (refreshToken) {
      try {
        await api.post('/auth/logout', { refreshToken }, { anonymous: true });
      } catch {
        // already signed out locally; the token expires on its own
      }
    }
  },
};
