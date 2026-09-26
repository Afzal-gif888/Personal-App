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

export type ReminderRepeat = 'none' | 'daily' | 'weekly' | 'monthly';
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

export type ActionCardType = 'create_reminder' | 'study_plan_generated' | 'task_created' | 'approval_required';
export type ActionCardStatus = 'pending' | 'approved' | 'rejected' | 'executed';

export interface ActionCardData {
  title: string;
  subtitle?: string;
  details?: Record<string, any>;
  targetId?: string;
  type: ActionCardType;
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
  user_id?: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageMetadata {
  actionCard?: ActionCardData;
  steps?: AgentStep[];
  status?: 'success' | 'error' | 'loading';
  error?: string;
  toolCalls?: any[];
}

export interface ChatMessage {
  id: string;
  conversation_id?: string;
  role: 'user' | 'assistant' | 'system';
  sender?: 'user' | 'assistant' | 'system'; // backward compatible alias
  content: string;
  text?: string; // backward compatible alias
  created_at: string;
  timestamp?: string; // backward compatible alias
  metadata?: ChatMessageMetadata;
  actionCard?: ActionCardData; // backward compatible alias
  steps?: AgentStep[]; // backward compatible alias
  isError?: boolean;
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
  steps: AgentStep[];
}

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired';

export interface ApprovalAction {
  id: string;
  runId?: string;
  type: string; // e.g. "Create Reminder", "Schedule Study Session", "Delete Document"
  title: string;
  description: string;
  details: Record<string, any>;
  status: ApprovalStatus;
  requestedAt: string;
  respondedAt?: string;
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
export type GoalStatus = 'active' | 'completed' | 'on_hold';
export interface Goal {
  id: string;
  title: string;
  category: GoalCategory;
  target: string;
  progress: number; // 0-100
  deadline?: string; // YYYY-MM-DD
  status: GoalStatus;
}
