import React, { useState } from 'react';
import { Plus, Trash2, Edit3, Target, TrendingUp } from 'lucide-react';
import { useGoals } from '../hooks/useGoals';
import type { Goal, GoalCategory, GoalStatus } from '../types';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { formatDate } from '../utils/formatters';

const CATEGORY_CONFIG: Record<GoalCategory, { label: string; color: string }> = {
  academic: { label: 'Academic', color: 'bg-blue-50 text-blue-700 border border-blue-100' },
  financial: { label: 'Financial', color: 'bg-emerald-50 text-emerald-700 border border-emerald-100' },
  career: { label: 'Career', color: 'bg-amber-50 text-amber-700 border border-amber-100' },
  personal: { label: 'Personal', color: 'bg-purple-50 text-purple-700 border border-purple-100' },
  general: { label: 'General', color: 'bg-[#F7F7F7] text-[#666666] border border-[#EAEAEA]' },
};

export const GoalsPage: React.FC = () => {
  const { data: goals = [], create, update, remove } = useGoals();

  const [categoryFilter, setCategoryFilter] = useState<GoalCategory | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<GoalStatus | 'all'>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingGoal, setEditingGoal] = useState<Goal | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [updatingProgressId, setUpdatingProgressId] = useState<string | null>(null);
  const [newProgress, setNewProgress] = useState('');

  // Form
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState<GoalCategory>('academic');
  const [target, setTarget] = useState('');
  const [progress, setProgress] = useState('0');
  const [deadline, setDeadline] = useState('');
  const [status, setStatus] = useState<GoalStatus>('active');

  const resetForm = () => { setTitle(''); setCategory('academic'); setTarget(''); setProgress('0'); setDeadline(''); setStatus('active'); };

  const openCreate = () => { setEditingGoal(null); resetForm(); setIsModalOpen(true); };

  const openEdit = (g: Goal) => {
    setEditingGoal(g); setTitle(g.title); setCategory(g.category); setTarget(g.target);
    setProgress(String(g.progress)); setDeadline(g.deadline || ''); setStatus(g.status);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !target.trim()) return;
    const data = { title, category, target, progress: parseInt(progress), deadline: deadline || undefined, status };
    if (editingGoal) {
      await update.mutateAsync({ id: editingGoal.id, data });
    } else {
      await create.mutateAsync(data);
    }
    setIsModalOpen(false);
  };

  const handleProgressUpdate = async (id: string) => {
    const val = parseInt(newProgress);
    if (isNaN(val) || val < 0 || val > 100) return;
    await update.mutateAsync({ id, data: { progress: val, status: val === 100 ? 'completed' : 'active' } });
    setUpdatingProgressId(null);
    setNewProgress('');
  };

  const filtered = goals.filter((g) => {
    if (categoryFilter !== 'all' && g.category !== categoryFilter) return false;
    if (statusFilter !== 'all' && g.status !== statusFilter) return false;
    return true;
  });

  const activeCount = goals.filter((g) => g.status === 'active').length;
  const completedCount = goals.filter((g) => g.status === 'completed').length;
  const avgProgress = goals.length > 0 ? Math.round(goals.reduce((s, g) => s + g.progress, 0) / goals.length) : 0;

  return (
    <div className="space-y-6 text-left">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#EAEAEA]">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-[#111111] tracking-tight">Goals</h1>
          <p className="text-xs text-[#666666] mt-0.5">Academic, career, financial and personal goals</p>
        </div>
        <Button variant="primary" size="sm" onClick={openCreate} leftIcon={<Plus className="w-4 h-4" />}>
          Add Goal
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <Card className="bg-[#F7F7F7] border-0">
          <div className="text-[11px] text-[#8A8A8A] font-medium">Active</div>
          <div className="text-lg font-bold text-[#111111] mt-1">{activeCount}</div>
        </Card>
        <Card className="bg-[#F7F7F7] border-0">
          <div className="text-[11px] text-[#8A8A8A] font-medium">Completed</div>
          <div className="text-lg font-bold text-emerald-600 mt-1">{completedCount}</div>
        </Card>
        <Card className="bg-[#F7F7F7] border-0">
          <div className="text-[11px] text-[#8A8A8A] font-medium">Avg Progress</div>
          <div className="text-lg font-bold text-[#111111] mt-1">{avgProgress}%</div>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
          {(['all', 'academic', 'financial', 'career', 'personal', 'general'] as const).map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors shrink-0 ${
                categoryFilter === cat ? 'bg-black text-white' : 'bg-[#F7F7F7] text-[#666666] hover:bg-[#F3F3F3] hover:text-[#111111]'
              }`}
            >
              {cat === 'all' ? 'All' : CATEGORY_CONFIG[cat].label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          {(['all', 'active', 'completed', 'on_hold'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors shrink-0 border ${
                statusFilter === s ? 'bg-[#111111] text-white border-[#111111]' : 'bg-white text-[#666666] border-[#EAEAEA] hover:border-[#111111] hover:text-[#111111]'
              }`}
            >
              {s === 'all' ? 'All Status' : s === 'on_hold' ? 'On Hold' : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Goals List */}
      {filtered.length === 0 ? (
        <EmptyState title="No goals found" description="Set a goal to start tracking your progress." actionLabel="Add Goal" onAction={openCreate} />
      ) : (
        <div className="space-y-3">
          {filtered.map((goal) => {
            const cfg = CATEGORY_CONFIG[goal.category];
            const isUpdatingThis = updatingProgressId === goal.id;
            return (
              <Card key={goal.id} className={goal.status === 'completed' ? 'opacity-70' : ''}>
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${cfg.color}`}>
                        <Target className="w-4 h-4" />
                      </div>
                      <div className="min-w-0 space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className={`text-xs sm:text-sm font-semibold text-[#111111] ${goal.status === 'completed' ? 'line-through text-[#666666]' : ''}`}>
                            {goal.title}
                          </h3>
                          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${cfg.color}`}>{cfg.label}</span>
                          {goal.status === 'completed' && (
                            <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-100" size="sm">Completed</Badge>
                          )}
                        </div>
                        <div className="text-[11px] text-[#8A8A8A] flex items-center gap-3">
                          <span className="flex items-center gap-1"><TrendingUp className="w-3 h-3" />Target: <span className="font-medium text-[#111111]">{goal.target}</span></span>
                          {goal.deadline && <span>By {formatDate(goal.deadline)}</span>}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(goal)} className="p-1.5 text-[#8A8A8A] hover:text-[#111111]">
                        <Edit3 className="w-3.5 h-3.5" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setDeletingId(goal.id)} className="p-1.5 text-[#8A8A8A] hover:text-red-600">
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center">
                      <span className="text-[11px] text-[#8A8A8A]">Progress</span>
                      <div className="flex items-center gap-2">
                        {isUpdatingThis ? (
                          <div className="flex items-center gap-1.5">
                            <input
                              type="number" min="0" max="100" placeholder="0-100"
                              value={newProgress} onChange={(e) => setNewProgress(e.target.value)}
                              className="w-16 text-xs border border-[#EAEAEA] rounded px-2 py-0.5 focus:outline-none focus:ring-1 focus:ring-black"
                            />
                            <Button variant="primary" size="sm" onClick={() => handleProgressUpdate(goal.id)} className="text-[11px] px-2 py-0.5 h-auto">
                              Set
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => setUpdatingProgressId(null)} className="text-[11px] px-1">
                              ✕
                            </Button>
                          </div>
                        ) : (
                          <button
                            onClick={() => { setUpdatingProgressId(goal.id); setNewProgress(String(goal.progress)); }}
                            className="text-[11px] font-bold text-[#111111] hover:underline"
                          >
                            {goal.progress}%
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="h-2 bg-[#F7F7F7] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${goal.status === 'completed' ? 'bg-emerald-500' : 'bg-black'}`}
                        style={{ width: `${goal.progress}%` }}
                      />
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Modal */}
      <Modal
        isOpen={isModalOpen} onClose={() => setIsModalOpen(false)}
        title={editingGoal ? 'Edit Goal' : 'Add Goal'} maxWidth="md"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button variant="primary" size="sm" onClick={handleSubmit} isLoading={create.isPending || update.isPending}>
              {editingGoal ? 'Save Changes' : 'Add Goal'}
            </Button>
          </>
        }
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Goal Title" placeholder="e.g. Score 90% in ML, Save ₹20,000..." value={title} onChange={(e) => setTitle(e.target.value)} required />
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Category" value={category} onChange={(e) => setCategory(e.target.value as GoalCategory)}
              options={Object.entries(CATEGORY_CONFIG).map(([v, c]) => ({ value: v, label: c.label }))}
            />
            <Select
              label="Status" value={status} onChange={(e) => setStatus(e.target.value as GoalStatus)}
              options={[{ value: 'active', label: 'Active' }, { value: 'on_hold', label: 'On Hold' }, { value: 'completed', label: 'Completed' }]}
            />
          </div>
          <Input label="Target (what does success look like?)" placeholder="e.g. 90%, ₹20,000, 10 applications..." value={target} onChange={(e) => setTarget(e.target.value)} required />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Current Progress (%)" type="number" min="0" max="100" value={progress} onChange={(e) => setProgress(e.target.value)} />
            <Input label="Deadline (Optional)" type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deletingId} onClose={() => setDeletingId(null)}
        onConfirm={async () => { if (deletingId) { await remove.mutateAsync(deletingId); setDeletingId(null); } }}
        title="Delete Goal" message="Are you sure you want to delete this goal?"
      />
    </div>
  );
};
