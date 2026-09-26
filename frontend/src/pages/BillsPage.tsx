import React, { useState } from 'react';
import { Plus, Trash2, CheckCircle, AlertCircle, Clock, CreditCard, RefreshCw } from 'lucide-react';
import { useBills } from '../hooks/useBills';
import { usePaymentPlans } from '../hooks/usePaymentPlans';
import type { BillStatus } from '../types';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { EmptyState } from '../components/ui/EmptyState';
import { Tabs } from '../components/ui/Tabs';
import { formatDate } from '../utils/formatters';

const STATUS_CONFIG: Record<BillStatus, { label: string; color: string; icon: React.ReactNode }> = {
  upcoming: { label: 'Upcoming', color: 'bg-blue-50 text-blue-700 border border-blue-100', icon: <Clock className="w-3 h-3" /> },
  due: { label: 'Due Today', color: 'bg-amber-50 text-amber-700 border border-amber-100', icon: <AlertCircle className="w-3 h-3" /> },
  overdue: { label: 'Overdue', color: 'bg-red-50 text-red-700 border border-red-100', icon: <AlertCircle className="w-3 h-3" /> },
  paid: { label: 'Paid', color: 'bg-emerald-50 text-emerald-700 border border-emerald-100', icon: <CheckCircle className="w-3 h-3" /> },
};

