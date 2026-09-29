import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Pencil, PiggyBank, Plus, Sparkles, Trash2 } from 'lucide-react';
import { useBudgets } from '../hooks/useBudgets';
import type { Budget, BudgetStatus, ExpenseCategory } from '../types';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge, type BadgeVariant } from '../components/ui/Badge';
import { Card, Panel } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { StatCard } from '../components/ui/StatCard';
import { StatGrid } from '../components/ui/ResponsiveList';
import { Progress } from '../components/ui/Progress';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { RowActions } from '../components/ui/RowActions';
import { formatCurrency, todayISO } from '../utils/formatters';

const CATEGORIES: ExpenseCategory[] = ['food', 'travel', 'education', 'shopping', 'bills', 'entertainment', 'health', 'other'];
const OVERALL = 'overall';

const categoryLabel = (c: ExpenseCategory | null) => (c ? c.charAt(0).toUpperCase() + c.slice(1) : 'Overall');

const STATUS: Record<BudgetStatus, { label: string; badge: BadgeVariant; tone: 'accent' | 'warning' | 'danger' }> = {
  on_track: { label: 'On track', badge: 'success', tone: 'accent' },
  warning: { label: 'Near limit', badge: 'warning', tone: 'warning' },
  over: { label: 'Over budget', badge: 'error', tone: 'danger' },
};

function monthLabel(month: string) {
  const [y, m] = month.split('-').map(Number);
  return new Intl.DateTimeFormat('en-IN', { month: 'long', year: 'numeric' }).format(new Date(y, m - 1, 1));
}

const BudgetRow: React.FC<{ budget: Budget; onEdit: () => void; onDelete: () => void }> = ({ budget, onEdit, onDelete }) => {
  const s = STATUS[budget.status];
  const overBy = budget.spent - budget.amount;
  return (
    <div className="px-5 py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-fg">{categoryLabel(budget.category)}</p>
            <Badge variant={s.badge} dot>
              {s.label}
            </Badge>
          </div>
          <p className="text-xs text-fg-subtle mt-0.5">
            {budget.category ? 'Category budget' : 'All spending'} · alert at {budget.alertThreshold}%
          </p>
        </div>
        <RowActions
          label={`Actions for ${categoryLabel(budget.category)} budget`}
          items={[
            { id: 'edit', label: 'Edit limit', icon: <Pencil />, onClick: onEdit },
            { id: 'delete', label: 'Delete', icon: <Trash2 />, destructive: true, onClick: onDelete },
          ]}
        />
      </div>
      <div className="flex items-baseline justify-between gap-3 mt-3 mb-1.5 text-sm">
        <span className="tabular text-fg">
          {formatCurrency(budget.spent)} <span className="text-fg-faint">of {formatCurrency(budget.amount)}</span>
        </span>
        <span className="tabular text-fg-muted">{budget.percentUsed}%</span>
      </div>
      <Progress value={budget.percentUsed} tone={s.tone} size="md" label={`${categoryLabel(budget.category)} budget used`} />
      <p className="mt-1.5 text-xs text-fg-subtle">
        {overBy > 0 ? (
          <span className="text-danger">{formatCurrency(overBy)} over the limit</span>
        ) : (
          `${formatCurrency(budget.remaining)} left`
        )}
      </p>
    </div>
  );
};

