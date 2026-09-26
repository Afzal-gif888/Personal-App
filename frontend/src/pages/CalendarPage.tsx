import React, { useState } from 'react';
import { Plus, Trash2, Edit3, MapPin, Clock, Video } from 'lucide-react';
import { useEvents } from '../hooks/useEvents';
import type { CalendarEvent, EventType } from '../types';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { formatDate } from '../utils/formatters';

const EVENT_TYPE_CONFIG: Record<EventType, { label: string; color: string }> = {
  class: { label: 'Class', color: 'bg-blue-50 text-blue-700 border border-blue-100' },
  meeting: { label: 'Meeting', color: 'bg-amber-50 text-amber-700 border border-amber-100' },
  appointment: { label: 'Appointment', color: 'bg-purple-50 text-purple-700 border border-purple-100' },
  exam: { label: 'Exam', color: 'bg-red-50 text-red-700 border border-red-100' },
  deadline: { label: 'Deadline', color: 'bg-orange-50 text-orange-700 border border-orange-100' },
  personal: { label: 'Personal', color: 'bg-emerald-50 text-emerald-700 border border-emerald-100' },
  other: { label: 'Other', color: 'bg-[#F7F7F7] text-[#666666] border border-[#EAEAEA]' },
};

// Group events by date
function groupByDate(events: CalendarEvent[]): Record<string, CalendarEvent[]> {
  const sorted = [...events].sort((a, b) => {
    const dateCompare = a.date.localeCompare(b.date);
    if (dateCompare !== 0) return dateCompare;
    return a.startTime.localeCompare(b.startTime);
  });
  return sorted.reduce((acc, ev) => {
    acc[ev.date] = acc[ev.date] ? [...acc[ev.date], ev] : [ev];
    return acc;
  }, {} as Record<string, CalendarEvent[]>);
}

