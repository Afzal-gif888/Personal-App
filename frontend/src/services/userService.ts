import type { NotificationSettings, PreferenceSettings } from '../types';
import { api } from './api';

interface PreferencesOut {
  dailyStudyGoalMinutes: number;
  preferredStudyStart: string | null;
  preferredStudyEnd: string | null;
  defaultReminderTime: string;
  timezone: string;
  currency: string;
  notificationPreferences: NotificationSettings;
}

function toPreferences(p: PreferencesOut): PreferenceSettings {
  return {
    dailyStudyGoalHours: Math.round((p.dailyStudyGoalMinutes / 60) * 10) / 10,
    preferredStudyHours: p.preferredStudyStart && p.preferredStudyEnd ? `${p.preferredStudyStart} – ${p.preferredStudyEnd}` : '',
    defaultReminderTime: p.defaultReminderTime,
    timezone: p.timezone,
  };
}

/** "18:00 – 22:00" (any dash) → ["18:00", "22:00"]; blank clears the window. */
function parseWindow(value: string): { start: string | null; end: string | null } {
  if (!value.trim()) return { start: null, end: null };
  const match = value.match(/(\d{1,2}:\d{2})\s*[-–—to]+\s*(\d{1,2}:\d{2})/);
  if (!match) throw new Error('Use the format 18:00 – 22:00 for the study window.');
  const pad = (t: string) => t.padStart(5, '0');
  return { start: pad(match[1]), end: pad(match[2]) };
}

export const userService = {
  async getPreferences(): Promise<PreferenceSettings> {
    return toPreferences(await api.get<PreferencesOut>('/users/me/preferences'));
  },

  async updatePreferences(prefs: PreferenceSettings): Promise<PreferenceSettings> {
    const window = parseWindow(prefs.preferredStudyHours);
    const res = await api.patch<PreferencesOut>('/users/me/preferences', {
      dailyStudyGoalMinutes: Math.round(prefs.dailyStudyGoalHours * 60),
      preferredStudyStart: window.start,
      preferredStudyEnd: window.end,
      defaultReminderTime: prefs.defaultReminderTime,
      timezone: prefs.timezone,
    });
    return toPreferences(res);
  },

  async getNotifications(): Promise<NotificationSettings> {
    return (await api.get<PreferencesOut>('/users/me/preferences')).notificationPreferences;
  },

  async updateNotifications(settings: NotificationSettings): Promise<NotificationSettings> {
    const res = await api.patch<PreferencesOut>('/users/me/preferences', { notificationPreferences: settings });
    return res.notificationPreferences;
  },
};
