import React, { useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { CheckSquare, CalendarDays, Receipt, Wallet, ArrowRight, Check, X, Inbox } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { useTasks } from '../hooks/useTasks';
import { useReminders } from '../hooks/useReminders';
import { useStudyPlan } from '../hooks/useStudyPlan';
import { useEvents } from '../hooks/useEvents';
import { useBills } from '../hooks/useBills';
import { useGoals } from '../hooks/useGoals';
import { useExpenses } from '../hooks/useExpenses';
import { useApprovals } from '../hooks/useApprovals';
import { useAgentRuns } from '../hooks/useAgentRuns';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { StatCard } from '../components/ui/StatCard';
import { Panel } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Checkbox } from '../components/ui/Checkbox';
import { Progress } from '../components/ui/Progress';
import { EmptyState } from '../components/ui/EmptyState';
import { WorkflowOverview } from '../components/dashboard/WorkflowOverview';
import {
  formatCurrency,
  formatDayLabel,
  formatLongDate,
  formatTime,
  todayISO,
  daysUntil,
} from '../utils/formatters';
import { PRIORITY_STYLES, BILL_STATUS_STYLES, statusStyle } from '../utils/status';

interface ScheduleEntry {
  id: string;
  date: string;
  time: string;
  title: string;
  kind: 'Event' | 'Study' | 'Reminder';
  detail?: string;
}

