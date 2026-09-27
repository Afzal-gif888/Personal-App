import React, { useState } from 'react';
import { Plus, Sparkles, Pencil, Trash2, BookOpen, Check, RotateCcw } from 'lucide-react';
import { useStudyPlan } from '../hooks/useStudyPlan';
import type { StudySession, Priority } from '../types';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Tabs } from '../components/ui/Tabs';
import { StatCard } from '../components/ui/StatCard';
import { StatGrid } from '../components/ui/ResponsiveList';
import { EmptyState } from '../components/ui/EmptyState';
import { RowActions } from '../components/ui/RowActions';
import { formatDayLabel, formatTime, todayISO } from '../utils/formatters';
import { PRIORITY_STYLES, SESSION_STATUS_STYLES, statusStyle } from '../utils/status';
import { cn } from '../utils/cn';

const SUBJECTS = [
  { value: 'Machine Learning', label: 'Machine Learning (CS 229)' },
  { value: 'Database Systems', label: 'Database Systems (CS 145)' },
  { value: 'Operating Systems', label: 'Operating Systems (CS 140)' },
  { value: 'Algorithm Analysis', label: 'Algorithm Analysis (CS 161)' },
];

function sessionHours(s: StudySession): number {
  const [sh, sm] = s.startTime.split(':').map(Number);
  const [eh, em] = s.endTime.split(':').map(Number);
  return Math.max(0, (eh * 60 + em - (sh * 60 + sm)) / 60);
}

type View = 'upcoming' | 'completed' | 'all';

