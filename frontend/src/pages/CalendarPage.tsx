import React, { useState } from 'react';
import { Plus, Pencil, Trash2, MapPin, Video, CalendarDays } from 'lucide-react';
import { useEvents } from '../hooks/useEvents';
import type { CalendarEvent, EventType } from '../types';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { Tabs } from '../components/ui/Tabs';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { RowActions } from '../components/ui/RowActions';
import { Toolbar, FilterSelect } from '../components/ui/Toolbar';
import { formatDayLabel, formatDate, formatTime, todayISO } from '../utils/formatters';
import { cn } from '../utils/cn';

const EVENT_TYPES: Record<EventType, { label: string; bar: string }> = {
  class: { label: 'Class', bar: 'bg-accent' },
  exam: { label: 'Exam', bar: 'bg-danger-solid' },
  deadline: { label: 'Deadline', bar: 'bg-warning' },
  meeting: { label: 'Meeting', bar: 'bg-fg-muted' },
  appointment: { label: 'Appointment', bar: 'bg-success' },
  personal: { label: 'Personal', bar: 'bg-fg-faint' },
  other: { label: 'Other', bar: 'bg-line-strong' },
};

type Range = 'upcoming' | 'past' | 'all';

export const CalendarPage: React.FC = () => {
  const { data: events = [], create, update, remove } = useEvents();

  const [range, setRange] = useState<Range>('upcoming');
  const [typeFilter, setTypeFilter] = useState<EventType | 'all'>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState(todayISO());
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('10:00');
  const [type, setType] = useState<EventType>('meeting');
  const [location, setLocation] = useState('');

  const openCreate = () => {
    setEditingEvent(null);
    setTitle('');
    setDescription('');
    setDate(todayISO());
    setStartTime('09:00');
    setEndTime('10:00');
    setType('meeting');
    setLocation('');
    setIsModalOpen(true);
  };

  const openEdit = (ev: CalendarEvent) => {
    setEditingEvent(ev);
    setTitle(ev.title);
    setDescription(ev.description || '');
    setDate(ev.date);
    setStartTime(ev.startTime);
    setEndTime(ev.endTime || '');
    setType(ev.type);
    setLocation(ev.location || '');
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    const data = { title, description, date, startTime, endTime, type, location };
    if (editingEvent) await update.mutateAsync({ id: editingEvent.id, data });
    else await create.mutateAsync(data);
    setIsModalOpen(false);
  };

  const today = todayISO();
  const inRange = (ev: CalendarEvent) => (range === 'upcoming' ? ev.date >= today : range === 'past' ? ev.date < today : true);
  const filtered = events
    .filter((ev) => inRange(ev) && (typeFilter === 'all' || ev.type === typeFilter))
    .sort((a, b) => (a.date + a.startTime).localeCompare(b.date + b.startTime));
  if (range === 'past') filtered.reverse();

  const byDate = filtered.reduce<Record<string, CalendarEvent[]>>((acc, ev) => {
    (acc[ev.date] ||= []).push(ev);
    return acc;
  }, {});

  return (
    <Page>
      <PageHeader
        title="Calendar"
        description="Classes, exams, meetings and appointments in one agenda."
        actions={
          <Button onClick={openCreate} leftIcon={<Plus className="size-4" />}>
            New event
          </Button>
        }
      />

      <Toolbar>
        <Tabs
          variant="pills"
          activeTab={range}
          onChange={(id) => setRange(id as Range)}
          tabs={[
            { id: 'upcoming', label: 'Upcoming', badge: events.filter((e) => e.date >= today).length },
            { id: 'past', label: 'Past', badge: events.filter((e) => e.date < today).length },
            { id: 'all', label: 'All', badge: events.length },
          ]}
        />
        <FilterSelect
          label="Event type"
          value={typeFilter}
          onChange={(v) => setTypeFilter(v as EventType | 'all')}
          options={[
            { value: 'all', label: 'All types' },
            ...Object.entries(EVENT_TYPES).map(([value, c]) => ({ value, label: c.label })),
          ]}
        />
      </Toolbar>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<CalendarDays />}
          title="No events"
          description="Nothing matches this view. Add an event or change the filters."
          actionLabel="New event"
          onAction={openCreate}
        />
      ) : (
        <Card flush className="overflow-hidden">
          {Object.entries(byDate).map(([day, list]) => (
            <section key={day} className="border-b border-line last:border-b-0">
              <header className="flex items-center gap-2 px-5 h-9 bg-subtle/70 border-b border-line">
                <span className={cn('text-xs font-medium', day === today ? 'text-accent' : 'text-fg-muted')}>
                  {formatDayLabel(day)}
                </span>
                {formatDayLabel(day) !== formatDate(day) && <span className="text-xs text-fg-faint">{formatDate(day)}</span>}
              </header>
              <ul className="divide-y divide-line">
                {list.map((ev) => {
                  const cfg = EVENT_TYPES[ev.type];
                  const isLink = ev.location?.startsWith('http');
                  return (
                    <li key={ev.id} className="flex items-stretch gap-4 px-5 py-3.5">
                      <div className="w-20 shrink-0 text-sm tabular">
                        <p className="text-fg font-medium">{formatTime(ev.startTime)}</p>
                        {ev.endTime && <p className="text-xs text-fg-subtle">{formatTime(ev.endTime)}</p>}
                      </div>
                      <span className={cn('w-1 rounded-full shrink-0', cfg.bar)} aria-hidden="true" />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-sm font-medium text-fg">{ev.title}</p>
                          <span className="text-xs text-fg-subtle">{cfg.label}</span>
                        </div>
                        {ev.description && <p className="text-sm text-fg-subtle mt-0.5 line-clamp-1">{ev.description}</p>}
                        {ev.location && (
                          <p className="flex items-center gap-1 text-xs text-fg-subtle mt-1 truncate">
                            {isLink ? <Video className="size-3.5 shrink-0" /> : <MapPin className="size-3.5 shrink-0" />}
                            {isLink ? (
                              <a href={ev.location} target="_blank" rel="noreferrer" className="text-accent hover:underline truncate">
                                Join meeting
                              </a>
                            ) : (
                              ev.location
                            )}
                          </p>
                        )}
                      </div>
                      <RowActions
                        label={`Actions for ${ev.title}`}
                        items={[
                          { id: 'edit', label: 'Edit', icon: <Pencil />, onClick: () => openEdit(ev) },
                          {
                            id: 'delete',
                            label: 'Delete',
                            icon: <Trash2 />,
                            destructive: true,
                            separated: true,
                            onClick: () => setDeletingId(ev.id),
                          },
                        ]}
                      />
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </Card>
      )}

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingEvent ? 'Edit event' : 'New event'}
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" form="event-form" isLoading={create.isPending || update.isPending}>
              {editingEvent ? 'Save changes' : 'Create event'}
            </Button>
          </>
        }
      >
        <form id="event-form" onSubmit={handleSubmit} className="space-y-4">
          <Input label="Title" placeholder="e.g. ML lecture" value={title} onChange={(e) => setTitle(e.target.value)} required autoFocus />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select
              label="Type"
              value={type}
              onChange={(e) => setType(e.target.value as EventType)}
              options={Object.entries(EVENT_TYPES).map(([v, c]) => ({ value: v, label: c.label }))}
            />
            <Input label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Start" type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} required />
            <Input label="End" type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
          </div>
          <Input
            label="Location or link"
            placeholder="Room 304 or https://meet.google.com/…"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
          <Textarea label="Notes" placeholder="Optional" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deletingId}
        onClose={() => setDeletingId(null)}
        onConfirm={async () => {
          if (deletingId) {
            await remove.mutateAsync(deletingId);
            setDeletingId(null);
          }
        }}
        title="Delete event?"
        message="This event will be removed from your calendar."
      />
    </Page>
  );
};