const ViewAll: React.FC<{ to: string; label?: string }> = ({ to, label = 'View all' }) => (
  <Link to={to} className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:text-accent-hover">
    {label}
    <ArrowRight className="size-3.5" />
  </Link>
);

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { tasks, toggleComplete: toggleTask } = useTasks();
  const { reminders } = useReminders();
  const { sessions } = useStudyPlan();
  const { data: events = [] } = useEvents();
  const { data: bills = [] } = useBills();
  const { data: goals = [] } = useGoals();
  const { data: expenses = [] } = useExpenses();
  const { approvals, respondToApproval, isResponding } = useApprovals();
  const { agentRuns } = useAgentRuns();

  const today = todayISO();
  const openTasks = tasks.filter((t) => t.status !== 'completed');
  const dueToday = openTasks.filter((t) => t.dueDate <= today).length;
  const tasksDueSoon = [...openTasks].sort((a, b) => a.dueDate.localeCompare(b.dueDate)).slice(0, 5);

  const unpaidBills = bills.filter((b) => b.status !== 'paid').sort((a, b) => a.dueDate.localeCompare(b.dueDate));
  const unpaidTotal = unpaidBills.reduce((s, b) => s + b.amount, 0);
  const overdueCount = unpaidBills.filter((b) => b.status === 'overdue').length;

  const month = today.slice(0, 7);
  const spentThisMonth = expenses.filter((e) => e.date.startsWith(month)).reduce((s, e) => s + e.amount, 0);

  const pendingApprovals = approvals.filter((a) => a.status === 'pending');
  const activeGoals = goals.filter((g) => g.status === 'active').slice(0, 4);

  const schedule = useMemo<ScheduleEntry[]>(() => {
    const entries: ScheduleEntry[] = [
      ...events.map((e) => ({
        id: e.id,
        date: e.date,
        time: e.startTime,
        title: e.title,
        kind: 'Event' as const,
        detail: e.location,
      })),
      ...sessions
        .filter((s) => s.status === 'scheduled')
        .map((s) => ({ id: s.id, date: s.date, time: s.startTime, title: s.topic, kind: 'Study' as const, detail: s.subject })),
      ...reminders
        .filter((r) => r.status !== 'completed')
        .map((r) => ({ id: r.id, date: r.date, time: r.time, title: r.title, kind: 'Reminder' as const })),
    ];
    return entries
      .filter((e) => {
        const d = daysUntil(e.date);
        return d >= 0 && d <= 7;
      })
      .sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time))
      .slice(0, 7);
  }, [events, sessions, reminders]);

  const upcomingEventCount = events.filter((e) => {
    const d = daysUntil(e.date);
    return d >= 0 && d <= 7;
  }).length;

  const scheduleByDay = schedule.reduce<Record<string, ScheduleEntry[]>>((acc, entry) => {
    (acc[entry.date] ||= []).push(entry);
    return acc;
  }, {});

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const firstName = user?.name?.split(' ')[0];

  return (
    <Page>
      <PageHeader
        title={firstName ? `${greeting}, ${firstName}` : greeting}
        description={formatLongDate()}
        actions={
          <Button variant="secondary" size="sm" onClick={() => navigate('/tasks')} leftIcon={<CheckSquare className="size-4" />}>
            New task
          </Button>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StatCard
          label="Open tasks"
          value={openTasks.length}
          hint={dueToday ? `${dueToday} due today or earlier` : 'Nothing due today'}
          icon={<CheckSquare />}
          onClick={() => navigate('/tasks')}
        />
        <StatCard
          label="Events this week"
          value={upcomingEventCount}
          hint="Next 7 days"
          icon={<CalendarDays />}
          onClick={() => navigate('/calendar')}
        />
        <StatCard
          label="Bills outstanding"
          value={formatCurrency(unpaidTotal)}
          hint={overdueCount ? `${overdueCount} overdue` : `${unpaidBills.length} unpaid`}
          tone={overdueCount ? 'danger' : 'default'}
          icon={<Receipt />}
          onClick={() => navigate('/bills')}
        />
        <StatCard
          label="Spent this month"
          value={formatCurrency(spentThisMonth)}
          hint="All categories"
          icon={<Wallet />}
          onClick={() => navigate('/expenses')}
        />
      </div>

      <WorkflowOverview
        runCount={agentRuns.length}
        pendingCount={pendingApprovals.length}
        approvedCount={approvals.filter((a) => a.status === 'approved').length}
        openTaskCount={openTasks.length}
      />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 sm:gap-6 items-start">
        <div className="xl:col-span-2 space-y-4 sm:space-y-6">
          <Panel title="Tasks due soon" description="Sorted by due date" action={<ViewAll to="/tasks" />}>
            {tasksDueSoon.length === 0 ? (
              <EmptyState bare icon={<CheckSquare />} title="All caught up" description="No open tasks right now." />
            ) : (
              <ul className="divide-y divide-line">
                {tasksDueSoon.map((t) => {
                  const priority = statusStyle(PRIORITY_STYLES, t.priority);
                  const overdue = daysUntil(t.dueDate) < 0;
                  return (
                    <li key={t.id} className="flex items-center gap-3 px-5 py-3">
                      <Checkbox
                        checked={false}
                        onChange={() => toggleTask(t.id)}
                        aria-label={`Mark "${t.title}" as done`}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-fg truncate">{t.title}</p>
                        <p className="text-xs text-fg-subtle truncate mt-0.5">
                          {t.subject ? `${t.subject} · ` : ''}
                          <span className={overdue ? 'text-danger font-medium' : undefined}>
                            {overdue ? 'Overdue' : formatDayLabel(t.dueDate)}
                          </span>
                          {t.dueTime ? ` at ${formatTime(t.dueTime)}` : ''}
                        </p>
                      </div>
                      <Badge variant={priority.variant} dot>
                        {priority.label}
                      </Badge>
                    </li>
                  );
                })}
              </ul>
            )}
          </Panel>

          <Panel title="Schedule" description="Events, study sessions and reminders for the next 7 days" action={<ViewAll to="/calendar" label="Calendar" />}>
            {schedule.length === 0 ? (
              <EmptyState bare icon={<CalendarDays />} title="Nothing scheduled" description="Your next 7 days are clear." />
            ) : (
              <div className="divide-y divide-line">
                {Object.entries(scheduleByDay).map(([date, entries]) => (
                  <div key={date} className="px-5 py-3">
                    <p className="text-xs font-medium text-fg-subtle mb-2">{formatDayLabel(date)}</p>
                    <ul className="space-y-2">
                      {entries.map((entry) => (
                        <li key={`${entry.kind}-${entry.id}`} className="flex items-center gap-3">
                          <span className="w-16 shrink-0 text-xs text-fg-subtle tabular">{formatTime(entry.time)}</span>
                          <span
                            className={
                              entry.kind === 'Study'
                                ? 'w-0.5 self-stretch rounded-full bg-accent'
                                : entry.kind === 'Reminder'
                                  ? 'w-0.5 self-stretch rounded-full bg-warning'
                                  : 'w-0.5 self-stretch rounded-full bg-fg-faint'
                            }
                          />
                          <div className="min-w-0 flex-1">
                            <p className="text-sm text-fg truncate">{entry.title}</p>
                            {entry.detail && <p className="text-xs text-fg-subtle truncate">{entry.detail}</p>}
                          </div>
                          <span className="text-xs text-fg-subtle shrink-0">{entry.kind}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-1 gap-4 sm:gap-6 items-start">
          <Panel
            title="Awaiting your approval"
            description="Proposed by the assistant"
            action={pendingApprovals.length > 0 ? <ViewAll to="/approvals" label="Review" /> : undefined}
          >
            {pendingApprovals.length === 0 ? (
              <EmptyState bare icon={<Inbox />} title="Inbox zero" description="Nothing needs your review." />
            ) : (
              <ul className="divide-y divide-line">
                {pendingApprovals.slice(0, 3).map((a) => (
                  <li key={a.id} className="px-5 py-3.5">
                    <p className="text-xs font-medium text-fg-subtle">{a.type}</p>
                    <p className="text-sm font-medium text-fg mt-0.5">{a.title}</p>
                    <div className="flex items-center gap-2 mt-3">
                      <Button
                        size="xs"
                        leftIcon={<Check className="size-3.5" />}
                        disabled={isResponding}
                        onClick={() => respondToApproval({ id: a.id, decision: 'approved' })}
                      >
                        Approve
                      </Button>
                      <Button
                        size="xs"
                        variant="secondary"
                        leftIcon={<X className="size-3.5" />}
                        disabled={isResponding}
                        onClick={() => respondToApproval({ id: a.id, decision: 'rejected' })}
                      >
                        Reject
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Upcoming bills" action={<ViewAll to="/bills" />}>
            {unpaidBills.length === 0 ? (
              <EmptyState bare icon={<Receipt />} title="All paid" description="No outstanding bills." />
            ) : (
              <ul className="divide-y divide-line">
                {unpaidBills.slice(0, 4).map((bill) => {
                  const s = statusStyle(BILL_STATUS_STYLES, bill.status);
                  return (
                    <li key={bill.id} className="flex items-center justify-between gap-3 px-5 py-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-fg truncate">{bill.title}</p>
                        <p className="text-xs text-fg-subtle mt-0.5">Due {formatDayLabel(bill.dueDate)}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-sm font-semibold text-fg tabular">{formatCurrency(bill.amount)}</p>
                        {bill.status !== 'upcoming' && (
                          <Badge variant={s.variant} className="mt-1">
                            {s.label}
                          </Badge>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </Panel>

          <Panel title="Goals" action={<ViewAll to="/goals" />} bodyClassName="px-5 py-4 space-y-4">
            {activeGoals.length === 0 ? (
              <p className="text-sm text-fg-subtle">No active goals.</p>
            ) : (
              activeGoals.map((g) => (
                <div key={g.id}>
                  <div className="flex items-center justify-between gap-3 mb-1.5">
                    <span className="text-sm text-fg truncate">{g.title}</span>
                    <span className="text-xs font-medium text-fg-muted tabular">{g.progress}%</span>
                  </div>
                  <Progress value={g.progress} label={g.title} />
                </div>
              ))
            )}
          </Panel>
        </div>
      </div>
    </Page>
  );
};