export const BudgetsPage: React.FC = () => {
  const currentMonth = todayISO().slice(0, 7);
  const [month, setMonth] = useState(currentMonth);
  const { data: budgets = [], isLoading, create, update, remove } = useBudgets(month === currentMonth ? undefined : month);

  const [editing, setEditing] = useState<Budget | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [deleting, setDeleting] = useState<Budget | null>(null);
  const [category, setCategory] = useState<string>(OVERALL);
  const [amount, setAmount] = useState('');
  const [threshold, setThreshold] = useState('80');

  const used = new Set<string>(budgets.map((b) => b.category ?? OVERALL));
  const available: string[] = [OVERALL, ...CATEGORIES].filter((c) => !used.has(c));

  const openCreate = () => {
    setEditing(null);
    setCategory(available[0] ?? OVERALL);
    setAmount('');
    setThreshold('80');
    setIsModalOpen(true);
  };

  const openEdit = (b: Budget) => {
    setEditing(b);
    setCategory(b.category ?? OVERALL);
    setAmount(String(b.amount));
    setThreshold(String(b.alertThreshold));
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = parseFloat(amount);
    const alertThreshold = Math.max(1, Math.min(100, parseInt(threshold, 10) || 80));
    if (!(value > 0)) return;
    try {
      if (editing) {
        await update.mutateAsync({ id: editing.id, data: { amount: value, alertThreshold } });
      } else {
        const cat = category === OVERALL ? null : (category as ExpenseCategory);
        await create.mutateAsync({ category: cat, amount: value, alertThreshold });
      }
      setIsModalOpen(false);
    } catch {
      // the hook shows the error; keep the form open
    }
  };

  const overall = budgets.find((b) => b.category === null);
  const categoryBudgets = budgets.filter((b) => b.category !== null);
  const totalLimit = overall?.amount ?? categoryBudgets.reduce((s, b) => s + b.amount, 0);
  const totalSpent = overall?.spent ?? categoryBudgets.reduce((s, b) => s + b.spent, 0);
  const needsAttention = budgets.filter((b) => b.status !== 'on_track');

  return (
    <Page>
      <PageHeader
        title="Budgets"
        description="Monthly spending limits, tracked against the expenses you log."
        actions={
          <div className="flex items-center gap-2">
            <Input
              aria-label="Month"
              type="month"
              value={month}
              max={currentMonth}
              onChange={(e) => setMonth(e.target.value || currentMonth)}
              className="w-40"
            />
            <Button onClick={openCreate} disabled={available.length === 0} leftIcon={<Plus className="size-4" />}>
              New budget
            </Button>
          </div>
        }
      />

      <StatGrid cols={3}>
        <StatCard
          label={overall ? 'Monthly limit' : 'Total of category limits'}
          value={formatCurrency(totalLimit)}
          hint={monthLabel(month)}
        />
        <StatCard
          label="Spent"
          value={formatCurrency(totalSpent)}
          hint={totalLimit ? `${Math.round((totalSpent / totalLimit) * 100)}% of the limit` : 'No limit set'}
          tone={totalLimit && totalSpent > totalLimit ? 'danger' : 'default'}
        />
        <StatCard
          label="Need attention"
          value={needsAttention.length}
          hint={needsAttention.length ? needsAttention.map((b) => categoryLabel(b.category)).join(', ') : 'Everything on track'}
          tone={needsAttention.some((b) => b.status === 'over') ? 'danger' : needsAttention.length ? 'warning' : 'success'}
        />
      </StatGrid>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 sm:gap-6 items-start">
        <Card flush className="xl:col-span-2 overflow-hidden">
          {isLoading ? (
            <p className="px-5 py-6 text-sm text-fg-subtle">Loading budgets…</p>
          ) : budgets.length === 0 ? (
            <EmptyState
              bare
              icon={<PiggyBank />}
              title="No budgets yet"
              description="Set a monthly limit for all spending or for a category like food or travel."
              actionLabel="New budget"
              onAction={openCreate}
            />
          ) : (
            <div className="divide-y divide-line">
              {budgets.map((b) => (
                <BudgetRow key={b.id} budget={b} onEdit={() => openEdit(b)} onDelete={() => setDeleting(b)} />
              ))}
            </div>
          )}
        </Card>

        <Panel title="Ask the assistant" description="Budgets work in chat too" bodyClassName="px-5 py-4 space-y-3">
          <p className="text-sm text-fg-muted">
            The assistant can check your budgets and draft new limits. Nothing changes until you approve it.
          </p>
          <ul className="space-y-1.5 text-sm text-fg">
            <li>“How are my budgets looking?”</li>
            <li>“Set my food budget to 3000”</li>
          </ul>
          <Link to="/chat" className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent-hover">
            <Sparkles className="size-4" />
            Open Assistant
          </Link>
        </Panel>
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editing ? `Edit ${categoryLabel(editing.category).toLowerCase()} budget` : 'New budget'}
        maxWidth="sm"
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" form="budget-form" isLoading={create.isPending || update.isPending}>
              Save budget
            </Button>
          </>
        }
      >
        <form id="budget-form" onSubmit={handleSubmit} className="space-y-4">
          <Select
            label="Applies to"
            value={category}
            disabled={!!editing}
            onChange={(e) => setCategory(e.target.value)}
            options={(editing ? [category] : available).map((c) => ({
              value: c,
              label: c === OVERALL ? 'All spending (overall)' : categoryLabel(c as ExpenseCategory),
            }))}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Monthly limit (₹)"
              type="number"
              min="1"
              step="any"
              placeholder="0"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
              autoFocus
            />
            <Input
              label="Alert at (%)"
              type="number"
              min="1"
              max="100"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              helperText="Marks the budget as near its limit"
            />
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          if (deleting) {
            await remove.mutateAsync(deleting.id);
            setDeleting(null);
          }
        }}
        title="Delete budget?"
        message={deleting ? `The ${categoryLabel(deleting.category).toLowerCase()} budget will be removed. Your expenses are kept.` : ''}
      />
    </Page>
  );
};