export const BillsPage: React.FC = () => {
  const { data: bills = [], create, markPaid, remove } = useBills();
  const { data: plans = [], recordPayment, remove: removePlan } = usePaymentPlans();

  const [activeTab, setActiveTab] = useState('bills');
  const [statusFilter, setStatusFilter] = useState<BillStatus | 'all'>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Bill form
  const [billTitle, setBillTitle] = useState('');
  const [amount, setAmount] = useState('');
  const [dueDate, setDueDate] = useState(new Date().toISOString().split('T')[0]);
  const [category, setCategory] = useState('utilities');
  const [isRecurring, setIsRecurring] = useState(false);
  const [frequency, setFrequency] = useState('monthly');
  const [paymentMethod, setPaymentMethod] = useState('');
  const [notes, setNotes] = useState('');

  const resetForm = () => {
    setBillTitle(''); setAmount(''); setDueDate(new Date().toISOString().split('T')[0]);
    setCategory('utilities'); setIsRecurring(false); setFrequency('monthly');
    setPaymentMethod(''); setNotes('');
  };

  const handleBillSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!billTitle.trim() || !amount) return;
    await create.mutateAsync({
      title: billTitle, amount: parseFloat(amount), dueDate, category,
      status: 'upcoming', isRecurring, frequency: isRecurring ? frequency : undefined,
      paymentMethod, notes,
    });
    resetForm();
    setIsModalOpen(false);
  };

  const filteredBills = bills.filter((b) => statusFilter === 'all' || b.status === statusFilter);

  // Summary stats
  const unpaid = bills.filter((b) => b.status !== 'paid');
  const totalUnpaid = unpaid.reduce((s, b) => s + b.amount, 0);
  const overdue = bills.filter((b) => b.status === 'overdue').length;

  return (
    <div className="space-y-6 text-left">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#EAEAEA]">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-[#111111] tracking-tight">Bills & Payments</h1>
          <p className="text-xs text-[#666666] mt-0.5">Track bills, subscriptions, and payment plans</p>
        </div>
        {activeTab === 'bills' && (
          <Button variant="primary" size="sm" onClick={() => setIsModalOpen(true)} leftIcon={<Plus className="w-4 h-4" />}>
            Add Bill
          </Button>
        )}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <Card className="bg-[#F7F7F7] border-0">
          <div className="text-[11px] text-[#8A8A8A] font-medium">Total Unpaid</div>
          <div className="text-lg font-bold text-[#111111] mt-1">₹{totalUnpaid.toLocaleString()}</div>
        </Card>
        <Card className={`border-0 ${overdue > 0 ? 'bg-red-50' : 'bg-[#F7F7F7]'}`}>
          <div className={`text-[11px] font-medium ${overdue > 0 ? 'text-red-600' : 'text-[#8A8A8A]'}`}>Overdue</div>
          <div className={`text-lg font-bold mt-1 ${overdue > 0 ? 'text-red-700' : 'text-[#111111]'}`}>{overdue}</div>
        </Card>
        <Card className="bg-[#F7F7F7] border-0 col-span-2 sm:col-span-1">
          <div className="text-[11px] text-[#8A8A8A] font-medium">Active Plans</div>
          <div className="text-lg font-bold text-[#111111] mt-1">{plans.filter((p) => p.status === 'active').length}</div>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs
        activeTab={activeTab}
        onChange={setActiveTab}
        tabs={[
          { id: 'bills', label: 'Bills & Subscriptions' },
          { id: 'plans', label: 'Payment Plans' },
        ]}
      />

      {activeTab === 'bills' && (
        <>
          {/* Status Filter */}
          <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
            {(['all', 'upcoming', 'due', 'overdue', 'paid'] as const).map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors shrink-0 ${
                  statusFilter === s ? 'bg-black text-white' : 'bg-[#F7F7F7] text-[#666666] hover:bg-[#F3F3F3] hover:text-[#111111]'
                }`}
              >
                {s === 'all' ? 'All' : STATUS_CONFIG[s].label}
              </button>
            ))}
          </div>

          {filteredBills.length === 0 ? (
            <EmptyState title="No bills" description="Add bills to track upcoming payments." actionLabel="Add Bill" onAction={() => setIsModalOpen(true)} />
          ) : (
            <div className="space-y-2">
              {filteredBills.map((bill) => {
                const cfg = STATUS_CONFIG[bill.status];
                return (
                  <Card key={bill.id} className="hover:border-[#D0D0D0] transition-colors">
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex-1 min-w-0 space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full ${cfg.color}`}>
                            {cfg.icon}{cfg.label}
                          </span>
                          {bill.isRecurring && (
                            <span className="inline-flex items-center gap-1 text-[10px] text-[#8A8A8A]">
                              <RefreshCw className="w-2.5 h-2.5" />{bill.frequency}
                            </span>
                          )}
                          <h3 className="text-xs sm:text-sm font-semibold text-[#111111]">{bill.title}</h3>
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-[#8A8A8A]">
                          <span className="font-bold text-[#111111] text-sm">₹{bill.amount.toLocaleString()}</span>
                          <span>•</span>
                          <span>Due {formatDate(bill.dueDate)}</span>
                          {bill.paymentMethod && <><span>•</span><span className="flex items-center gap-1"><CreditCard className="w-3 h-3" />{bill.paymentMethod}</span></>}
                        </div>
                        {bill.notes && <p className="text-[11px] text-[#8A8A8A]">{bill.notes}</p>}
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {bill.status !== 'paid' && (
                          <Button variant="outline" size="sm" onClick={() => markPaid.mutateAsync(bill.id)} className="text-[11px] px-2 py-1">
                            Mark Paid
                          </Button>
                        )}
                        <Button variant="ghost" size="sm" onClick={() => remove.mutateAsync(bill.id)} className="p-1.5 text-[#8A8A8A] hover:text-red-600">
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </>
      )}

      {activeTab === 'plans' && (
        <div className="space-y-3">
          {plans.length === 0 ? (
            <EmptyState title="No payment plans" description="Add installment or recurring payment plans to track here." />
          ) : (
            plans.map((plan) => {
              const progress = (plan.completedInstallments / plan.totalInstallments) * 100;
              return (
                <Card key={plan.id}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0 space-y-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-xs sm:text-sm font-semibold text-[#111111]">{plan.title}</h3>
                        <Badge className={plan.status === 'completed' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : 'bg-blue-50 text-blue-700 border border-blue-100'} size="sm">
                          {plan.status === 'completed' ? 'Completed' : 'Active'}
                        </Badge>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
                        <div>
                          <div className="text-[#8A8A8A]">Total Amount</div>
                          <div className="font-semibold text-[#111111]">₹{plan.totalAmount.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-[#8A8A8A]">Installment</div>
                          <div className="font-semibold text-[#111111]">₹{plan.installmentAmount.toLocaleString()} / {plan.frequency}</div>
                        </div>
                        <div>
                          <div className="text-[#8A8A8A]">Remaining</div>
                          <div className="font-semibold text-[#111111]">₹{plan.remainingAmount.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-[#8A8A8A]">Next Due</div>
                          <div className="font-semibold text-[#111111]">{formatDate(plan.nextPaymentDate)}</div>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="space-y-1">
                        <div className="flex justify-between text-[11px] text-[#8A8A8A]">
                          <span>{plan.completedInstallments} of {plan.totalInstallments} installments paid</span>
                          <span>{Math.round(progress)}%</span>
                        </div>
                        <div className="h-1.5 bg-[#F7F7F7] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-black rounded-full transition-all"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col gap-1 shrink-0">
                      {plan.status === 'active' && (
                        <Button variant="outline" size="sm" onClick={() => recordPayment.mutateAsync(plan.id)} className="text-[11px]">
                          Record Payment
                        </Button>
                      )}
                      <Button variant="ghost" size="sm" onClick={() => removePlan.mutateAsync(plan.id)} className="p-1.5 text-[#8A8A8A] hover:text-red-600">
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })
          )}
        </div>
      )}

      {/* Add Bill Modal */}
      <Modal
        isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Add Bill" maxWidth="md"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button variant="primary" size="sm" onClick={handleBillSubmit} isLoading={create.isPending}>Add Bill</Button>
          </>
        }
      >
        <form onSubmit={handleBillSubmit} className="space-y-4">
          <Input label="Bill Name" placeholder="e.g. Electricity Bill, Netflix..." value={billTitle} onChange={(e) => setBillTitle(e.target.value)} required />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Amount (₹)" type="number" placeholder="0.00" value={amount} onChange={(e) => setAmount(e.target.value)} required />
            <Input label="Due Date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Category" value={category} onChange={(e) => setCategory(e.target.value)}
              options={[
                { value: 'utilities', label: 'Utilities' },
                { value: 'entertainment', label: 'Entertainment' },
                { value: 'education', label: 'Education' },
                { value: 'rent', label: 'Rent / Hostel' },
                { value: 'phone', label: 'Phone' },
                { value: 'internet', label: 'Internet' },
                { value: 'other', label: 'Other' },
              ]}
            />
            <Input label="Payment Method" placeholder="UPI, Credit Card..." value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)} />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="recurring" checked={isRecurring} onChange={(e) => setIsRecurring(e.target.checked)} className="rounded" />
            <label htmlFor="recurring" className="text-xs text-[#666666]">Recurring bill</label>
          </div>
          {isRecurring && (
            <Select
              label="Frequency" value={frequency} onChange={(e) => setFrequency(e.target.value)}
              options={[
                { value: 'monthly', label: 'Monthly' },
                { value: 'quarterly', label: 'Quarterly' },
                { value: 'yearly', label: 'Yearly' },
              ]}
            />
          )}
          <Input label="Notes (Optional)" placeholder="Any additional details..." value={notes} onChange={(e) => setNotes(e.target.value)} />
        </form>
      </Modal>
    </div>
  );
};
