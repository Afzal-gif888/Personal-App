import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Menu, Search, LogOut, Settings as SettingsIcon } from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import { useAuthStore } from '../../stores/authStore';
import { Avatar } from '../ui/Avatar';
import { Dropdown } from '../ui/Dropdown';

export const Header: React.FC = () => {
  const { setMobileDrawerOpen, setCommandMenuOpen } = useUIStore();
  const { user, logout } = useAuthStore();
  const location = useLocation();
  const navigate = useNavigate();

  // Dynamic route titles
  const getPageTitle = (path: string) => {
    if (path.startsWith('/dashboard')) return 'Dashboard';
    if (path.startsWith('/chat')) return 'AI Assistant';
    if (path.startsWith('/tasks')) return 'Tasks & Assignments';
    if (path.startsWith('/calendar')) return 'Calendar & Schedule';
    if (path.startsWith('/study-plan')) return 'Study Plan';
    if (path.startsWith('/reminders')) return 'Reminders';
    if (path.startsWith('/documents')) return 'Document Library';
    if (path.startsWith('/bills')) return 'Bills & Payments';
    if (path.startsWith('/expenses')) return 'Expenses & Budget';
    if (path.startsWith('/goals')) return 'Personal Goals';
    if (path.startsWith('/agent-runs')) return 'Agent Execution Log';
    if (path.startsWith('/approvals')) return 'Pending Approvals';
    if (path.startsWith('/settings')) return 'Settings';
    return 'AgentOS';
  };

  const dropdownItems = [
    {
      id: 'profile',
      label: 'Profile & Settings',
      icon: <SettingsIcon className="w-3.5 h-3.5" />,
      onClick: () => navigate('/settings/profile'),
    },
    {
      id: 'logout',
      label: 'Sign out',
      icon: <LogOut className="w-3.5 h-3.5" />,
      onClick: () => {
        logout();
        navigate('/login');
      },
      destructive: true,
    },
  ];

  return (
    <header className="sticky top-0 z-20 h-14 bg-white border-b border-[#EAEAEA] px-4 sm:px-6 flex items-center justify-between">
      {/* Mobile Drawer Trigger & Page Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setMobileDrawerOpen(true)}
          className="md:hidden p-1.5 rounded-md text-[#666666] hover:text-[#111111] hover:bg-[#F7F7F7]"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="text-sm font-semibold text-[#111111] tracking-tight">
          {getPageTitle(location.pathname)}
        </h1>
      </div>

      {/* Right Controls: Quick Search & Profile */}
      <div className="flex items-center gap-3">
        {/* Quick Search Palette Trigger */}
        <button
          onClick={() => setCommandMenuOpen(true)}
          className="hidden sm:flex items-center gap-2 px-3 py-1.5 text-xs text-[#8A8A8A] bg-[#F7F7F7] border border-[#EAEAEA] rounded-md hover:bg-[#F3F3F3] hover:text-[#111111] transition-colors cursor-pointer"
        >
          <Search className="w-3.5 h-3.5" />
          <span>Search or commands...</span>
          <kbd className="px-1.5 py-0.2 text-[10px] font-mono bg-white border border-[#EAEAEA] rounded text-[#666666]">
            ⌘K
          </kbd>
        </button>

        {/* Small Search Icon for Mobile */}
        <button
          onClick={() => setCommandMenuOpen(true)}
          className="sm:hidden p-1.5 rounded-md text-[#666666] hover:bg-[#F7F7F7]"
          aria-label="Search"
        >
          <Search className="w-4 h-4" />
        </button>

        <div className="h-4 w-px bg-[#EAEAEA]" />

        {/* User Dropdown */}
        <Dropdown
          trigger={
            <div className="flex items-center gap-2 cursor-pointer p-0.5 rounded-md hover:bg-[#F7F7F7]">
              <Avatar name={user?.name || 'Alex Rivera'} src={user?.avatarUrl} size="sm" />
              <span className="hidden md:inline-block text-xs font-medium text-[#111111]">
                {user?.name || 'Alex Rivera'}
              </span>
            </div>
          }
          items={dropdownItems}
        />
      </div>
    </header>
  );
};
