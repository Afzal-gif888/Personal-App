import React, { useState } from 'react';
import { Plus, Pencil, Trash2, Target } from 'lucide-react';
import { useGoals } from '../hooks/useGoals';
import type { Goal, GoalCategory, GoalStatus } from '../types';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Tabs } from '../components/ui/Tabs';
import { StatCard } from '../components/ui/StatCard';
import { StatGrid } from '../components/ui/ResponsiveList';
import { Progress } from '../components/ui/Progress';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { RowActions } from '../components/ui/RowActions';
import { Toolbar, FilterSelect } from '../components/ui/Toolbar';
import { formatDate, daysUntil } from '../utils/formatters';
import { CATEGORY_LABELS, GOAL_STATUS_STYLES, statusStyle } from '../utils/status';

const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ value, label }));

export const GoalsPage: React.FC = () => {
  const { data: goals = [], create, update, remove } = useGoals();

  const [statusFilter, setStatusFilter] = useState<GoalStatus | 'all'>('active');
  const [categoryFilter, setCategoryFilter] = useState<GoalCategory | 'all'>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingGoal, setEditingGoal] = useState<Goal | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [category, setCategory] = useState<GoalCategory>('academic');
  const [target, setTarget] = useState('');
  const [progress, setProgress] = useState('0');
  const [deadline, setDeadline] = useState('');
  const [status, setStatus] = useState<GoalStatus>('active');

  const openCreate = () => {
    setEditingGoal(null);
    setTitle('');
    setCategory('academic');
    setTarget('');
    setProgress('0');
    setDeadline('');
    setStatus('active');
    setIsModalOpen(true);
  };

  const openEdit = (g: Goal) => {
    setEditingGoal(g);
    setTitle(g.title);
    setCategory(g.category);
    setTarget(g.target);
    setProgress(String(g.progress));
    setDeadline(g.deadline || '');
    setStatus(g.status);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !target.trim()) return;
    const pct = Math.max(0, Math.min(100, parseInt(progress, 10) || 0));
    const data = { title, category, target, progress: pct, deadline: deadline || undefined, status };
    if (editingGoal) await update.mutateAsync({ id: editingGoal.id, data });
    else await create.mutateAsync(data);
    setIsModalOpen(false);
  };

  const filtered = goals.filter(
    (g) => (statusFilter === 'all' || g.status === statusFilter) && (categoryFilter === 'all' || g.category === categoryFilter)
  );

  const active = goals.filter((g) => g.status === 'active');
  const completedCount = goals.filter((g) => g.status === 'completed').length;
  const avgProgress = active.length ? Math.round(active.reduce((s, g) => s + g.progress, 0) / active.length) : 0;

  return (
    <Page>
      <PageHeader
        title="Goals"
        description="Longer-term objectives across academics, career, finances and personal growth."
        actions={
          <Button onClick={openCreate} leftIcon={<Plus className="size-4" />}>
            New goal
          </Button>
        }
      />

      <StatGrid cols={3}>
        <StatCard label="Active goals" value={active.length} hint="In progress" />
        <StatCard label="Average progress" value={`${avgProgress}%`} hint="Across active goals" />
        <StatCard label="Completed" value={completedCount} hint="All time" tone="success" />
      </StatGrid>

      <Toolbar>
        <Tabs
          variant="pills"
          activeTab={statusFilter}
          onChange={(id) => setStatusFilter(id as GoalStatus | 'all')}
          tabs={[
            { id: 'active', label: 'Active', badge: active.length },
            { id: 'on_hold', label: 'On hold', badge: goals.filter((g) => g.status === 'on_hold').length },
            { id: 'completed', label: 'Completed', badge: completedCount },
            { id: 'all', label: 'All', badge: goals.length },
          ]}
        />
        <FilterSelect
          label="Category"
          value={categoryFilter}
          onChange={(v) => setCategoryFilter(v as GoalCategory | 'all')}
          options={[{ value: 'all', label: 'All categories' }, ...CATEGORY_OPTIONS]}
        />
      </Toolbar>

      {filtered.length === 0 ? (
        <EmptyState icon={<Target />} title="No goals here" description="Set a goal to start tracking progress." actionLabel="New goal" onAction={openCreate} />
      ) : (
        <Card flush className="overflow-hidden">
          <ul className="divide-y divide-line">
            {filtered.map((goal) => {
              const s = statusStyle(GOAL_STATUS_STYLES, goal.status);
              const days = goal.deadline ? daysUntil(goal.deadline) : null;
              return (
                <li key={goal.id} className="flex flex-col md:flex-row md:items-center gap-3 md:gap-6 px-5 py-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-medium text-fg">{goal.title}</p>
                      <Badge variant={s.variant}>{s.label}</Badge>
                    </div>
                    <p className="text-xs text-fg-subtle mt-0.5">
                      {CATEGORY_LABELS[goal.category]} · Target: {goal.target}
                      {goal.deadline && (
                        <>
                          {' · '}
                          <span className={days !== null && days < 0 && goal.status !== 'completed' ? 'text-danger' : undefined}>
                            Due {formatDate(goal.deadline)}
                          </span>
                        </>
                      )}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 md:w-72 shrink-0">
                    <Progress value={goal.progress} tone={goal.status === 'completed' ? 'success' : 'accent'} label={`${goal.title} progress`} />
                    <span className="w-10 text-right text-sm font-medium text-fg tabular">{goal.progress}%</span>
                    <RowActions
                      label={`Actions for ${goal.title}`}
                      items={[
                        { id: 'edit', label: 'Edit / update progress', icon: <Pencil />, onClick: () => openEdit(goal) },
                        {
                          id: 'delete',
                          label: 'Delete',
                          icon: <Trash2 />,
                          destructive: true,
                          separated: true,
                          onClick: () => setDeletingId(goal.id),
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
        title={editingGoal ? 'Edit goal' : 'New goal'}
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" form="goal-form" isLoading={create.isPending || update.isPending}>
              {editingGoal ? 'Save changes' : 'Create goal'}
            </Button>
          </>
        }
      >
        <form id="goal-form" onSubmit={handleSubmit} className="space-y-4">
          <Input label="Goal" placeholder="e.g. Score 90% in Machine Learning" value={title} onChange={(e) => setTitle(e.target.value)} required autoFocus />
          <Input
            label="Target"
            placeholder="e.g. 90%, ₹20,000, 10 applications"
            helperText="What does success look like?"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            required
          />
          <div className="grid grid-cols-2 gap-4">
            <Select label="Category" value={category} onChange={(e) => setCategory(e.target.value as GoalCategory)} options={CATEGORY_OPTIONS} />
            <Select
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value as GoalStatus)}
              options={[
                { value: 'active', label: 'Active' },
                { value: 'on_hold', label: 'On hold' },
                { value: 'completed', label: 'Completed' },
              ]}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Progress (%)" type="number" min="0" max="100" value={progress} onChange={(e) => setProgress(e.target.value)} />
            <Input label="Deadline" type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
          </div>
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
        title="Delete goal?"
        message="This goal and its progress will be removed."
      />
    </Page>
  );
};
