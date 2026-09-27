import React, { useState } from 'react';
import { Plus, Trash2, Receipt, Repeat, Check, CreditCard } from 'lucide-react';
import { useBills } from '../hooks/useBills';
import { usePaymentPlans } from '../hooks/usePaymentPlans';
import type { BillStatus } from '../types';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Checkbox } from '../components/ui/Checkbox';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Tabs } from '../components/ui/Tabs';
import { StatCard } from '../components/ui/StatCard';
import { Progress } from '../components/ui/Progress';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { RowActions } from '../components/ui/RowActions';
import { Table, THead, TBody, TR, TH, TD } from '../components/ui/Table';
import { Toolbar } from '../components/ui/Toolbar';
import { DesktopOnly, MobileList, MobileRow, StatGrid } from '../components/ui/ResponsiveList';
import { formatCurrency, formatDayLabel, formatDate, daysUntil, todayISO, capitalize } from '../utils/formatters';
import { BILL_STATUS_STYLES, statusStyle } from '../utils/status';

const BILL_CATEGORIES = [
  { value: 'utilities', label: 'Utilities' },
  { value: 'rent', label: 'Rent / hostel' },
  { value: 'internet', label: 'Internet' },
  { value: 'phone', label: 'Phone' },
  { value: 'education', label: 'Education' },
  { value: 'entertainment', label: 'Entertainment' },
  { value: 'other', label: 'Other' },
];

