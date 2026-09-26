import React, { useState } from 'react';
import { Plus, Bell, Trash2, Edit3, RotateCw } from 'lucide-react';
import { useReminders } from '../hooks/useReminders';
import type { Reminder, ReminderRepeat } from '../types';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Tabs } from '../components/ui/Tabs';
import { Modal } from '../components/ui/Modal';
import { EmptyState } from '../components/ui/EmptyState';
import { formatDate } from '../utils/formatters';

export const RemindersPage: React.FC = () => {
  const {
    reminders,
    createReminder,
    updateReminder,
    toggleComplete,
    snoozeReminder,
    deleteReminder,
  } = useReminders();

  const [activeTab, setActiveTab] = useState<'today' | 'upcoming' | 'completed'>('today');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingReminder, setEditingReminder] = useState<Reminder | null>(null);

  // Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [time, setTime] = useState('19:00');
  const [repeat, setRepeat] = useState<ReminderRepeat>('none');

  const openCreateModal = () => {
    setEditingReminder(null);
    setTitle('');
    setDescription('');
    setDate(new Date().toISOString().split('T')[0]);
    setTime('19:00');
    setRepeat('none');
    setIsModalOpen(true);
  };

  const openEditModal = (r: Reminder) => {
    setEditingReminder(r);
    setTitle(r.title);
    setDescription(r.description || '');
    setDate(r.date);
    setTime(r.time);
    setRepeat(r.repeat);
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    if (editingReminder) {
      await updateReminder({
        id: editingReminder.id,
        updates: { title, description, date, time, repeat },
      });
    } else {
      await createReminder({
        title,
        description,
        date,
        time,
        repeat,
        status: 'upcoming',
      });
    }
    setIsModalOpen(false);
  };

  // Tab filtering
  const filteredReminders = reminders.filter((r) => {
    if (activeTab === 'today') return r.status === 'today' || (r.status === 'upcoming' && r.date === new Date().toISOString().split('T')[0]);
    if (activeTab === 'upcoming') return r.status === 'upcoming' || r.status === 'snoozed';
    if (activeTab === 'completed') return r.status === 'completed';
    return true;
  });

  const tabItems = [
    { id: 'today', label: 'Today', badge: reminders.filter((r) => r.status === 'today').length },
    { id: 'upcoming', label: 'Upcoming', badge: reminders.filter((r) => r.status === 'upcoming' || r.status === 'snoozed').length },
    { id: 'completed', label: 'Completed', badge: reminders.filter((r) => r.status === 'completed').length },
  ];

  return (
    <div className="space-y-6 text-left">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#EAEAEA]">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-[#111111] tracking-tight">Reminders</h1>
          <p className="text-xs text-[#666666] mt-0.5">Bills, appointments, assignments, personal reminders, and more</p>
        </div>
        <Button variant="primary" size="sm" onClick={openCreateModal} leftIcon={<Plus className="w-4 h-4" />}>
          Create Reminder
        </Button>
      </div>

      {/* Tabs Switcher */}
      <Tabs tabs={tabItems} activeTab={activeTab} onChange={(id) => setActiveTab(id as any)} variant="underline" />

      {/* Reminders List */}
      {filteredReminders.length === 0 ? (
        <EmptyState
          icon={<Bell className="w-8 h-8 text-[#8A8A8A]" />}
          title={`No ${activeTab} reminders`}
          description="You don't have any reminders scheduled in this view."
          actionLabel="Create Reminder"
          onAction={openCreateModal}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredReminders.map((r) => (
            <Card
              key={r.id}
              className={`space-y-3 transition-all ${
                r.status === 'completed' ? 'opacity-60 bg-[#F7F7F7]/60' : 'bg-white'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-md bg-[#F7F7F7] border border-[#EAEAEA]">
                    <Bell className="w-4 h-4 text-amber-600" />
                  </div>
                  <div>
                    <h3 className="text-xs sm:text-sm font-semibold text-[#111111] leading-snug">{r.title}</h3>
                    <p className="text-[11px] font-mono text-[#666666] mt-0.5">
                      {formatDate(r.date)} at {r.time}
                    </p>
                  </div>
                </div>

                <Badge
                  variant={
                    r.status === 'completed'
                      ? 'success'
                      : r.status === 'snoozed'
                      ? 'warning'
                      : 'neutral'
                  }
                  size="sm"
                >
                  {r.status}
                </Badge>
              </div>

              {r.description && <p className="text-xs text-[#666666] leading-relaxed">{r.description}</p>}

              {r.repeat !== 'none' && (
                <div className="inline-flex items-center gap-1 text-[10px] text-[#8A8A8A] bg-[#F7F7F7] px-2 py-0.5 rounded border border-[#EAEAEA]">
                  <RotateCw className="w-3 h-3" />
                  <span>Repeats {r.repeat}</span>
                </div>
              )}

              <div className="flex items-center justify-between pt-3 border-t border-[#EAEAEA]">
                {r.status !== 'completed' ? (
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleComplete(r.id)}
                      className="text-xs h-7 px-2.5"
                    >
                      Complete
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => snoozeReminder({ id: r.id })}
                      className="text-xs h-7 px-2.5"
                    >
                      Snooze
                    </Button>
                  </div>
                ) : (
                  <span className="text-[11px] text-emerald-700 font-medium">✓ Completed</span>
                )}

                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openEditModal(r)}
                    className="p-1 text-[#8A8A8A] hover:text-[#111111]"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteReminder(r.id)}
                    className="p-1 text-[#8A8A8A] hover:text-red-600"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Modal Form */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingReminder ? 'Edit Reminder' : 'Create Reminder'}
        maxWidth="md"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleFormSubmit}>
              {editingReminder ? 'Save Reminder' : 'Create Reminder'}
            </Button>
          </>
        }
      >
        <form onSubmit={handleFormSubmit} className="space-y-4">
          <Input
            label="Reminder Title"
            placeholder="e.g. ML Revision Session"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />

          <Textarea
            label="Description (Optional)"
            placeholder="Details, chapters to review, group links..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Date"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
            />
            <Input
              label="Time"
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              required
            />
          </div>

          <Select
            label="Repeat Interval"
            value={repeat}
            onChange={(e) => setRepeat(e.target.value as ReminderRepeat)}
            options={[
              { value: 'none', label: 'Does not repeat' },
              { value: 'daily', label: 'Every day' },
              { value: 'weekly', label: 'Every week' },
              { value: 'monthly', label: 'Every month' },
            ]}
          />
        </form>
      </Modal>
    </div>
  );
};
