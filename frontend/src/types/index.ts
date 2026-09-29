export type Priority = 'low' | 'medium' | 'high';
export type TaskStatus = 'pending' | 'in_progress' | 'completed';
export type TaskCategory = 'academic' | 'personal' | 'financial' | 'career' | 'general';

export interface Task {
  id: string;
  title: string;
  description?: string;
  subject?: string;
  category: TaskCategory;
  priority: Priority;
  dueDate: string; // YYYY-MM-DD
  dueTime?: string; // HH:mm
  status: TaskStatus;
  createdAt: string;
  updatedAt: string;
}
export type StudySessionStatus = 'scheduled' | 'completed' | 'cancelled';

export interface StudySession {
  id: string;
  subject: string;
  topic: string;
  date: string; // YYYY-MM-DD
  startTime: string; // HH:mm
  endTime: string; // HH:mm
  priority: Priority;
  status: StudySessionStatus;
  notes?: string;
}

export type ReminderRepeat = 'none' | 'daily' | 'weekly' | 'monthly' | 'yearly';
export type ReminderStatus = 'upcoming' | 'today' | 'completed' | 'snoozed';

export interface Reminder {
  id: string;
  title: string;
  description?: string;
  date: string; // YYYY-MM-DD
  time: string; // HH:mm
  repeat: ReminderRepeat;
  status: ReminderStatus;
  category?: TaskCategory;
  createdAt: string;
}

export type DocumentStatus = 'ready' | 'processing' | 'uploading' | 'failed';

export interface Document {
  id: string;
  name: string;
  size: string;
  type: string;
  pageCount?: number;
  uploadedAt: string;
  category: string;
  status: DocumentStatus;
  url?: string;
  progress?: number; // 0 - 100 for uploading simulation
}

/** Agent write tools; each proposal becomes an approval card. */
export type ActionCardType =
  | 'create_task'
  | 'complete_task'
  | 'create_reminder'
  | 'create_event'
  | 'create_study_plan'
  | 'log_expense'
  | 'mark_bill_paid'
  | 'set_budget';
export type ActionCardStatus = 'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled';

export interface ActionCardData {
  approvalId: string;
  type: ActionCardType | string;
  label: string; // e.g. "Create reminder"
  title: string;
  description?: string;
  details?: Record<string, any>;
  status: ActionCardStatus;
}

export interface AgentStep {
  id: string;
  title: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  timestamp: string;
  toolName?: string;
  toolInput?: Record<string, any>;
  toolOutput?: Record<string, any>;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChatMessageMetadata {
  actions?: ActionCardData[];
  steps?: AgentStep[];
  status?: 'success' | 'error';
  error?: string;
}

export interface ChatMessage {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
  agentRunId?: string | null;
  metadata?: ChatMessageMetadata;
}

export type AgentRunStatus = 'completed' | 'running' | 'failed' | 'awaiting_approval';

export interface AgentRun {
  id: string;
  runNumber: string; // e.g., "#1042"
  request: string;
  status: AgentRunStatus;
  startedAt: string;
  completedAt?: string;
  duration: string;
  toolsUsed: string[];
  steps: AgentStep[]; // only filled in on the run detail
  errorMessage?: string;
}

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled';

export interface ApprovalAction {
  id: string;
  runId?: string;
  action: string; // tool name, e.g. "create_reminder"
  type: string; // label, e.g. "Create reminder"
  title: string;
  description: string;
  details: Record<string, any>;
  status: ApprovalStatus;
  requestedAt: string;
  respondedAt?: string;
  expiresAt?: string;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  university: string;
  major: string;
  academicYear: string;
  bio?: string;
}

export interface NotificationSettings {
  reminders: boolean;
  studyNotifications: boolean;
  aiNotifications: boolean;
  emailNotifications: boolean;
}

export interface PreferenceSettings {
  dailyStudyGoalHours: number;
  preferredStudyHours: string;
  defaultReminderTime: string;
  timezone: string;
}

export interface Subject {
  id: string;
  name: string;
  code: string;
  color?: string;
}

export type EventType = 'class' | 'meeting' | 'appointment' | 'exam' | 'deadline' | 'personal' | 'other';
export interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  date: string; // YYYY-MM-DD
  startTime: string; // HH:mm
  endTime?: string; // HH:mm
  type: EventType;
  location?: string;
  createdAt: string;
}

export type BillStatus = 'upcoming' | 'due' | 'paid' | 'overdue';
export interface Bill {
  id: string;
  title: string;
  amount: number;
  dueDate: string; // YYYY-MM-DD
  category: string;
  status: BillStatus;
  isRecurring: boolean;
  frequency?: string;
  paymentMethod?: string;
  notes?: string;
}

export interface PaymentPlan {
  id: string;
  title: string;
  totalAmount: number;
  installmentAmount: number;
  frequency: string;
  nextPaymentDate: string; // YYYY-MM-DD
  remainingAmount: number;
  totalInstallments: number;
  completedInstallments: number;
  status: 'active' | 'completed';
}

export interface Expense {
  id: string;
  title: string;
  amount: number;
  category: string;
  date: string; // YYYY-MM-DD
  description?: string;
}

export type GoalCategory = 'academic' | 'financial' | 'career' | 'personal' | 'general';
export type GoalStatus = 'active' | 'completed' | 'on_hold' | 'abandoned';
export interface Goal {
  id: string;
  title: string;
  category: GoalCategory;
  target: string;
  progress: number; // 0-100
  deadline?: string; // YYYY-MM-DD
  status: GoalStatus;
}

export type ExpenseCategory = 'food' | 'travel' | 'education' | 'shopping' | 'bills' | 'entertainment' | 'health' | 'other';
export type BudgetStatus = 'on_track' | 'warning' | 'over';

/** A monthly spending limit for one category, or for all spending when `category` is null. */
export interface Budget {
  id: string;
  category: ExpenseCategory | null;
  amount: number;
  currency: string;
  alertThreshold: number; // percent of the limit that counts as "warning"
  month: string; // YYYY-MM the progress below is for
  spent: number;
  remaining: number;
  percentUsed: number;
  status: BudgetStatus;
}
