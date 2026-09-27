/** Local calendar date as YYYY-MM-DD (toISOString() would shift to UTC). */
export function todayISO(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** Parses YYYY-MM-DD as a local date rather than UTC midnight. */
function parseDate(dateStr: string): Date {
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    const [y, m, d] = dateStr.split('-').map(Number);
    return new Date(y, m - 1, d);
  }
  return new Date(dateStr);
}

export function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  const date = parseDate(dateStr);
  if (isNaN(date.getTime())) return dateStr;
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
}

export function formatShortDate(dateStr: string): string {
  if (!dateStr) return '';
  const date = parseDate(dateStr);
  if (isNaN(date.getTime())) return dateStr;
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(date);
}

/** "Today", "Tomorrow", "Yesterday", otherwise "Mon, Sep 29". */
export function formatDayLabel(dateStr: string): string {
  if (!dateStr) return '';
  if (dateStr === todayISO()) return 'Today';
  if (dateStr === todayISO(1)) return 'Tomorrow';
  if (dateStr === todayISO(-1)) return 'Yesterday';
  const date = parseDate(dateStr);
  if (isNaN(date.getTime())) return dateStr;
  return new Intl.DateTimeFormat('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).format(date);
}

export function formatLongDate(date = new Date()): string {
  return new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'long', day: 'numeric' }).format(date);
}

export function formatTime(timeStr: string): string {
  if (!timeStr) return '';
  const [hours, minutes] = timeStr.split(':');
  if (!hours || !minutes) return timeStr;
  const date = new Date();
  date.setHours(parseInt(hours, 10), parseInt(minutes, 10));
  return new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit', hour12: true }).format(date);
}

export function formatRelativeTime(isoOrTime: string): string {
  if (!isoOrTime) return '';
  const date = new Date(isoOrTime);
  if (isNaN(date.getTime())) return isoOrTime;
  const diffInSeconds = Math.floor((Date.now() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return 'Just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 172800) return 'Yesterday';
  return formatDate(isoOrTime);
}

/** Days from today until the given YYYY-MM-DD (negative when past). */
export function daysUntil(dateStr: string): number {
  const target = parseDate(dateStr).getTime();
  const today = parseDate(todayISO()).getTime();
  return Math.round((target - today) / 86400000);
}

const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

export function formatCurrency(amount: number): string {
  return currency.format(amount);
}

/** Formats raw ISO dates / 24h times found in loosely-typed detail maps. */
export function formatDetailValue(value: unknown): string {
  const str = String(value);
  if (/^\d{4}-\d{2}-\d{2}$/.test(str)) return formatDate(str);
  if (/^\d{2}:\d{2}$/.test(str)) return formatTime(str);
  return str;
}

/** "DueDate" / "due_date" → "Due date" for key/value detail lists. */
export function humanizeKey(key: string): string {
  const spaced = key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .toLowerCase();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export function capitalize(value: string): string {
  return value ? value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, ' ') : value;
}
