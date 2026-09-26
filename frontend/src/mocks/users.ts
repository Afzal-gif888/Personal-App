import type { UserProfile, NotificationSettings, PreferenceSettings } from '../types';

export const MOCK_USER: UserProfile = {
  id: 'user-alex-101',
  name: 'Alex Rivera',
  email: 'student@agentos.demo',
  avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=256&q=80',
  university: 'Stanford University',
  major: 'Computer Science & AI',
  academicYear: 'Senior (Year 4)',
  bio: 'Focusing on Machine Learning, Database Management Systems, and Distributed Computing.',
};

export const MOCK_NOTIFICATIONS: NotificationSettings = {
  reminders: true,
  studyNotifications: true,
  aiNotifications: true,
  emailNotifications: false,
};

export const MOCK_PREFERENCES: PreferenceSettings = {
  dailyStudyGoalHours: 4,
  preferredStudyHours: '18:00 - 22:00',
  defaultReminderTime: '09:00',
  timezone: 'America/Los_Angeles (PST)',
};
