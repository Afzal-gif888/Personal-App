import React, { useState } from 'react';
import { Plus, Trash2, Wallet } from 'lucide-react';
import { useExpenses } from '../hooks/useExpenses';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Textarea } from '../components/ui/Textarea';
import { Card, Panel } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { StatCard } from '../components/ui/StatCard';
import { StatGrid, DesktopOnly, MobileList, MobileRow } from '../components/ui/ResponsiveList';
import { Progress } from '../components/ui/Progress';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { RowActions } from '../components/ui/RowActions';
import { Table, THead, TBody, TR, TH, TD } from '../components/ui/Table';
import { Toolbar, SearchField, FilterSelect, TableFooter } from '../components/ui/Toolbar';
import { formatCurrency, formatDate, todayISO } from '../utils/formatters';

const EXPENSE_CATEGORIES = ['Food', 'Travel', 'Shopping', 'Education', 'Bills', 'Entertainment', 'Health', 'Other'];

export const ExpensesPage: React.FC = () => {
  const { data: expenses = [], create, remove } = useExpenses();

  const [categoryFilter, setCategoryFilter] = useState('All');
  const [search, setSearch] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState('Food');
  const [date, setDate] = useState(todayISO());
  const [description, setDescription] = useState('');

  const openCreate = () => {
    setTitle('');
    setAmount('');
    setCategory('Food');
    setDate(todayISO());
    setDescription('');
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !amount) return;
    await create.mutateAsync({ title, amount: parseFloat(amount), category, date, description });
    setIsModalOpen(false);
  };

  const month = todayISO().slice(0, 7);
  const thisMonth = expenses.filter((e) => e.date.startsWith(month));
  const totalThisMonth = thisMonth.reduce((s, e) => s + e.amount, 0);
  const dayOfMonth = new Date().getDate();
  const byCategory = EXPENSE_CATEGORIES.map((cat) => ({
    cat,
    amount: thisMonth.filter((e) => e.category === cat).reduce((s, e) => s + e.amount, 0),
  }))
    .filter((c) => c.amount > 0)
    .sort((a, b) => b.amount - a.amount);

  const q = search.trim().toLowerCase();
  const filtered = expenses
    .filter((e) => (categoryFilter === 'All' || e.category === categoryFilter) && (!q || e.title.toLowerCase().includes(q)))
    .sort((a, b) => b.date.localeCompare(a.date));

  return (
    <Page>
      <PageHeader
        title="Expenses"
        description="Day-to-day spending, grouped by category."
        actions={
          <Button onClick={openCreate} leftIcon={<Plus className="size-4" />}>
            Log expense
          </Button>
        }
      />

      <StatGrid cols={3}>
        <StatCard label="Spent this month" value={formatCurrency(totalThisMonth)} hint={`${thisMonth.length} transactions`} />
        <StatCard label="Daily average" value={formatCurrency(Math.round(totalThisMonth / Math.max(dayOfMonth, 1)))} hint="This month" />
        <StatCard
          label="Top category"
          value={byCategory[0]?.cat ?? '—'}
          hint={byCategory[0] ? formatCurrency(byCategory[0].amount) : 'No spending yet'}
        />
      </StatGrid>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 sm:gap-6 items-start">
        <div className="xl:col-span-2 space-y-4">
          <Toolbar>
            <SearchField value={search} onChange={setSearch} placeholder="Search expenses" />
            <FilterSelect
              label="Category"
              value={categoryFilter}
              onChange={setCategoryFilter}
              options={[{ value: 'All', label: 'All categories' }, ...EXPENSE_CATEGORIES.map((c) => ({ value: c, label: c }))]}
            />
          </Toolbar>

          <Card flush className="overflow-hidden">
            {filtered.length === 0 ? (
              <EmptyState bare icon={<Wallet />} title="No expenses" description="Log an expense to start tracking." actionLabel="Log expense" onAction={openCreate} />
            ) : (
              <>
                <MobileList>
                  {filtered.map((exp) => (
                    <MobileRow
                      key={exp.id}
                      title={exp.title}
                      aside={<span className="font-semibold text-fg tabular">{formatCurrency(exp.amount)}</span>}
                      subtitle={`${exp.category} · ${formatDate(exp.date)}${exp.description ? ` · ${exp.description}` : ''}`}
                      actions={
                        <RowActions
                          label={`Actions for ${exp.title}`}
                          items={[{ id: 'delete', label: 'Delete', icon: <Trash2 />, destructive: true, onClick: () => setDeletingId(exp.id) }]}
                        />
                      }
                    />
                  ))}
                </MobileList>
                <DesktopOnly>
                <Table>
                  <THead>
                    <tr>
                      <TH>Description</TH>
                      <TH className="hidden sm:table-cell">Category</TH>
                      <TH className="hidden md:table-cell">Date</TH>
                      <TH className="text-right">Amount</TH>
                      <TH className="w-12">
                        <span className="sr-only">Actions</span>
                      </TH>
                    </tr>
                  </THead>
                  <TBody>
                    {filtered.map((exp) => (
                      <TR key={exp.id}>
                        <TD className="w-full max-w-0">
                          <p className="font-medium truncate">{exp.title}</p>
                          <p className="text-xs text-fg-subtle truncate mt-0.5 md:hidden">
                            {exp.category} · {formatDate(exp.date)}
                          </p>
                          {exp.description && <p className="hidden md:block text-xs text-fg-subtle truncate mt-0.5">{exp.description}</p>}
                        </TD>
                        <TD className="hidden sm:table-cell text-fg-muted">{exp.category}</TD>
                        <TD className="hidden md:table-cell text-fg-muted whitespace-nowrap">{formatDate(exp.date)}</TD>
                        <TD className="text-right font-medium tabular whitespace-nowrap">{formatCurrency(exp.amount)}</TD>
                        <TD>
                          <RowActions
                            label={`Actions for ${exp.title}`}
                            items={[{ id: 'delete', label: 'Delete', icon: <Trash2 />, destructive: true, onClick: () => setDeletingId(exp.id) }]}
                          />
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
                </DesktopOnly>
                <TableFooter shown={filtered.length} total={expenses.length} noun="expenses" />
              </>
            )}
          </Card>
        </div>

        <Panel title="By category" description="This month" bodyClassName="px-5 py-4 space-y-4">
          {byCategory.length === 0 ? (
            <p className="text-sm text-fg-subtle">No spending recorded this month.</p>
          ) : (
            byCategory.map(({ cat, amount: amt }) => {
              const pct = totalThisMonth ? (amt / totalThisMonth) * 100 : 0;
              return (
                <div key={cat}>
                  <div className="flex items-center justify-between text-sm mb-1.5">
                    <span className="text-fg">{cat}</span>
                    <span className="tabular text-fg-muted">
                      {formatCurrency(amt)} <span className="text-fg-faint">· {Math.round(pct)}%</span>
                    </span>
                  </div>
                  <Progress value={pct} label={`${cat} share of spending`} />
                </div>
              );
            })
          )}
        </Panel>
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Log expense"
        maxWidth="sm"
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" form="expense-form" isLoading={create.isPending}>
              Save expense
            </Button>
          </>
        }
      >
        <form id="expense-form" onSubmit={handleSubmit} className="space-y-4">
          <Input label="Description" placeholder="e.g. Groceries" value={title} onChange={(e) => setTitle(e.target.value)} required autoFocus />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Amount (₹)" type="number" min="0" placeholder="0" value={amount} onChange={(e) => setAmount(e.target.value)} required />
            <Input label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          </div>
          <Select label="Category" value={category} onChange={(e) => setCategory(e.target.value)} options={EXPENSE_CATEGORIES.map((c) => ({ value: c, label: c }))} />
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
        title="Delete expense?"
        message="This expense will be permanently removed."
      />
    </Page>
  );
};
