import React, { useState } from 'react';
import { Plus, Sparkles, Clock, CheckCircle2, Trash2, Edit3 } from 'lucide-react';
import { useStudyPlan } from '../hooks/useStudyPlan';
import type { StudySession, Priority } from '../types';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { EmptyState } from '../components/ui/EmptyState';
import { getPriorityBadgeColor, formatDate } from '../utils/formatters';

export const StudyPlanPage: React.FC = () => {
  const {
    sessions,
    createSession,
    updateSession,
    toggleComplete,
    deleteSession,
    generateAIPlan,
    isGeneratingAI,
  } = useStudyPlan();

  const [viewMode, setViewMode] = useState<'day' | 'week'>('day');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSession, setEditingSession] = useState<StudySession | null>(null);

  // Form states
  const [subject, setSubject] = useState('Machine Learning');
  const [topic, setTopic] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [startTime, setStartTime] = useState('18:00');
  const [endTime, setEndTime] = useState('19:15');
  const [priority, setPriority] = useState<Priority>('high');
  const [notes, setNotes] = useState('');

  const openCreateModal = () => {
    setEditingSession(null);
    setSubject('Machine Learning');
    setTopic('');
    setDate(new Date().toISOString().split('T')[0]);
    setStartTime('18:00');
    setEndTime('19:15');
    setPriority('high');
    setNotes('');
    setIsModalOpen(true);
  };

  const openEditModal = (session: StudySession) => {
    setEditingSession(session);
    setSubject(session.subject);
    setTopic(session.topic);
    setDate(session.date);
    setStartTime(session.startTime);
    setEndTime(session.endTime);
    setPriority(session.priority);
    setNotes(session.notes || '');
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;

    if (editingSession) {
      await updateSession({
        id: editingSession.id,
        updates: { subject, topic, date, startTime, endTime, priority, notes },
      });
    } else {
      await createSession({
        subject,
        topic,
        date,
        startTime,
        endTime,
        priority,
        status: 'scheduled',
        notes,
      });
    }
    setIsModalOpen(false);
  };

  const handleGenerateAI = async () => {
    await generateAIPlan({ subject: 'Machine Learning', hours: 4 });
  };

  return (
    <div className="space-y-6 text-left">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#EAEAEA]">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-[#111111] tracking-tight">Study Plan</h1>
          <p className="text-xs text-[#666666] mt-0.5">Automated AI study session scheduling and daily syllabus tracking</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleGenerateAI}
            isLoading={isGeneratingAI}
            leftIcon={<Sparkles className="w-3.5 h-3.5 text-emerald-600" />}
          >
            Generate with AI
          </Button>
          <Button variant="primary" size="sm" onClick={openCreateModal} leftIcon={<Plus className="w-4 h-4" />}>
            Add Session
          </Button>
        </div>
      </div>

      {/* View Switcher Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1 bg-[#F7F7F7] p-1 rounded-md border border-[#EAEAEA]">
          <button
            onClick={() => setViewMode('day')}
            className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
              viewMode === 'day' ? 'bg-black text-white' : 'text-[#666666] hover:text-[#111111]'
            }`}
          >
            Day View
          </button>
          <button
            onClick={() => setViewMode('week')}
            className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
              viewMode === 'week' ? 'bg-black text-white' : 'text-[#666666] hover:text-[#111111]'
            }`}
          >
            Week View
          </button>
        </div>
        <span className="text-xs text-[#666666] font-medium">
          {sessions.length} Scheduled Sessions
        </span>
      </div>

      {/* Session Cards Grid */}
      {sessions.length === 0 ? (
        <EmptyState
          title="No study sessions scheduled"
          description="Click 'Generate with AI' or manually create a session to organize your daily syllabus goals."
          actionLabel="Generate with AI"
          onAction={handleGenerateAI}
        />
      ) : (
        <div className="space-y-4">
          <div className="font-semibold text-xs text-[#8A8A8A] uppercase tracking-wider">
            {formatDate(new Date().toISOString())}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sessions.map((s) => (
              <Card
                key={s.id}
                className={`space-y-3 transition-all ${
                  s.status === 'completed' ? 'bg-[#F7F7F7]/60 border-[#EAEAEA]' : 'bg-white'
                }`}
              >
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1.5 font-mono text-[#666666]">
                    <Clock className="w-3.5 h-3.5 text-[#8A8A8A]" />
                    <span>
                      {s.startTime} - {s.endTime}
                    </span>
                  </div>
                  <Badge className={getPriorityBadgeColor(s.priority)} size="sm">
                    {s.priority}
                  </Badge>
                </div>

                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-black">
                    {s.subject}
                  </span>
                  <h3
                    className={`text-sm font-semibold text-[#111111] leading-snug ${
                      s.status === 'completed' ? 'line-through text-[#666666]' : ''
                    }`}
                  >
                    {s.topic}
                  </h3>
                </div>

                {s.notes && (
                  <p className="text-xs text-[#666666] bg-[#F7F7F7] p-2 rounded border border-[#EAEAEA] leading-relaxed">
                    {s.notes}
                  </p>
                )}

                <div className="flex items-center justify-between pt-2 border-t border-[#EAEAEA]">
                  <Button
                    variant={s.status === 'completed' ? 'outline' : 'secondary'}
                    size="sm"
                    onClick={() => toggleComplete(s.id)}
                    className="text-xs px-2.5 h-7"
                    leftIcon={
                      s.status === 'completed' ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : undefined
                    }
                  >
                    {s.status === 'completed' ? 'Completed' : 'Mark Completed'}
                  </Button>

                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditModal(s)}
                      className="p-1 text-[#8A8A8A] hover:text-[#111111]"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteSession(s.id)}
                      className="p-1 text-[#8A8A8A] hover:text-red-600"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Modal Dialog */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingSession ? 'Edit Study Session' : 'Create Study Session'}
        maxWidth="md"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleFormSubmit}>
              {editingSession ? 'Save Session' : 'Add Session'}
            </Button>
          </>
        }
      >
        <form onSubmit={handleFormSubmit} className="space-y-4">
          <Select
            label="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            options={[
              { value: 'Machine Learning', label: 'Machine Learning (CS 229)' },
              { value: 'Database Systems', label: 'Database Systems (CS 145)' },
              { value: 'Operating Systems', label: 'Operating Systems (CS 140)' },
              { value: 'Algorithm Analysis', label: 'Algorithm Analysis (CS 161)' },
            ]}
          />

          <Input
            label="Topic / Focus Area"
            placeholder="e.g. Convex Optimization & Loss Minimization"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Input
              label="Date"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
            />
            <Input
              label="Start Time"
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              required
            />
            <Input
              label="End Time"
              type="time"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              required
            />
          </div>

          <Select
            label="Priority Level"
            value={priority}
            onChange={(e) => setPriority(e.target.value as Priority)}
            options={[
              { value: 'high', label: 'High Priority' },
              { value: 'medium', label: 'Medium Priority' },
              { value: 'low', label: 'Low Priority' },
            ]}
          />

          <Textarea
            label="Notes / Instructions (Optional)"
            placeholder="Formula derivation proofs, specific textbook pages..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
          />
        </form>
      </Modal>
    </div>
  );
};
