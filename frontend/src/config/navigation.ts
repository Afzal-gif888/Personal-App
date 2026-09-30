import type { LucideIcon } from 'lucide-react';
import {
  Home,
  MessageSquare,
  Inbox,
  CheckSquare,
  CalendarDays,
  Bell,
  Target,
  BookOpen,
  FileText,
  Receipt,
  Wallet,
  PiggyBank,
  Activity,
  Settings,
} from 'lucide-react';

export interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: LucideIcon;
  /** Icon colour: a --color-nav-* token from index.css, matching what the section is about. */
  color: string;
  description: string;
  /** Shows the pending-approvals count next to the item. */
  showApprovalCount?: boolean;
}

export interface NavGroup {
  id: string;
  label?: string;
  items: NavItem[];
}

/**
 * Information architecture, ordered by the product workflow:
 *   Workspace  → ask the assistant and review what it proposes
 *   Planning / Study / Finance → where approved work lands
 *   Automation → audit trail of every agent run
 */
export const NAV_GROUPS: NavGroup[] = [
  {
    id: 'workspace',
    items: [
      { id: 'home', color: 'var(--color-nav-home)', label: 'Home', path: '/dashboard', icon: Home, description: 'Today at a glance' },
      { id: 'assistant', color: 'var(--color-nav-assistant)', label: 'Assistant', path: '/chat', icon: MessageSquare, description: 'Ask the AI to plan, schedule or summarise' },
      {
        id: 'approvals', color: 'var(--color-nav-approvals)',
        label: 'Approvals',
        path: '/approvals',
        icon: Inbox,
        description: 'Review actions the assistant has proposed',
        showApprovalCount: true,
      },
    ],
  },
  {
    id: 'planning',
    label: 'Planning',
    items: [
      { id: 'tasks', color: 'var(--color-nav-tasks)', label: 'Tasks', path: '/tasks', icon: CheckSquare, description: 'Assignments and to-dos across every area' },
      { id: 'calendar', color: 'var(--color-nav-calendar)', label: 'Calendar', path: '/calendar', icon: CalendarDays, description: 'Classes, meetings and appointments' },
      { id: 'reminders', color: 'var(--color-nav-reminders)', label: 'Reminders', path: '/reminders', icon: Bell, description: 'Time-based nudges' },
      { id: 'goals', color: 'var(--color-nav-goals)', label: 'Goals', path: '/goals', icon: Target, description: 'Longer-term objectives and progress' },
    ],
  },
  {
    id: 'study',
    label: 'Study',
    items: [
      { id: 'study-plan', color: 'var(--color-nav-study)', label: 'Study plan', path: '/study-plan', icon: BookOpen, description: 'Scheduled revision sessions' },
      { id: 'documents', color: 'var(--color-nav-documents)', label: 'Documents', path: '/documents', icon: FileText, description: 'Notes and syllabi the assistant can read' },
    ],
  },
  {
    id: 'finance',
    label: 'Finance',
    items: [
      { id: 'bills', color: 'var(--color-nav-bills)', label: 'Bills & payments', path: '/bills', icon: Receipt, description: 'Upcoming bills and instalment plans' },
      { id: 'expenses', color: 'var(--color-nav-expenses)', label: 'Expenses', path: '/expenses', icon: Wallet, description: 'Day-to-day spending' },
      { id: 'budgets', color: 'var(--color-nav-budgets)', label: 'Budgets', path: '/budgets', icon: PiggyBank, description: 'Monthly spending limits' },
    ],
  },
  {
    id: 'automation',
    label: 'Automation',
    items: [
      { id: 'agent-runs', color: 'var(--color-nav-activity)', label: 'Agent activity', path: '/agent-runs', icon: Activity, description: 'Every assistant run, step by step' },
    ],
  },
];

export const SETTINGS_NAV: NavItem = {
  id: 'settings', color: 'var(--color-nav-settings)',
  label: 'Settings',
  path: '/settings/profile',
  icon: Settings,
  description: 'Profile, notifications and preferences',
};

export const ALL_NAV_ITEMS: NavItem[] = [...NAV_GROUPS.flatMap((g) => g.items), SETTINGS_NAV];

export function isNavItemActive(item: NavItem, pathname: string) {
  const base = item.path.startsWith('/settings') ? '/settings' : item.path;
  return pathname === base || pathname.startsWith(`${base}/`);
}

/** Resolves the group + item for the current route, for breadcrumbs. */
export function findNavContext(pathname: string): { group?: NavGroup; item?: NavItem } {
  for (const group of NAV_GROUPS) {
    const item = group.items.find((i) => isNavItemActive(i, pathname));
    if (item) return { group, item };
  }
  if (isNavItemActive(SETTINGS_NAV, pathname)) return { item: SETTINGS_NAV };
  return {};
}
