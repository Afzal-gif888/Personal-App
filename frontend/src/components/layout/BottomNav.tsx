import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  CheckSquare,
  CalendarDays,
  Menu,
} from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import { useApprovals } from '../../hooks/useApprovals';
import { cn } from '../../utils/cn';

export const BottomNav: React.FC = () => {
  const { setMobileDrawerOpen } = useUIStore();
  const { approvals } = useApprovals();
  const location = useLocation();

  const pendingApprovalsCount = approvals.filter((a) => a.status === 'pending').length;

  const navItems = [
    { label: 'Home', icon: LayoutDashboard, path: '/dashboard' },
    { label: 'AI Chat', icon: MessageSquare, path: '/chat' },
    { label: 'Tasks', icon: CheckSquare, path: '/tasks' },
    { label: 'Calendar', icon: CalendarDays, path: '/calendar' },
  ];

  return (
    <nav
      aria-label="Mobile Navigation"
      className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-white/95 backdrop-blur-md border-t border-[#EAEAEA] px-2 py-1 shadow-lg pb-[env(safe-area-inset-bottom,0px)]"
    >
      <div className="flex items-center justify-around h-13 max-w-lg mx-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname.startsWith(item.path);

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={cn(
                'flex flex-col items-center justify-center flex-1 py-1 px-1 transition-all rounded-lg active:scale-95 select-none min-h-[44px]',
                isActive
                  ? 'text-black font-semibold'
                  : 'text-[#8A8A8A] hover:text-[#111111]'
              )}
            >
              <div className="relative">
                <Icon
                  className={cn(
                    'w-5 h-5 transition-transform',
                    isActive ? 'scale-110 text-black stroke-[2.2]' : 'stroke-[1.8]'
                  )}
                />
                {item.path === '/chat' && (
                  <span className="absolute -top-0.5 -right-1 w-2 h-2 rounded-full bg-cyan-400 animate-pulse ring-2 ring-white" />
                )}
              </div>
              <span className="text-[10px] mt-1 leading-none tracking-tight">
                {item.label}
              </span>
            </NavLink>
          );
        })}

        {/* More Button to trigger full drawer */}
        <button
          onClick={() => setMobileDrawerOpen(true)}
          className="flex flex-col items-center justify-center flex-1 py-1 px-1 text-[#8A8A8A] hover:text-[#111111] transition-all rounded-lg active:scale-95 select-none cursor-pointer min-h-[44px]"
        >
          <div className="relative">
            <Menu className="w-5 h-5 stroke-[1.8]" />
            {pendingApprovalsCount > 0 && (
              <span className="absolute -top-1 -right-1.5 min-w-[14px] h-[14px] flex items-center justify-center rounded-full bg-black text-white text-[8px] font-bold px-0.5">
                {pendingApprovalsCount}
              </span>
            )}
          </div>
          <span className="text-[10px] mt-1 leading-none tracking-tight">
            Menu
          </span>
        </button>
      </div>
    </nav>
  );
};
