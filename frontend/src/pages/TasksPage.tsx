import React, { useState } from 'react';
import { Plus, Search, Trash2, Edit3, Calendar } from 'lucide-react';
import { useTasks } from '../hooks/useTasks';
import type { Task, Priority, TaskCategory } from '../types';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Checkbox } from '../components/ui/Checkbox';
import { Modal } from '../components/ui/Modal';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { getPriorityBadgeColor, formatDate } from '../utils/formatters';

const CATEGORY_LABELS: Record<TaskCategory, string> = {
  academic: 'Academic',
  personal: 'Personal',
  financial: 'Financial',
  career: 'Career',
  general: 'General',
};

const CATEGORY_COLORS: Record<TaskCategory, string> = {
  academic: 'bg-blue-50 text-blue-700 border border-blue-100',
  personal: 'bg-purple-50 text-purple-700 border border-purple-100',
  financial: 'bg-emerald-50 text-emerald-700 border border-emerald-100',
  career: 'bg-amber-50 text-amber-700 border border-amber-100',
  general: 'bg-[#F7F7F7] text-[#666666] border border-[#EAEAEA]',
};

export const TasksPage: React.FC = () => {
  const { tasks, createTask, isCreating, updateTask, toggleComplete, deleteTask } = useTasks();

  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<'all' | 'pending' | 'completed' | 'high' | 'duesoon'>('all');
  const [activeCategoryFilter, setActiveCategoryFilter] = useState<TaskCategory | 'all'>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [deletingTaskId, setDeletingTaskId] = useState<string | null>(null);

  // Form states
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<TaskCategory>('academic');
  const [subject, setSubject] = useState('');
  const [priority, setPriority] = useState<Priority>('medium');
  const [dueDate, setDueDate] = useState(new Date().toISOString().split('T')[0]);
  const [dueTime, setDueTime] = useState('23:59');

  const openCreateModal = () => {
    setEditingTask(null);
    setTitle('');
    setDescription('');
    setCategory('academic');
    setSubject('');
    setPriority('medium');
    setDueDate(new Date().toISOString().split('T')[0]);
    setDueTime('23:59');
    setIsModalOpen(true);
  };

  const openEditModal = (task: Task) => {
    setEditingTask(task);
    setTitle(task.title);
    setDescription(task.description || '');
    setCategory(task.category);
    setSubject(task.subject || '');
    setPriority(task.priority);
    setDueDate(task.dueDate);
    setDueTime(task.dueTime || '23:59');
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    if (editingTask) {
      await updateTask({
        id: editingTask.id,
        updates: { title, description, category, subject, priority, dueDate, dueTime },
      });
    } else {
      await createTask({
        title,
        description,
        category,
        subject,
        priority,
        dueDate,
        dueTime,
        status: 'pending',
      });
    }
    setIsModalOpen(false);
  };

  // Filter & Search Logic
  const filteredTasks = tasks.filter((t) => {
    const matchesSearch =
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.subject || '').toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;
    if (activeCategoryFilter !== 'all' && t.category !== activeCategoryFilter) return false;
    if (activeFilter === 'pending') return t.status !== 'completed';
    if (activeFilter === 'completed') return t.status === 'completed';
    if (activeFilter === 'high') return t.priority === 'high';
    if (activeFilter === 'duesoon') {
      const due = new Date(t.dueDate).getTime();
      const now = new Date().getTime();
      return due - now < 3 * 86400000 && t.status !== 'completed';
    }
    return true;
  });

  return (
    <div className="space-y-6 text-left">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#EAEAEA]">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-[#111111] tracking-tight">Tasks</h1>
          <p className="text-xs text-[#666666] mt-0.5">Academic, personal, financial and career tasks in one place</p>
        </div>
        <Button variant="primary" size="sm" onClick={openCreateModal} leftIcon={<Plus className="w-4 h-4" />}>
          Create Task
        </Button>
      </div>

      {/* Controls Bar */}
      <div className="space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="w-full md:w-72">
            <Input
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              leftIcon={<Search className="w-4 h-4" />}
            />
          </div>

          {/* Status Filter Pills */}
          <div className="flex items-center gap-1 overflow-x-auto no-scrollbar py-1">
            {(['all', 'pending', 'completed', 'high', 'duesoon'] as const).map((filter) => {
              const labels = { all: 'All', pending: 'Pending', completed: 'Done', high: 'High Priority', duesoon: 'Due Soon' };
              return (
                <button
                  key={filter}
                  onClick={() => setActiveFilter(filter)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors shrink-0 ${
                    activeFilter === filter
                      ? 'bg-black text-white font-semibold'
                      : 'bg-[#F7F7F7] text-[#666666] hover:bg-[#F3F3F3] hover:text-[#111111]'
                  }`}
                >
                  {labels[filter]}
                </button>
              );
            })}
          </div>
        </div>

        {/* Category Filter Pills */}
        <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
          {(['all', 'academic', 'personal', 'financial', 'career', 'general'] as const).map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategoryFilter(cat)}
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors shrink-0 border ${
                activeCategoryFilter === cat
                  ? 'bg-[#111111] text-white border-[#111111]'
                  : 'bg-white text-[#666666] border-[#EAEAEA] hover:border-[#111111] hover:text-[#111111]'
              }`}
            >
              {cat === 'all' ? 'All Categories' : CATEGORY_LABELS[cat]}
            </button>
          ))}
        </div>
      </div>

      {/* Task List */}
      {filteredTasks.length === 0 ? (
        <EmptyState
          title="No tasks found"
          description="Create a task to get started tracking your work across all areas of life."
          actionLabel="Create Task"
          onAction={openCreateModal}
        />
      ) : (
        <div className="space-y-3">
          {filteredTasks.map((t) => (
            <Card
              key={t.id}
              className={`transition-all ${t.status === 'completed' ? 'opacity-60 bg-[#F7F7F7]/50' : 'bg-white'}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <Checkbox checked={t.status === 'completed'} onChange={() => toggleComplete(t.id)} className="mt-1" />
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3
                        className={`text-xs sm:text-sm font-semibold text-[#111111] leading-snug ${
                          t.status === 'completed' ? 'line-through text-[#666666]' : ''
                        }`}
                      >
                        {t.title}
                      </h3>
                      <Badge className={getPriorityBadgeColor(t.priority)} size="sm">{t.priority}</Badge>
                      <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${CATEGORY_COLORS[t.category]}`}>
                        {CATEGORY_LABELS[t.category]}
                      </span>
                    </div>

                    {t.description && (
                      <p className="text-xs text-[#666666] line-clamp-2 leading-relaxed">{t.description}</p>
                    )}

                    <div className="flex items-center gap-3 pt-1 text-[11px] text-[#8A8A8A]">
                      {t.subject && <span className="font-semibold text-[#111111]">{t.subject}</span>}
                      {t.subject && <span>•</span>}
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3 text-[#8A8A8A]" />
                        Due {formatDate(t.dueDate)} {t.dueTime ? `at ${t.dueTime}` : ''}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="ghost" size="sm" onClick={() => openEditModal(t)}
                    className="p-1.5 text-[#8A8A8A] hover:text-[#111111]" title="Edit task"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </Button>
                  <Button
                    variant="ghost" size="sm" onClick={() => setDeletingTaskId(t.id)}
                    className="p-1.5 text-[#8A8A8A] hover:text-red-600" title="Delete task"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Create / Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingTask ? 'Edit Task' : 'Create New Task'}
        maxWidth="md"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button variant="primary" size="sm" onClick={handleFormSubmit} isLoading={isCreating}>
              {editingTask ? 'Save Changes' : 'Create Task'}
            </Button>
          </>
        }
      >
        <form onSubmit={handleFormSubmit} className="space-y-4">
          <Input
            label="Task Title"
            placeholder="e.g. Buy groceries, Pay electricity bill, ML Problem Set..."
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />

          <Textarea
            label="Description (Optional)"
            placeholder="Additional details..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select
              label="Category"
              value={category}
              onChange={(e) => setCategory(e.target.value as TaskCategory)}
              options={[
                { value: 'academic', label: 'Academic' },
                { value: 'personal', label: 'Personal' },
                { value: 'financial', label: 'Financial' },
                { value: 'career', label: 'Career' },
                { value: 'general', label: 'General' },
              ]}
            />

            <Select
              label="Priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value as Priority)}
              options={[
                { value: 'high', label: 'High Priority' },
                { value: 'medium', label: 'Medium Priority' },
                { value: 'low', label: 'Low Priority' },
              ]}
            />
          </div>

          {category === 'academic' && (
            <Input
              label="Subject / Course"
              placeholder="e.g. Machine Learning, Database Systems..."
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Due Date"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              required
            />
            <Input
              label="Due Time"
              type="time"
              value={dueTime}
              onChange={(e) => setDueTime(e.target.value)}
            />
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deletingTaskId}
        onClose={() => setDeletingTaskId(null)}
        onConfirm={async () => {
          if (deletingTaskId) { await deleteTask(deletingTaskId); setDeletingTaskId(null); }
        }}
        title="Delete Task"
        message="Are you sure you want to delete this task? This action cannot be undone."
      />
    </div>
  );
};
