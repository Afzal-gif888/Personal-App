import React, { useState } from 'react';
import { Plus, Trash2, TrendingUp } from 'lucide-react';
import { useExpenses } from '../hooks/useExpenses';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { EmptyState } from '../components/ui/EmptyState';
import { Textarea } from '../components/ui/Textarea';

const EXPENSE_CATEGORIES = ['Food', 'Travel', 'Shopping', 'Education', 'Bills', 'Entertainment', 'Health', 'Other'];

const CATEGORY_COLORS: Record<string, string> = {
  Food: 'bg-amber-50 text-amber-700',
  Travel: 'bg-blue-50 text-blue-700',
  Shopping: 'bg-purple-50 text-purple-700',
  Education: 'bg-emerald-50 text-emerald-700',
  Bills: 'bg-red-50 text-red-700',
  Entertainment: 'bg-pink-50 text-pink-700',
  Health: 'bg-teal-50 text-teal-700',
  Other: 'bg-[#F7F7F7] text-[#666666]',
};

export const ExpensesPage: React.FC = () => {
  const { data: expenses = [], create, remove } = useExpenses();

  const [categoryFilter, setCategoryFilter] = useState<string>('All');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Form
  const [title, setTitle] = useState('');
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState('Food');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [description, setDescription] = useState('');

  const resetForm = () => { setTitle(''); setAmount(''); setCategory('Food'); setDate(new Date().toISOString().split('T')[0]); setDescription(''); };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !amount) return;
    await create.mutateAsync({ title, amount: parseFloat(amount), category, date, description });
    resetForm();
    setIsModalOpen(false);
  };

  const filtered = categoryFilter === 'All' ? expenses : expenses.filter((e) => e.category === categoryFilter);

  // Summary: spending by category this month
  const thisMonth = expenses.filter((e) => e.date.startsWith(new Date().toISOString().slice(0, 7)));
  const totalThisMonth = thisMonth.reduce((s, e) => s + e.amount, 0);
  const byCategory = EXPENSE_CATEGORIES.reduce((acc, cat) => {
    acc[cat] = thisMonth.filter((e) => e.category === cat).reduce((s, e) => s + e.amount, 0);
    return acc;
  }, {} as Record<string, number>);
  const topCategories = Object.entries(byCategory).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]).slice(0, 4);

  return (
    <div className="space-y-6 text-left">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#EAEAEA]">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-[#111111] tracking-tight">Expenses</h1>
          <p className="text-xs text-[#666666] mt-0.5">Track daily spending across all categories</p>
        </div>
        <Button variant="primary" size="sm" onClick={() => setIsModalOpen(true)} leftIcon={<Plus className="w-4 h-4" />}>
          Add Expense
        </Button>
      </div>

      {/* Summary Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <Card className="bg-[#F7F7F7] border-0 col-span-2 sm:col-span-1">
          <div className="text-[11px] text-[#8A8A8A] font-medium">This Month</div>
          <div className="text-lg font-bold text-[#111111] mt-1">₹{totalThisMonth.toLocaleString()}</div>
        </Card>
        {topCategories.slice(0, 2).map(([cat, amt]) => (
          <Card key={cat} className="bg-[#F7F7F7] border-0">
            <div className="text-[11px] text-[#8A8A8A] font-medium">{cat}</div>
            <div className="text-base font-bold text-[#111111] mt-1">₹{amt.toLocaleString()}</div>
          </Card>
        ))}
      </div>

      {/* Spending by Category */}
      {topCategories.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <TrendingUp className="w-4 h-4" />
              This Month's Spending
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {topCategories.map(([cat, amt]) => {
                const pct = totalThisMonth > 0 ? (amt / totalThisMonth) * 100 : 0;
                return (
                  <div key={cat} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-[#666666]">{cat}</span>
                      <span className="font-semibold text-[#111111]">₹{amt.toLocaleString()}</span>
                    </div>
                    <div className="h-1.5 bg-[#F7F7F7] rounded-full overflow-hidden">
                      <div className="h-full bg-black rounded-full transition-all" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Category Filters */}
      <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
        {['All', ...EXPENSE_CATEGORIES].map((cat) => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors shrink-0 ${
              categoryFilter === cat ? 'bg-black text-white' : 'bg-[#F7F7F7] text-[#666666] hover:bg-[#F3F3F3] hover:text-[#111111]'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Expense List */}
      {filtered.length === 0 ? (
        <EmptyState title="No expenses" description="Add your first expense to start tracking spending." actionLabel="Add Expense" onAction={() => setIsModalOpen(true)} />
      ) : (
        <div className="space-y-2">
          {[...filtered].sort((a, b) => b.date.localeCompare(a.date)).map((exp) => (
            <Card key={exp.id} className="hover:border-[#D0D0D0] transition-colors">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${CATEGORY_COLORS[exp.category] || 'bg-[#F7F7F7] text-[#666666]'}`}>
                    {exp.category.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs sm:text-sm font-semibold text-[#111111] truncate">{exp.title}</div>
                    <div className="text-[11px] text-[#8A8A8A]">{exp.category} · {exp.date}</div>
                    {exp.description && <div className="text-[11px] text-[#8A8A8A] truncate">{exp.description}</div>}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-sm font-bold text-[#111111]">₹{exp.amount.toLocaleString()}</span>
                  <Button variant="ghost" size="sm" onClick={() => remove.mutateAsync(exp.id)} className="p-1.5 text-[#8A8A8A] hover:text-red-600">
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Add Expense Modal */}
      <Modal
        isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Add Expense" maxWidth="sm"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button variant="primary" size="sm" onClick={handleSubmit} isLoading={create.isPending}>Add Expense</Button>
          </>
        }
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Title" placeholder="e.g. Groceries, Uber, Coffee..." value={title} onChange={(e) => setTitle(e.target.value)} required />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Amount (₹)" type="number" placeholder="0" value={amount} onChange={(e) => setAmount(e.target.value)} required />
            <Input label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          </div>
          <Select
            label="Category" value={category} onChange={(e) => setCategory(e.target.value)}
            options={EXPENSE_CATEGORIES.map((c) => ({ value: c, label: c }))}
          />
          <Textarea label="Note (Optional)" placeholder="Details..." value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
        </form>
      </Modal>
    </div>
  );
};
