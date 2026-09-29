import React, { useState } from 'react';
import { Plus, Bell, Pencil, Trash2, Repeat, Check, AlarmClock } from 'lucide-react';
import { useReminders } from '../hooks/useReminders';
import type { Reminder, ReminderRepeat } from '../types';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Tabs } from '../components/ui/Tabs';
import { Modal } from '../components/ui/Modal';
import { EmptyState } from '../components/ui/EmptyState';
import { RowActions } from '../components/ui/RowActions';
import { Tooltip } from '../components/ui/Tooltip';
import { formatDayLabel, formatTime, todayISO } from '../utils/formatters';
import { REMINDER_STATUS_STYLES, statusStyle } from '../utils/status';
import { cn } from '../utils/cn';

type View = 'today' | 'upcoming' | 'completed';

const REPEAT_LABELS: Record<ReminderRepeat, string> = {
  none: 'Does not repeat',
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
  yearly: 'Yearly',
};

export const RemindersPage: React.FC = () => {
  const { reminders, createReminder, updateReminder, toggleComplete, snoozeReminder, deleteReminder } = useReminders();

  const [view, setView] = useState<View>('today');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<Reminder | null>(null);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState(todayISO());
  const [time, setTime] = useState('19:00');
  const [repeat, setRepeat] = useState<ReminderRepeat>('none');

  const openCreate = () => {
    setEditing(null);
    setTitle('');
    setDescription('');
    setDate(todayISO());
    setTime('19:00');
    setRepeat('none');
    setIsModalOpen(true);
  };

  const openEdit = (r: Reminder) => {
    setEditing(r);
    setTitle(r.title);
    setDescription(r.description || '');
    setDate(r.date);
    setTime(r.time);
    setRepeat(r.repeat);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    if (editing) {
      await updateReminder({ id: editing.id, updates: { title, description, date, time, repeat } });
    } else {
      await createReminder({ title, description, date, time, repeat, status: 'upcoming' });
    }
    setIsModalOpen(false);
  };

  const today = todayISO();
  const isToday = (r: Reminder) => r.status !== 'completed' && (r.status === 'today' || r.date <= today);
  const buckets: Record<View, Reminder[]> = {
    today: reminders.filter(isToday),
    upcoming: reminders.filter((r) => r.status !== 'completed' && !isToday(r)),
    completed: reminders.filter((r) => r.status === 'completed'),
  };
  const visible = [...buckets[view]].sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time));

  return (
    <Page>
      <PageHeader
        title="Reminders"
        description="Time-based nudges for bills, deadlines and appointments."
        actions={
          <Button onClick={openCreate} leftIcon={<Plus className="size-4" />}>
            New reminder
          </Button>
        }
      />

      <Tabs
        activeTab={view}
        onChange={(id) => setView(id as View)}
        tabs={[
          { id: 'today', label: 'Today', badge: buckets.today.length },
          { id: 'upcoming', label: 'Upcoming', badge: buckets.upcoming.length },
          { id: 'completed', label: 'Completed', badge: buckets.completed.length },
        ]}
      />

      {visible.length === 0 ? (
        <EmptyState
          icon={<Bell />}
          title={view === 'today' ? 'Nothing due today' : view === 'upcoming' ? 'No upcoming reminders' : 'No completed reminders'}
          description="Create a reminder, or ask the assistant to set one for you."
          actionLabel="New reminder"
          onAction={openCreate}
        />
      ) : (
        <Card flush className="overflow-hidden">
          <ul className="divide-y divide-line">
            {visible.map((r) => {
              const done = r.status === 'completed';
              const s = statusStyle(REMINDER_STATUS_STYLES, r.status);
              return (
                <li key={r.id} className="flex items-center gap-4 px-5 py-3.5">
                  <span
                    className={cn(
                      'hidden sm:flex items-center justify-center size-9 shrink-0 rounded-lg border',
                      done ? 'border-line bg-subtle text-fg-faint' : 'border-warning-line bg-warning-subtle text-warning'
                    )}
                  >
                    <Bell className="size-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className={cn('text-sm font-medium truncate', done ? 'text-fg-subtle line-through' : 'text-fg')}>{r.title}</p>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-0.5 text-xs text-fg-subtle">
                      <span className="tabular">
                        {formatDayLabel(r.date)} · {formatTime(r.time)}
                      </span>
                      {r.repeat !== 'none' && (
                        <span className="inline-flex items-center gap-1">
                          <Repeat className="size-3" />
                          {REPEAT_LABELS[r.repeat]}
                        </span>
                      )}
                      {r.description && <span className="truncate max-w-xs">{r.description}</span>}
                    </div>
                  </div>
                  {r.status === 'snoozed' && <Badge variant={s.variant}>{s.label}</Badge>}
                  <div className="flex items-center gap-1 shrink-0">
                    {!done && (
                      <Tooltip content="Snooze 15 min">
                        <Button variant="ghost" size="sm" iconOnly onClick={() => snoozeReminder({ id: r.id })} aria-label="Snooze">
                          <AlarmClock className="size-4" />
                        </Button>
                      </Tooltip>
                    )}
                    <Button
                      variant="secondary"
                      size="xs"
                      onClick={() => toggleComplete(r.id)}
                      leftIcon={done ? undefined : <Check className="size-3.5" />}
                    >
                      {done ? 'Reopen' : 'Done'}
                    </Button>
                    <RowActions
                      label={`Actions for ${r.title}`}
                      items={[
                        { id: 'edit', label: 'Edit', icon: <Pencil />, onClick: () => openEdit(r) },
                        {
                          id: 'delete',
                          label: 'Delete',
                          icon: <Trash2 />,
                          destructive: true,
                          separated: true,
                          onClick: () => deleteReminder(r.id),
                        },
                      ]}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      )}

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editing ? 'Edit reminder' : 'New reminder'}
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" form="reminder-form">
              {editing ? 'Save changes' : 'Create reminder'}
            </Button>
          </>
        }
      >
        <form id="reminder-form" onSubmit={handleSubmit} className="space-y-4">
          <Input label="Title" placeholder="e.g. Pay electricity bill" value={title} onChange={(e) => setTitle(e.target.value)} required autoFocus />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
            <Input label="Time" type="time" value={time} onChange={(e) => setTime(e.target.value)} required />
          </div>
          <Select
            label="Repeat"
            value={repeat}
            onChange={(e) => setRepeat(e.target.value as ReminderRepeat)}
            options={Object.entries(REPEAT_LABELS).map(([value, label]) => ({ value, label }))}
          />
          <Textarea label="Notes" placeholder="Optional" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
        </form>
      </Modal>
    </Page>
  );
};
