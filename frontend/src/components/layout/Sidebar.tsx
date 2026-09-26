import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  CheckSquare,
  CalendarDays,
  BookOpen,
  Bell,
  FileText,
  Activity,
  ShieldCheck,
  User,
  ChevronLeft,
  ChevronRight,
  Receipt,
  Wallet,
  Target,
} from 'lucide-react';
import { Logo } from '../ui/Logo';
import { useUIStore } from '../../stores/uiStore';
import { useApprovals } from '../../hooks/useApprovals';
import { cn } from '../../utils/cn';

export const Sidebar: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const { approvals } = useApprovals();
  const location = useLocation();

  const pendingApprovalsCount = approvals.filter((a) => a.status === 'pending').length;

  const sections = [
    {
      title: 'Overview',
      items: [
        { label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
        { label: 'AI Assistant', icon: MessageSquare, path: '/chat' },
      ],
    },
    {
      title: 'Academic',
      items: [
        { label: 'Tasks', icon: CheckSquare, path: '/tasks' },
        { label: 'Calendar', icon: CalendarDays, path: '/calendar' },
        { label: 'Study Plan', icon: BookOpen, path: '/study-plan' },
        { label: 'Reminders', icon: Bell, path: '/reminders' },
        { label: 'Documents', icon: FileText, path: '/documents' },
      ],
    },
    {
      title: 'Personal & Finance',
      items: [
        { label: 'Bills & Payments', icon: Receipt, path: '/bills' },
        { label: 'Expenses', icon: Wallet, path: '/expenses' },
        { label: 'Goals', icon: Target, path: '/goals' },
      ],
    },
    {
      title: 'AI',
      items: [
        { label: 'Agent Runs', icon: Activity, path: '/agent-runs' },
        {
          label: 'Approvals',
          icon: ShieldCheck,
          path: '/approvals',
          badge: pendingApprovalsCount > 0 ? pendingApprovalsCount : undefined,
        },
      ],
    },
    {
      title: 'Settings',
      items: [{ label: 'User Profile', icon: User, path: '/settings/profile' }],
    },
  ];

  return (
    <aside
      className={cn(
        'hidden md:flex flex-col h-screen bg-white border-r border-[#EAEAEA] transition-all duration-200 sticky top-0 z-30 select-none text-left',
        sidebarCollapsed ? 'w-16' : 'w-60'
      )}
    >
      {/* Brand Header */}
      <div className="flex items-center justify-between h-14 px-4 border-b border-[#EAEAEA]">
        <div className="flex items-center gap-2 overflow-hidden">
          <Logo size="sm" withText={!sidebarCollapsed} subtext="Personal AI OS" />
        </div>
        <button
          onClick={toggleSidebar}
          className="p-1 rounded-md text-[#8A8A8A] hover:text-[#111111] hover:bg-[#F7F7F7] transition-colors"
          title={sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation Groups */}
      <div className="flex-1 overflow-y-auto p-3 space-y-5">
        {sections.map((sec, idx) => (
          <div key={idx} className="space-y-1">
            {!sidebarCollapsed && (
              <h4 className="px-2 text-[10px] font-semibold text-[#8A8A8A] uppercase tracking-wider">
                {sec.title}
              </h4>
            )}
            <nav className="space-y-0.5">
              {sec.items.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname.startsWith(item.path);

                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={cn(
                      'flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors group relative',
                      isActive
                        ? 'bg-black text-white'
                        : 'text-[#666666] hover:text-[#111111] hover:bg-[#F7F7F7]',
                      sidebarCollapsed && 'justify-center px-0'
                    )}
                    title={sidebarCollapsed ? item.label : undefined}
                  >
                    <Icon className={cn('w-4 h-4 shrink-0', isActive ? 'text-white' : 'text-[#8A8A8A] group-hover:text-[#111111]')} />
                    {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
                    {item.badge !== undefined && (
                      <span
                        className={cn(
                          'ml-auto rounded-full px-1.5 py-0.2 text-[10px] font-semibold',
                          isActive ? 'bg-white text-black' : 'bg-black text-white',
                          sidebarCollapsed && 'absolute -top-1 -right-1 px-1 py-0.2'
                        )}
                      >
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* Agent Status Footer */}
      {!sidebarCollapsed && (
        <div className="p-3 border-t border-[#EAEAEA]">
          <div className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-[#F7F7F7] border border-[#EAEAEA]">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[11px] font-medium text-[#666666]">Mock Agent Core: Active</span>
          </div>
        </div>
      )}
    </aside>
  );
};
