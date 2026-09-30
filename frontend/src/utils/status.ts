import type { BadgeVariant } from '../components/ui/Badge';

/**
 * Single source of truth for how domain statuses are labelled and coloured.
 * Pages should never pick badge colours ad hoc.
 */
interface StatusStyle {
  label: string;
  variant: BadgeVariant;
}

const style = (label: string, variant: BadgeVariant): StatusStyle => ({ label, variant });

export const PRIORITY_STYLES: Record<string, StatusStyle> = {
  high: style('High', 'error'),
  medium: style('Medium', 'warning'),
  low: style('Low', 'neutral'),
};

export const TASK_STATUS_STYLES: Record<string, StatusStyle> = {
  pending: style('To do', 'neutral'),
  in_progress: style('In progress', 'info'),
  completed: style('Done', 'success'),
};

export const BILL_STATUS_STYLES: Record<string, StatusStyle> = {
  upcoming: style('Upcoming', 'info'),
  due: style('Due today', 'warning'),
  overdue: style('Overdue', 'error'),
  paid: style('Paid', 'success'),
};

export const REMINDER_STATUS_STYLES: Record<string, StatusStyle> = {
  today: style('Today', 'info'),
  upcoming: style('Scheduled', 'neutral'),
  snoozed: style('Snoozed', 'warning'),
  completed: style('Done', 'success'),
};

export const SESSION_STATUS_STYLES: Record<string, StatusStyle> = {
  scheduled: style('Scheduled', 'info'),
  completed: style('Completed', 'success'),
  cancelled: style('Cancelled', 'neutral'),
};

export const RUN_STATUS_STYLES: Record<string, StatusStyle> = {
  completed: style('Completed', 'success'),
  running: style('Running', 'info'),
  failed: style('Failed', 'error'),
  awaiting_approval: style('Awaiting approval', 'warning'),
};

export const APPROVAL_STATUS_STYLES: Record<string, StatusStyle> = {
  pending: style('Needs review', 'warning'),
  approved: style('Approved', 'success'),
  rejected: style('Rejected', 'error'),
  expired: style('Expired', 'neutral'),
};

export const GOAL_STATUS_STYLES: Record<string, StatusStyle> = {
  active: style('Active', 'info'),
  completed: style('Completed', 'success'),
  on_hold: style('On hold', 'neutral'),
};

export const DOCUMENT_STATUS_STYLES: Record<string, StatusStyle> = {
  ready: style('Ready', 'success'),
  processing: style('Processing', 'info'),
  uploading: style('Uploading', 'info'),
  failed: style('Failed', 'error'),
  // Ready documents show their search-index state instead.
  index_pending: style('Indexing', 'info'),
  index_indexing: style('Indexing', 'info'),
  index_indexed: style('Searchable', 'success'),
  index_failed: style('Index failed', 'warning'),
  index_unsupported: style('Not searchable', 'neutral'),
};

/** Badge key for a document: upload state, or the search-index state once it's ready. */
export function documentBadgeKey(doc: { status: string; indexStatus?: string }): string {
  return doc.status === 'ready' && doc.indexStatus ? `index_${doc.indexStatus}` : doc.status;
}

export function documentIsIndexing(doc: { status: string; indexStatus?: string }): boolean {
  return doc.status === 'ready' && (doc.indexStatus === 'pending' || doc.indexStatus === 'indexing');
}

export function statusStyle(map: Record<string, StatusStyle>, key: string): StatusStyle {
  return map[key] ?? style(key.replace(/_/g, ' '), 'neutral');
}

export const CATEGORY_LABELS: Record<string, string> = {
  academic: 'Academic',
  personal: 'Personal',
  financial: 'Financial',
  career: 'Career',
  general: 'General',
};
