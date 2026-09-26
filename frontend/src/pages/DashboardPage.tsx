import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  CheckSquare,
  CalendarDays,
  Sparkles,
  ArrowRight,
  Bell,
  Receipt,
  Target,
  Wallet,
} from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { useTasks } from '../hooks/useTasks';
import { useReminders } from '../hooks/useReminders';
import { useStudyPlan } from '../hooks/useStudyPlan';
import { useEvents } from '../hooks/useEvents';
import { useBills } from '../hooks/useBills';
import { useGoals } from '../hooks/useGoals';
import { useExpenses } from '../hooks/useExpenses';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Checkbox } from '../components/ui/Checkbox';
import { getPriorityBadgeColor, formatDate } from '../utils/formatters';

const CATEGORY_COLORS: Record<string, string> = {
  academic: 'bg-blue-50 text-blue-700',
  personal: 'bg-purple-50 text-purple-700',
  financial: 'bg-emerald-50 text-emerald-700',
  career: 'bg-amber-50 text-amber-700',
  general: 'bg-[#F7F7F7] text-[#666666]',
};

export const DashboardPage: React.FC = () => {
  const { user } = useAuthStore();
  const { tasks, toggleComplete: toggleTask } = useTasks();
  const { reminders, toggleComplete: toggleReminder, snoozeReminder } = useReminders();
  const { sessions } = useStudyPlan();
  const { data: events = [] } = useEvents();
  const { data: bills = [] } = useBills();
  const { data: goals = [] } = useGoals();
  const { data: expenses = [] } = useExpenses();
  const navigate = useNavigate();

  const pendingTasks = tasks.filter((t) => t.status !== 'completed').slice(0, 5);
  const todaysReminders = reminders.filter((r) => r.status === 'today' || r.status === 'upcoming').slice(0, 3);
  const upcomingEvents = events.slice(0, 3);
  const unpaidBills = bills.filter((b) => b.status !== 'paid').slice(0, 3);
  const activeGoals = goals.filter((g) => g.status === 'active').slice(0, 3);
  const todaysSessions = sessions.slice(0, 2);

  // Compute summary stats
  const pendingTaskCount = tasks.filter((t) => t.status !== 'completed').length;
  const upcomingEventCount = events.length;
  const unpaidBillTotal = bills.filter((b) => b.status !== 'paid').reduce((s, b) => s + b.amount, 0);
  const thisMonthExpenses = expenses
    .filter((e) => e.date.startsWith(new Date().toISOString().slice(0, 7)))
    .reduce((s, e) => s + e.amount, 0);

  // Time-based greeting
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  return (
    <div className="space-y-6 text-left">
      {/* Header Greeting */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#EAEAEA]">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-[#111111] tracking-tight">
            {greeting}, {user?.name?.split(' ')[0] || 'Alex'}
          </h1>
          <p className="text-xs text-[#666666] mt-0.5">Here's everything that needs your attention today.</p>
        </div>
        <Button
          variant="primary" size="sm" onClick={() => navigate('/chat')}
          leftIcon={<Sparkles className="w-3.5 h-3.5 text-emerald-400" />}
        >
          Ask AI
        </Button>
      </div>

      {/* Top Metrics Bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Card hoverable onClick={() => navigate('/tasks')}>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] text-[#8A8A8A] font-medium">Pending Tasks</span>
            <CheckSquare className="w-3.5 h-3.5 text-[#8A8A8A]" />
          </div>
          <div className="text-xl font-bold text-[#111111]">{pendingTaskCount}</div>
          <p className="text-[10px] text-[#8A8A8A] mt-0.5">across all categories</p>
        </Card>

        <Card hoverable onClick={() => navigate('/calendar')}>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] text-[#8A8A8A] font-medium">Events</span>
            <CalendarDays className="w-3.5 h-3.5 text-[#8A8A8A]" />
          </div>
          <div className="text-xl font-bold text-[#111111]">{upcomingEventCount}</div>
          <p className="text-[10px] text-[#8A8A8A] mt-0.5">upcoming</p>
        </Card>

        <Card hoverable onClick={() => navigate('/bills')}>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] text-[#8A8A8A] font-medium">Bills Due</span>
            <Receipt className="w-3.5 h-3.5 text-[#8A8A8A]" />
          </div>
          <div className="text-xl font-bold text-[#111111]">₹{unpaidBillTotal.toLocaleString()}</div>
          <p className="text-[10px] text-[#8A8A8A] mt-0.5">unpaid</p>
        </Card>

        <Card hoverable onClick={() => navigate('/expenses')}>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] text-[#8A8A8A] font-medium">Spent This Month</span>
            <Wallet className="w-3.5 h-3.5 text-[#8A8A8A]" />
          </div>
          <div className="text-xl font-bold text-[#111111]">₹{thisMonthExpenses.toLocaleString()}</div>
          <p className="text-[10px] text-[#8A8A8A] mt-0.5">total expenses</p>
        </Card>
      </div>

      {/* AI Assistant Callout Card */}
      <Card className="bg-black text-white border-black p-4 sm:p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">AI Assistant</span>
            </div>
            <h3 className="text-sm sm:text-base font-bold text-white">What would you like to work on?</h3>
            <p className="text-xs text-neutral-400">
              Manage tasks, study plans, bills, expenses, goals, calendar events, and more — all in one place.
            </p>
          </div>
          <Button
            variant="secondary" size="sm" onClick={() => navigate('/chat')}
            className="shrink-0 bg-white text-black hover:bg-neutral-100"
            rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
          >
            Open Assistant
          </Button>
        </div>
      </Card>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Tasks + Upcoming Bills */}
        <div className="lg:col-span-2 space-y-6">
          {/* Today's Tasks */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle>Tasks</CardTitle>
                <CardDescription>Priority items requiring your attention</CardDescription>
              </div>
              <Link to="/tasks" className="text-xs font-semibold text-black hover:underline">
                View all ({tasks.length})
              </Link>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {pendingTasks.length === 0 ? (
                  <p className="text-xs text-[#8A8A8A] py-4 text-center">All caught up — no pending tasks!</p>
                ) : (
                  pendingTasks.map((t) => (
                    <div
                      key={t.id}
                      className="flex items-start justify-between gap-3 p-3 rounded-md border border-[#EAEAEA] bg-white hover:bg-[#F7F7F7] transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <Checkbox checked={t.status === 'completed'} onChange={() => toggleTask(t.id)} className="mt-0.5" />
                        <div className="space-y-1">
                          <h4 className="text-xs font-semibold text-[#111111] leading-snug">{t.title}</h4>
                          <div className="flex items-center gap-2 text-[11px] text-[#666666]">
                            <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${CATEGORY_COLORS[t.category] || ''}`}>
                              {t.category}
                            </span>
                            {t.subject && <span className="font-medium text-[#111111]">{t.subject}</span>}
                            <span>•</span>
                            <span>Due {t.dueTime || '11:59 PM'}</span>
                          </div>
                        </div>
                      </div>
                      <Badge className={getPriorityBadgeColor(t.priority)} size="sm">{t.priority}</Badge>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Upcoming Events & Meetings */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle>Upcoming Events</CardTitle>
                <CardDescription>Classes, meetings, and appointments</CardDescription>
              </div>
              <Link to="/calendar" className="text-xs font-semibold text-black hover:underline">View all</Link>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {upcomingEvents.length === 0 ? (
                  <p className="text-xs text-[#8A8A8A] py-4 text-center">No upcoming events</p>
                ) : (
                  upcomingEvents.map((ev) => (
                    <div key={ev.id} className="flex items-center justify-between p-3 rounded-md border border-[#EAEAEA] bg-white">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-md bg-[#F7F7F7] flex flex-col items-center justify-center shrink-0">
                          <span className="text-[10px] text-[#8A8A8A] font-medium leading-none">{formatDate(ev.date).split(' ')[0]}</span>
                          <span className="text-xs font-bold text-[#111111] leading-none">{formatDate(ev.date).split(' ')[1]}</span>
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold text-[#111111]">{ev.title}</h4>
                          <p className="text-[11px] text-[#666666]">{ev.startTime}{ev.endTime ? ` – ${ev.endTime}` : ''}{ev.location ? ` · ${ev.location}` : ''}</p>
                        </div>
                      </div>
                      <Badge variant="neutral" size="sm">{ev.type}</Badge>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Unpaid Bills */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle>Upcoming Bills</CardTitle>
                <CardDescription>Payments due soon</CardDescription>
              </div>
              <Link to="/bills" className="text-xs font-semibold text-black hover:underline">View all</Link>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {unpaidBills.length === 0 ? (
                  <p className="text-xs text-[#8A8A8A] py-4 text-center">All bills are paid!</p>
                ) : (
                  unpaidBills.map((bill) => (
                    <div key={bill.id} className="flex items-center justify-between p-3 rounded-md border border-[#EAEAEA] bg-white">
                      <div className="space-y-0.5">
                        <h4 className="text-xs font-semibold text-[#111111]">{bill.title}</h4>
                        <p className="text-[11px] text-[#666666]">Due {formatDate(bill.dueDate)}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-bold text-[#111111]">₹{bill.amount.toLocaleString()}</div>
                        <Badge
                          className={
                            bill.status === 'overdue' ? 'bg-red-50 text-red-700 border border-red-100' :
                            bill.status === 'due' ? 'bg-amber-50 text-amber-700 border border-amber-100' :
                            'bg-blue-50 text-blue-700 border border-blue-100'
                          }
                          size="sm"
                        >
                          {bill.status}
                        </Badge>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Study Plan, Reminders, Goals */}
        <div className="space-y-6">
          {/* Today's Study Plan */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle>Study Sessions</CardTitle>
                <CardDescription>Scheduled study time</CardDescription>
              </div>
              <Link to="/study-plan" className="text-xs font-semibold text-black hover:underline">Manage</Link>
            </CardHeader>
            <CardContent>
              <div className="space-y-2.5">
                {todaysSessions.length === 0 ? (
                  <p className="text-xs text-[#8A8A8A] py-3 text-center">No study sessions scheduled</p>
                ) : (
                  todaysSessions.map((s) => (
                    <div key={s.id} className="p-3 rounded-md border border-[#EAEAEA] bg-white space-y-1.5">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-mono text-[#8A8A8A]">{s.startTime} - {s.endTime}</span>
                        <Badge variant={s.status === 'completed' ? 'success' : 'neutral'} size="sm">{s.status}</Badge>
                      </div>
                      <h4 className="text-xs font-semibold text-[#111111]">{s.subject}</h4>
                      <p className="text-[11px] text-[#666666]">{s.topic}</p>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Reminders */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle>Reminders</CardTitle>
                <CardDescription>Upcoming alerts</CardDescription>
              </div>
              <Link to="/reminders" className="text-xs font-semibold text-black hover:underline">All ({reminders.length})</Link>
            </CardHeader>
            <CardContent>
              <div className="space-y-2.5">
                {todaysReminders.map((r) => (
                  <div key={r.id} className="p-3 rounded-md border border-[#EAEAEA] bg-white flex items-center justify-between gap-2">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-[#111111]">
                        <Bell className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                        <span>{r.title}</span>
                      </div>
                      <p className="text-[11px] text-[#666666]">{r.date} at {r.time}</p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Button variant="ghost" size="sm" onClick={() => snoozeReminder({ id: r.id })} className="px-2 text-[10px]">Snooze</Button>
                      <Button variant="outline" size="sm" onClick={() => toggleReminder(r.id)} className="px-2 text-[10px]">Done</Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Active Goals */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle>Active Goals</CardTitle>
                <CardDescription>Track your progress</CardDescription>
              </div>
              <Link to="/goals" className="text-xs font-semibold text-black hover:underline">View all</Link>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {activeGoals.length === 0 ? (
                  <p className="text-xs text-[#8A8A8A] py-3 text-center">No active goals</p>
                ) : (
                  activeGoals.map((g) => (
                    <div key={g.id} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Target className="w-3.5 h-3.5 text-[#8A8A8A]" />
                          <span className="text-xs font-semibold text-[#111111]">{g.title}</span>
                        </div>
                        <span className="text-[11px] font-bold text-[#111111]">{g.progress}%</span>
                      </div>
                      <div className="h-1.5 bg-[#F7F7F7] rounded-full overflow-hidden">
                        <div className="h-full bg-black rounded-full transition-all" style={{ width: `${g.progress}%` }} />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
