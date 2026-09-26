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
  Receipt,
  Wallet,
  Target,
} from 'lucide-react';
import { Logo } from '../ui/Logo';
import { Drawer } from '../ui/Drawer';
import { useUIStore } from '../../stores/uiStore';
import { useApprovals } from '../../hooks/useApprovals';
import { cn } from '../../utils/cn';

export const MobileNav: React.FC = () => {
  const { mobileDrawerOpen, setMobileDrawerOpen } = useUIStore();
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
      title: 'AI Management',
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
    <Drawer
      isOpen={mobileDrawerOpen}
      onClose={() => setMobileDrawerOpen(false)}
      title={<Logo size="sm" withText subtext="Personal AI OS" />}
    >
      <div className="space-y-6">
        {sections.map((sec, idx) => (
          <div key={idx} className="space-y-1">
            <h4 className="px-2 text-[10px] font-semibold text-[#8A8A8A] uppercase tracking-wider">
              {sec.title}
            </h4>
            <nav className="space-y-0.5">
              {sec.items.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname.startsWith(item.path);

                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileDrawerOpen(false)}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors',
                      isActive ? 'bg-black text-white' : 'text-[#666666] hover:bg-[#F7F7F7] hover:text-[#111111]'
                    )}
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <span>{item.label}</span>
                    {item.badge !== undefined && (
                      <span className="ml-auto rounded-full px-1.5 py-0.2 text-[10px] font-semibold bg-black text-white">
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
    </Drawer>
  );
};
