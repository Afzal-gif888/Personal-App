import type {
  Task,
  Reminder,
  StudySession,
  Document,
  AgentRun,
  ApprovalAction,
  ChatMessage,
  UserProfile,
  NotificationSettings,
  PreferenceSettings,
  CalendarEvent,
  Bill,
  PaymentPlan,
  Expense,
  Goal,
} from '../types';
import { INITIAL_TASKS } from '../mocks/tasks';
import { INITIAL_REMINDERS } from '../mocks/reminders';
import { INITIAL_STUDY_SESSIONS } from '../mocks/studyPlans';
import { INITIAL_DOCUMENTS } from '../mocks/documents';
import { INITIAL_AGENT_RUNS } from '../mocks/agentRuns';
import { INITIAL_APPROVALS } from '../mocks/approvals';
import { INITIAL_CHAT_MESSAGES } from '../mocks/conversations';
import { MOCK_USER, MOCK_NOTIFICATIONS, MOCK_PREFERENCES } from '../mocks/users';
import { INITIAL_EVENTS } from '../mocks/events';
import { INITIAL_BILLS } from '../mocks/bills';
import { INITIAL_PAYMENT_PLANS } from '../mocks/paymentPlans';
import { INITIAL_EXPENSES } from '../mocks/expenses';
import { INITIAL_GOALS } from '../mocks/goals';

const STORAGE_KEYS = {
  TASKS: 'agentos_tasks',
  REMINDERS: 'agentos_reminders',
  STUDY_SESSIONS: 'agentos_study_sessions',
  DOCUMENTS: 'agentos_documents',
  AGENT_RUNS: 'agentos_agent_runs',
  APPROVALS: 'agentos_approvals',
  CHAT_MESSAGES: 'agentos_chat_messages',
  USER: 'agentos_user_profile',
  NOTIFICATIONS: 'agentos_notifications',
  PREFERENCES: 'agentos_preferences',
  AUTH_TOKEN: 'agentos_auth_token',
  EVENTS: 'agentos_events',
  BILLS: 'agentos_bills',
  PAYMENT_PLANS: 'agentos_payment_plans',
  EXPENSES: 'agentos_expenses',
  GOALS: 'agentos_goals',
};

function getStoredItem<T>(key: string, defaultValue: T): T {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (error) {
    console.warn(`Error reading localStorage key "${key}":`, error);
    return defaultValue;
  }
}

function setStoredItem<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.warn(`Error writing localStorage key "${key}":`, error);
  }
}

export const storage = {
  // Tasks
  getTasks: (): Task[] => getStoredItem(STORAGE_KEYS.TASKS, INITIAL_TASKS),
  setTasks: (tasks: Task[]): void => setStoredItem(STORAGE_KEYS.TASKS, tasks),

  // Reminders
  getReminders: (): Reminder[] => getStoredItem(STORAGE_KEYS.REMINDERS, INITIAL_REMINDERS),
  setReminders: (reminders: Reminder[]): void => setStoredItem(STORAGE_KEYS.REMINDERS, reminders),

  // Study Sessions
  getStudySessions: (): StudySession[] => getStoredItem(STORAGE_KEYS.STUDY_SESSIONS, INITIAL_STUDY_SESSIONS),
  setStudySessions: (sessions: StudySession[]): void => setStoredItem(STORAGE_KEYS.STUDY_SESSIONS, sessions),

  // Documents
  getDocuments: (): Document[] => getStoredItem(STORAGE_KEYS.DOCUMENTS, INITIAL_DOCUMENTS),
  setDocuments: (docs: Document[]): void => setStoredItem(STORAGE_KEYS.DOCUMENTS, docs),

  // Agent Runs
  getAgentRuns: (): AgentRun[] => getStoredItem(STORAGE_KEYS.AGENT_RUNS, INITIAL_AGENT_RUNS),
  setAgentRuns: (runs: AgentRun[]): void => setStoredItem(STORAGE_KEYS.AGENT_RUNS, runs),

  // Approvals
  getApprovals: (): ApprovalAction[] => getStoredItem(STORAGE_KEYS.APPROVALS, INITIAL_APPROVALS),
  setApprovals: (approvals: ApprovalAction[]): void => setStoredItem(STORAGE_KEYS.APPROVALS, approvals),

  // Chat Messages
  getChatMessages: (): ChatMessage[] => getStoredItem(STORAGE_KEYS.CHAT_MESSAGES, INITIAL_CHAT_MESSAGES),
  setChatMessages: (messages: ChatMessage[]): void => setStoredItem(STORAGE_KEYS.CHAT_MESSAGES, messages),

  // User Profile
  getUser: (): UserProfile => getStoredItem(STORAGE_KEYS.USER, MOCK_USER),
  setUser: (user: UserProfile): void => setStoredItem(STORAGE_KEYS.USER, user),

  // Notifications
  getNotifications: (): NotificationSettings => getStoredItem(STORAGE_KEYS.NOTIFICATIONS, MOCK_NOTIFICATIONS),
  setNotifications: (settings: NotificationSettings): void => setStoredItem(STORAGE_KEYS.NOTIFICATIONS, settings),

  // Preferences
  getPreferences: (): PreferenceSettings => getStoredItem(STORAGE_KEYS.PREFERENCES, MOCK_PREFERENCES),
  setPreferences: (prefs: PreferenceSettings): void => setStoredItem(STORAGE_KEYS.PREFERENCES, prefs),

  // Events
  getEvents: (): CalendarEvent[] => getStoredItem(STORAGE_KEYS.EVENTS, INITIAL_EVENTS),
  setEvents: (events: CalendarEvent[]): void => setStoredItem(STORAGE_KEYS.EVENTS, events),

  // Bills
  getBills: (): Bill[] => getStoredItem(STORAGE_KEYS.BILLS, INITIAL_BILLS),
  setBills: (bills: Bill[]): void => setStoredItem(STORAGE_KEYS.BILLS, bills),

  // Payment Plans
  getPaymentPlans: (): PaymentPlan[] => getStoredItem(STORAGE_KEYS.PAYMENT_PLANS, INITIAL_PAYMENT_PLANS),
  setPaymentPlans: (plans: PaymentPlan[]): void => setStoredItem(STORAGE_KEYS.PAYMENT_PLANS, plans),

  // Expenses
  getExpenses: (): Expense[] => getStoredItem(STORAGE_KEYS.EXPENSES, INITIAL_EXPENSES),
  setExpenses: (expenses: Expense[]): void => setStoredItem(STORAGE_KEYS.EXPENSES, expenses),

  // Goals
  getGoals: (): Goal[] => getStoredItem(STORAGE_KEYS.GOALS, INITIAL_GOALS),
  setGoals: (goals: Goal[]): void => setStoredItem(STORAGE_KEYS.GOALS, goals),

  // Auth
  getToken: (): string | null => localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN),
  setToken: (token: string | null): void => {
    if (token) localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token);
    else localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
  },

  // Reset to initial demo data
  resetAll: (): void => {
    localStorage.clear();
  },
};