export const StudyPlanPage: React.FC = () => {
  const { sessions, createSession, updateSession, toggleComplete, deleteSession, generateAIPlan, isGeneratingAI } =
    useStudyPlan();

  const [view, setView] = useState<View>('upcoming');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSession, setEditingSession] = useState<StudySession | null>(null);

  const [subject, setSubject] = useState(SUBJECTS[0].value);
  const [topic, setTopic] = useState('');
  const [date, setDate] = useState(todayISO());
  const [startTime, setStartTime] = useState('18:00');
  const [endTime, setEndTime] = useState('19:15');
  const [priority, setPriority] = useState<Priority>('high');
  const [notes, setNotes] = useState('');

  const openCreateModal = () => {
    setEditingSession(null);
    setSubject(SUBJECTS[0].value);
    setTopic('');
    setDate(todayISO());
    setStartTime('18:00');
    setEndTime('19:15');
    setPriority('high');
    setNotes('');
    setIsModalOpen(true);
  };

  const openEditModal = (s: StudySession) => {
    setEditingSession(s);
    setSubject(s.subject);
    setTopic(s.topic);
    setDate(s.date);
    setStartTime(s.startTime);
    setEndTime(s.endTime);
    setPriority(s.priority);
    setNotes(s.notes || '');
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    const payload = { subject, topic, date, startTime, endTime, priority, notes };
    if (editingSession) {
      await updateSession({ id: editingSession.id, updates: payload });
    } else {
      await createSession({ ...payload, status: 'scheduled' });
    }
    setIsModalOpen(false);
  };

  const handleGenerateAI = () => generateAIPlan({ subject: 'Machine Learning', hours: 4 });

  const scheduled = sessions.filter((s) => s.status === 'scheduled');
  const completed = sessions.filter((s) => s.status === 'completed');
  const plannedHours = scheduled.reduce((sum, s) => sum + sessionHours(s), 0);
  const completedHours = completed.reduce((sum, s) => sum + sessionHours(s), 0);

  const visible = sessions
    .filter((s) => (view === 'upcoming' ? s.status === 'scheduled' : view === 'completed' ? s.status === 'completed' : true))
    .sort((a, b) => (a.date + a.startTime).localeCompare(b.date + b.startTime));

  const byDate = visible.reduce<Record<string, StudySession[]>>((acc, s) => {
    (acc[s.date] ||= []).push(s);
    return acc;
  }, {});

  return (
    <Page>
      <PageHeader
        title="Study plan"
        description="Revision sessions you've scheduled or approved from the assistant."
        actions={
          <>
            <Button
              variant="secondary"
              onClick={handleGenerateAI}
              isLoading={isGeneratingAI}
              leftIcon={<Sparkles className="size-4" />}
            >
              Generate plan
            </Button>
            <Button onClick={openCreateModal} leftIcon={<Plus className="size-4" />}>
              Add session
            </Button>
          </>
        }
      />

      <StatGrid cols={3}>
        <StatCard label="Upcoming sessions" value={scheduled.length} hint={`${plannedHours.toFixed(1)} hours planned`} />
        <StatCard label="Completed" value={completed.length} hint={`${completedHours.toFixed(1)} hours studied`} tone="success" />
        <StatCard
          label="Completion rate"
          value={sessions.length ? `${Math.round((completed.length / sessions.length) * 100)}%` : '—'}
          hint="Across all sessions"
        />
      </StatGrid>

      <Tabs
        variant="pills"
        activeTab={view}
        onChange={(id) => setView(id as View)}
        tabs={[
          { id: 'upcoming', label: 'Upcoming', badge: scheduled.length },
          { id: 'completed', label: 'Completed', badge: completed.length },
          { id: 'all', label: 'All', badge: sessions.length },
        ]}
      />

      {visible.length === 0 ? (
        <EmptyState
          icon={<BookOpen />}
          title={view === 'completed' ? 'No completed sessions yet' : 'No sessions scheduled'}
          description="Add a session manually, or generate a plan and approve it."
          actionLabel="Add session"
          onAction={openCreateModal}
        />
      ) : (
        <Card flush className="overflow-hidden">
          {Object.entries(byDate).map(([day, list]) => (
            <section key={day} className="border-b border-line last:border-b-0">
              <header className="flex items-center justify-between px-5 h-9 bg-subtle/70 border-b border-line">
                <span className="text-xs font-medium text-fg-muted">{formatDayLabel(day)}</span>
                <span className="text-xs text-fg-faint tabular">
                  {list.reduce((sum, s) => sum + sessionHours(s), 0).toFixed(1)} h
                </span>
              </header>
              <ul className="divide-y divide-line">
                {list.map((s) => {
                  const p = statusStyle(PRIORITY_STYLES, s.priority);
                  const st = statusStyle(SESSION_STATUS_STYLES, s.status);
                  const done = s.status === 'completed';
                  return (
                    <li key={s.id} className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 px-5 py-3.5">
                      <div className="sm:w-36 shrink-0 text-sm text-fg-muted tabular">
                        {formatTime(s.startTime)} – {formatTime(s.endTime)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-fg-subtle">{s.subject}</p>
                        <p className={cn('text-sm font-medium truncate', done ? 'text-fg-subtle line-through' : 'text-fg')}>
                          {s.topic}
                        </p>
                        {s.notes && <p className="text-xs text-fg-subtle mt-0.5 line-clamp-1">{s.notes}</p>}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant={p.variant} dot>
                          {p.label}
                        </Badge>
                        <Badge variant={st.variant}>{st.label}</Badge>
                        <Button
                          variant="secondary"
                          size="xs"
                          onClick={() => toggleComplete(s.id)}
                          leftIcon={done ? <RotateCcw className="size-3.5" /> : <Check className="size-3.5" />}
                        >
                          {done ? 'Reopen' : 'Complete'}
                        </Button>
                        <RowActions
                          label={`Actions for ${s.topic}`}
                          items={[
                            { id: 'edit', label: 'Edit', icon: <Pencil />, onClick: () => openEditModal(s) },
                            {
                              id: 'delete',
                              label: 'Delete',
                              icon: <Trash2 />,
                              destructive: true,
                              separated: true,
                              onClick: () => deleteSession(s.id),
                            },
                          ]}
                        />
                      </div>
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
        title={editingSession ? 'Edit session' : 'New study session'}
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" form="session-form">
              {editingSession ? 'Save changes' : 'Add session'}
            </Button>
          </>
        }
      >
        <form id="session-form" onSubmit={handleFormSubmit} className="space-y-4">
          <Select label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} options={SUBJECTS} />
          <Input
            label="Topic"
            placeholder="e.g. Convex optimisation"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            required
            autoFocus
          />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Input label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
            <Input label="Start" type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} required />
            <Input label="End" type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} required />
          </div>
          <Select
            label="Priority"
            value={priority}
            onChange={(e) => setPriority(e.target.value as Priority)}
            options={[
              { value: 'high', label: 'High' },
              { value: 'medium', label: 'Medium' },
              { value: 'low', label: 'Low' },
            ]}
          />
          <Textarea
            label="Notes"
            placeholder="Chapters, problem sets, links"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
          />
        </form>
      </Modal>
    </Page>
  );
};