export const CalendarPage: React.FC = () => {
  const { data: events = [], create, update, remove } = useEvents();

  const [typeFilter, setTypeFilter] = useState<EventType | 'all'>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('10:00');
  const [type, setType] = useState<EventType>('meeting');
  const [location, setLocation] = useState('');

  const resetForm = () => {
    setTitle(''); setDescription(''); setDate(new Date().toISOString().split('T')[0]);
    setStartTime('09:00'); setEndTime('10:00'); setType('meeting'); setLocation('');
  };

  const openCreate = () => {
    setEditingEvent(null); resetForm(); setIsModalOpen(true);
  };

  const openEdit = (ev: CalendarEvent) => {
    setEditingEvent(ev);
    setTitle(ev.title); setDescription(ev.description || ''); setDate(ev.date);
    setStartTime(ev.startTime); setEndTime(ev.endTime || ''); setType(ev.type); setLocation(ev.location || '');
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    const data = { title, description, date, startTime, endTime, type, location };
    if (editingEvent) {
      await update.mutateAsync({ id: editingEvent.id, data });
    } else {
      await create.mutateAsync(data);
    }
    setIsModalOpen(false);
  };

  const filtered = events.filter((ev) => typeFilter === 'all' || ev.type === typeFilter);
  const grouped = groupByDate(filtered);
  const dates = Object.keys(grouped);

  return (
    <div className="space-y-6 text-left">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#EAEAEA]">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-[#111111] tracking-tight">Calendar & Events</h1>
          <p className="text-xs text-[#666666] mt-0.5">Classes, meetings, appointments, and personal events</p>
        </div>
        <Button variant="primary" size="sm" onClick={openCreate} leftIcon={<Plus className="w-4 h-4" />}>
          Add Event
        </Button>
      </div>

      {/* Type Filter Tabs */}
      <div className="flex items-center gap-1 overflow-x-auto no-scrollbar py-1">
        {(['all', 'class', 'meeting', 'appointment', 'exam', 'deadline', 'personal', 'other'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setTypeFilter(f)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors shrink-0 ${
              typeFilter === f
                ? 'bg-black text-white'
                : 'bg-[#F7F7F7] text-[#666666] hover:bg-[#F3F3F3] hover:text-[#111111]'
            }`}
          >
            {f === 'all' ? 'All Events' : EVENT_TYPE_CONFIG[f].label}
          </button>
        ))}
      </div>

      {/* Grouped Events by Date */}
      {dates.length === 0 ? (
        <EmptyState
          title="No events yet"
          description="Add classes, meetings, appointments, and personal events."
          actionLabel="Add Event"
          onAction={openCreate}
        />
      ) : (
        <div className="space-y-6">
          {dates.map((date) => {
            const isToday = date === new Date().toISOString().split('T')[0];
            return (
              <div key={date}>
                <div className="flex items-center gap-3 mb-3">
                  <h2 className={`text-xs font-bold uppercase tracking-wider ${isToday ? 'text-black' : 'text-[#8A8A8A]'}`}>
                    {isToday ? 'Today — ' : ''}{formatDate(date)}
                  </h2>
                  <div className="flex-1 h-px bg-[#EAEAEA]" />
                </div>

                <div className="space-y-2">
                  {grouped[date].map((ev) => {
                    const cfg = EVENT_TYPE_CONFIG[ev.type];
                    return (
                      <Card key={ev.id} className="hover:border-[#D0D0D0] transition-colors">
                        <div className="flex items-start justify-between gap-4">
                          {/* Time Column */}
                          <div className="shrink-0 text-right w-16 hidden sm:block">
                            <div className="text-xs font-semibold text-[#111111]">{ev.startTime}</div>
                            {ev.endTime && <div className="text-[11px] text-[#8A8A8A]">{ev.endTime}</div>}
                          </div>

                          {/* Vertical divider */}
                          <div className="hidden sm:block w-px self-stretch bg-[#EAEAEA]" />

                          {/* Content */}
                          <div className="flex-1 min-w-0 space-y-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${cfg.color}`}>
                                {cfg.label}
                              </span>
                              <h3 className="text-xs sm:text-sm font-semibold text-[#111111]">{ev.title}</h3>
                            </div>
                            {ev.description && <p className="text-xs text-[#666666]">{ev.description}</p>}
                            <div className="flex items-center gap-3 text-[11px] text-[#8A8A8A]">
                              <span className="flex items-center gap-1 sm:hidden">
                                <Clock className="w-3 h-3" />{ev.startTime}{ev.endTime ? ` – ${ev.endTime}` : ''}
                              </span>
                              {ev.location && (
                                <span className="flex items-center gap-1">
                                  {ev.location.startsWith('http') ? <Video className="w-3 h-3" /> : <MapPin className="w-3 h-3" />}
                                  {ev.location}
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="flex items-center gap-1 shrink-0">
                            <Button variant="ghost" size="sm" onClick={() => openEdit(ev)} className="p-1.5 text-[#8A8A8A] hover:text-[#111111]">
                              <Edit3 className="w-3.5 h-3.5" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => setDeletingId(ev.id)} className="p-1.5 text-[#8A8A8A] hover:text-red-600">
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingEvent ? 'Edit Event' : 'Add Event'}
        maxWidth="md"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button variant="primary" size="sm" onClick={handleSubmit} isLoading={create.isPending || update.isPending}>
              {editingEvent ? 'Save Changes' : 'Add Event'}
            </Button>
          </>
        }
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Event Title" placeholder="e.g. ML Lecture, Project Meeting..." value={title} onChange={(e) => setTitle(e.target.value)} required />
          <Textarea label="Description (Optional)" placeholder="Details..." value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
          <Select
            label="Event Type" value={type}
            onChange={(e) => setType(e.target.value as EventType)}
            options={Object.entries(EVENT_TYPE_CONFIG).map(([v, c]) => ({ value: v, label: c.label }))}
          />
          <Input label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Start Time" type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} required />
            <Input label="End Time" type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
          </div>
          <Input label="Location / Link (Optional)" placeholder="Room 304 or https://meet.google.com/..." value={location} onChange={(e) => setLocation(e.target.value)} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deletingId} onClose={() => setDeletingId(null)}
        onConfirm={async () => { if (deletingId) { await remove.mutateAsync(deletingId); setDeletingId(null); } }}
        title="Delete Event" message="Are you sure you want to delete this event?"
      />
    </div>
  );
};