export const BillsPage: React.FC = () => {
  const { data: bills = [], create, markPaid, remove } = useBills();
  const { data: plans = [], recordPayment, remove: removePlan } = usePaymentPlans();

  const [activeTab, setActiveTab] = useState<'bills' | 'plans'>('bills');
  const [statusFilter, setStatusFilter] = useState<BillStatus | 'unpaid' | 'all'>('unpaid');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [deleting, setDeleting] = useState<{ kind: 'bill' | 'plan'; id: string } | null>(null);

  const [billTitle, setBillTitle] = useState('');
  const [amount, setAmount] = useState('');
  const [dueDate, setDueDate] = useState(todayISO());
  const [category, setCategory] = useState('utilities');
  const [isRecurring, setIsRecurring] = useState(false);
  const [frequency, setFrequency] = useState('monthly');
  const [paymentMethod, setPaymentMethod] = useState('');
  const [notes, setNotes] = useState('');

  const openCreate = () => {
    setBillTitle('');
    setAmount('');
    setDueDate(todayISO());
    setCategory('utilities');
    setIsRecurring(false);
    setFrequency('monthly');
    setPaymentMethod('');
    setNotes('');
    setIsModalOpen(true);
  };

  const handleBillSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!billTitle.trim() || !amount) return;
    await create.mutateAsync({
      title: billTitle,
      amount: parseFloat(amount),
      dueDate,
      category,
      status: 'upcoming',
      isRecurring,
      frequency: isRecurring ? frequency : undefined,
      paymentMethod,
      notes,
    });
    setIsModalOpen(false);
  };

  const unpaid = bills.filter((b) => b.status !== 'paid');
  const outstanding = unpaid.reduce((s, b) => s + b.amount, 0);
  const overdue = bills.filter((b) => b.status === 'overdue');
  const dueThisWeek = unpaid.filter((b) => daysUntil(b.dueDate) <= 7);
  const activePlans = plans.filter((p) => p.status === 'active');

  const filteredBills = bills
    .filter((b) => (statusFilter === 'all' ? true : statusFilter === 'unpaid' ? b.status !== 'paid' : b.status === statusFilter))
    .sort((a, b) => a.dueDate.localeCompare(b.dueDate));

  return (
    <Page>
      <PageHeader
        title="Bills & payments"
        description="Upcoming bills, subscriptions and instalment plans."
        actions={
          activeTab === 'bills' && (
            <Button onClick={openCreate} leftIcon={<Plus className="size-4" />}>
              New bill
            </Button>
          )
        }
      />

      <StatGrid>
        <StatCard label="Outstanding" value={formatCurrency(outstanding)} hint={`${unpaid.length} unpaid bills`} />
        <StatCard
          label="Overdue"
          value={overdue.length}
          hint={overdue.length ? formatCurrency(overdue.reduce((s, b) => s + b.amount, 0)) : 'Nothing overdue'}
          tone={overdue.length ? 'danger' : 'default'}
        />
        <StatCard label="Due in 7 days" value={dueThisWeek.length} hint={formatCurrency(dueThisWeek.reduce((s, b) => s + b.amount, 0))} />
        <StatCard label="Active plans" value={activePlans.length} hint={formatCurrency(activePlans.reduce((s, p) => s + p.remainingAmount, 0)) + ' remaining'} />
      </StatGrid>

      <Tabs
        activeTab={activeTab}
        onChange={(id) => setActiveTab(id as 'bills' | 'plans')}
        tabs={[
          { id: 'bills', label: 'Bills', badge: bills.length },
          { id: 'plans', label: 'Payment plans', badge: plans.length },
        ]}
      />

      {activeTab === 'bills' ? (
        <>
          <Toolbar>
            <Tabs
              variant="pills"
              activeTab={statusFilter}
              onChange={(id) => setStatusFilter(id as BillStatus | 'unpaid' | 'all')}
              tabs={[
                { id: 'unpaid', label: 'Unpaid', badge: unpaid.length },
                { id: 'overdue', label: 'Overdue', badge: overdue.length },
                { id: 'paid', label: 'Paid', badge: bills.filter((b) => b.status === 'paid').length },
                { id: 'all', label: 'All', badge: bills.length },
              ]}
            />
          </Toolbar>

          <Card flush className="overflow-hidden">
            {filteredBills.length === 0 ? (
              <EmptyState bare icon={<Receipt />} title="No bills" description="Nothing matches this filter." actionLabel="New bill" onAction={openCreate} />
            ) : (
              <>
              <MobileList>
                {filteredBills.map((bill) => {
                  const s = statusStyle(BILL_STATUS_STYLES, bill.status);
                  return (
                    <MobileRow
                      key={bill.id}
                      title={bill.title}
                      aside={<span className="font-semibold text-fg tabular">{formatCurrency(bill.amount)}</span>}
                      subtitle={`Due ${formatDayLabel(bill.dueDate)} · ${capitalize(bill.category)}${bill.isRecurring ? ` · ${capitalize(bill.frequency || 'recurring')}` : ''}`}
                      meta={
                        <>
                          <Badge variant={s.variant} dot>
                            {s.label}
                          </Badge>
                          {bill.status !== 'paid' && (
                            <Button variant="secondary" size="xs" className="ml-auto" onClick={() => markPaid.mutateAsync(bill.id)} leftIcon={<Check className="size-3.5" />}>
                              Mark paid
                            </Button>
                          )}
                        </>
                      }
                      actions={
                        <RowActions
                          label={`Actions for ${bill.title}`}
                          items={[{ id: 'delete', label: 'Delete', icon: <Trash2 />, destructive: true, onClick: () => setDeleting({ kind: 'bill', id: bill.id }) }]}
                        />
                      }
                    />
                  );
                })}
              </MobileList>
              <DesktopOnly>
              <Table>
                <THead>
                  <tr>
                    <TH>Bill</TH>
                    <TH className="text-right">Amount</TH>
                    <TH>Due</TH>
                    <TH>Status</TH>
                    <TH className="hidden lg:table-cell">Method</TH>
                    <TH className="w-36">
                      <span className="sr-only">Actions</span>
                    </TH>
                  </tr>
                </THead>
                <TBody>
                  {filteredBills.map((bill) => {
                    const s = statusStyle(BILL_STATUS_STYLES, bill.status);
                    return (
                      <TR key={bill.id}>
                        <TD className="w-full max-w-0">
                          <p className="font-medium truncate">{bill.title}</p>
                          <p className="flex items-center gap-1.5 text-xs text-fg-subtle mt-0.5">
                            {capitalize(bill.category)}
                            {bill.isRecurring && (
                              <span className="inline-flex items-center gap-1">
                                · <Repeat className="size-3" /> {capitalize(bill.frequency || 'recurring')}
                              </span>
                            )}
                          </p>
                        </TD>
                        <TD className="text-right font-medium tabular whitespace-nowrap">{formatCurrency(bill.amount)}</TD>
                        <TD className="text-fg-muted whitespace-nowrap">{formatDayLabel(bill.dueDate)}</TD>
                        <TD>
                          <Badge variant={s.variant} dot>
                            {s.label}
                          </Badge>
                        </TD>
                        <TD className="hidden lg:table-cell text-fg-muted">
                          {bill.paymentMethod ? (
                            <span className="inline-flex items-center gap-1.5">
                              <CreditCard className="size-3.5 text-fg-faint" />
                              {bill.paymentMethod}
                            </span>
                          ) : (
                            '—'
                          )}
                        </TD>
                        <TD>
                          <div className="flex items-center justify-end gap-1">
                            {bill.status !== 'paid' && (
                              <Button variant="secondary" size="xs" onClick={() => markPaid.mutateAsync(bill.id)} leftIcon={<Check className="size-3.5" />}>
                                Mark paid
                              </Button>
                            )}
                            <RowActions
                              label={`Actions for ${bill.title}`}
                              items={[
                                {
                                  id: 'delete',
                                  label: 'Delete',
                                  icon: <Trash2 />,
                                  destructive: true,
                                  onClick: () => setDeleting({ kind: 'bill', id: bill.id }),
                                },
                              ]}
                            />
                          </div>
                        </TD>
                      </TR>
                    );
                  })}
                </TBody>
              </Table>
              </DesktopOnly>
              </>
            )}
          </Card>
        </>
      ) : (
        <Card flush className="overflow-hidden">
          {plans.length === 0 ? (
            <EmptyState bare icon={<CreditCard />} title="No payment plans" description="Instalment and EMI plans will appear here." />
          ) : (
            <>
            <MobileList>
              {plans.map((plan) => {
                const pct = (plan.completedInstallments / plan.totalInstallments) * 100;
                const done = plan.status === 'completed';
                return (
                  <MobileRow
                    key={plan.id}
                    title={plan.title}
                    aside={<span className="font-semibold text-fg tabular">{formatCurrency(plan.remainingAmount)}</span>}
                    subtitle={
                      done
                        ? 'Fully paid'
                        : `${formatCurrency(plan.installmentAmount)} / ${plan.frequency} · next ${formatDate(plan.nextPaymentDate)}`
                    }
                    meta={
                      <>
                        <div className="flex items-center gap-2 w-full">
                          <Progress value={pct} tone={done ? 'success' : 'accent'} label={`${plan.title} progress`} />
                          <span className="text-xs text-fg-subtle tabular whitespace-nowrap">
                            {plan.completedInstallments}/{plan.totalInstallments}
                          </span>
                        </div>
                        {!done && (
                          <Button variant="secondary" size="xs" className="mt-1" onClick={() => recordPayment.mutateAsync(plan.id)}>
                            Record payment
                          </Button>
                        )}
                      </>
                    }
                    actions={
                      <RowActions
                        label={`Actions for ${plan.title}`}
                        items={[{ id: 'delete', label: 'Delete', icon: <Trash2 />, destructive: true, onClick: () => setDeleting({ kind: 'plan', id: plan.id }) }]}
                      />
                    }
                  />
                );
              })}
            </MobileList>
            <DesktopOnly>
            <Table>
              <THead>
                <tr>
                  <TH>Plan</TH>
                  <TH className="hidden md:table-cell text-right">Instalment</TH>
                  <TH className="text-right">Remaining</TH>
                  <TH className="hidden sm:table-cell">Next payment</TH>
                  <TH className="w-48">Progress</TH>
                  <TH className="w-44">
                    <span className="sr-only">Actions</span>
                  </TH>
                </tr>
              </THead>
              <TBody>
                {plans.map((plan) => {
                  const pct = (plan.completedInstallments / plan.totalInstallments) * 100;
                  const done = plan.status === 'completed';
                  return (
                    <TR key={plan.id}>
                      <TD>
                        <p className="font-medium">{plan.title}</p>
                        <p className="text-xs text-fg-subtle mt-0.5">Total {formatCurrency(plan.totalAmount)}</p>
                      </TD>
                      <TD className="hidden md:table-cell text-right tabular whitespace-nowrap text-fg-muted">
                        {formatCurrency(plan.installmentAmount)} / {plan.frequency}
                      </TD>
                      <TD className="text-right font-medium tabular whitespace-nowrap">{formatCurrency(plan.remainingAmount)}</TD>
                      <TD className="hidden sm:table-cell text-fg-muted whitespace-nowrap">{done ? '—' : formatDate(plan.nextPaymentDate)}</TD>
                      <TD>
                        <div className="flex items-center gap-2">
                          <Progress value={pct} tone={done ? 'success' : 'accent'} label={`${plan.title} progress`} />
                          <span className="text-xs text-fg-subtle tabular whitespace-nowrap">
                            {plan.completedInstallments}/{plan.totalInstallments}
                          </span>
                        </div>
                      </TD>
                      <TD>
                        <div className="flex items-center justify-end gap-1">
                          {!done ? (
                            <Button variant="secondary" size="xs" onClick={() => recordPayment.mutateAsync(plan.id)}>
                              Record payment
                            </Button>
                          ) : (
                            <Badge variant="success">Completed</Badge>
                          )}
                          <RowActions
                            label={`Actions for ${plan.title}`}
                            items={[
                              {
                                id: 'delete',
                                label: 'Delete',
                                icon: <Trash2 />,
                                destructive: true,
                                onClick: () => setDeleting({ kind: 'plan', id: plan.id }),
                              },
                            ]}
                          />
                        </div>
                      </TD>
                    </TR>
                  );
                })}
              </TBody>
            </Table>
            </DesktopOnly>
            </>
          )}
        </Card>
      )}

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="New bill"
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" form="bill-form" isLoading={create.isPending}>
              Create bill
            </Button>
          </>
        }
      >
        <form id="bill-form" onSubmit={handleBillSubmit} className="space-y-4">
          <Input label="Name" placeholder="e.g. Electricity" value={billTitle} onChange={(e) => setBillTitle(e.target.value)} required autoFocus />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Amount (₹)" type="number" min="0" placeholder="0" value={amount} onChange={(e) => setAmount(e.target.value)} required />
            <Input label="Due date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label="Category" value={category} onChange={(e) => setCategory(e.target.value)} options={BILL_CATEGORIES} />
            <Input label="Payment method" placeholder="UPI, card…" value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)} />
          </div>
          <Checkbox
            label="Recurring bill"
            description="Repeats on a fixed schedule"
            checked={isRecurring}
            onChange={(e) => setIsRecurring(e.target.checked)}
          />
          {isRecurring && (
            <Select
              label="Frequency"
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              options={[
                { value: 'monthly', label: 'Monthly' },
                { value: 'quarterly', label: 'Quarterly' },
                { value: 'yearly', label: 'Yearly' },
              ]}
            />
          )}
          <Input label="Notes" placeholder="Optional" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          if (!deleting) return;
          if (deleting.kind === 'bill') await remove.mutateAsync(deleting.id);
          else await removePlan.mutateAsync(deleting.id);
          setDeleting(null);
        }}
        title={deleting?.kind === 'plan' ? 'Delete payment plan?' : 'Delete bill?'}
        message="This record will be permanently removed."
      />
    </Page>
  );
};
