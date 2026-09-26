import React from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { MobileNav } from './MobileNav';
import { BottomNav } from './BottomNav';
import { CommandMenu } from '../ui/CommandMenu';
import { ToastContainer } from '../ui/Toast';
import { useAuthStore } from '../../stores/authStore';
import { cn } from '../../utils/cn';

export const AppLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuthStore();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-white text-xs text-[#8A8A8A]">
        Loading AgentOS...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const isChatRoute = location.pathname.startsWith('/chat');

  return (
    <div className="min-h-screen bg-white text-[#111111] flex flex-col md:flex-row antialiased selection:bg-neutral-900 selection:text-white">
      {/* Desktop Sidebar */}
      <Sidebar />

      {/* Mobile Drawer Navigation (Menu drawer) */}
      <MobileNav />

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        <Header />
        <main
          className={cn(
            'flex-1 w-full mx-auto overflow-x-hidden',
            isChatRoute
              ? 'p-0 md:p-4 lg:p-6 max-w-7xl pb-16 md:pb-6'
              : 'p-3.5 sm:p-6 lg:p-8 max-w-7xl pb-20 md:pb-8'
          )}
        >
          <Outlet />
        </main>
      </div>

      {/* Mobile Native Bottom Navigation Bar */}
      <BottomNav />

      {/* Global Command Menu Cmd+K */}
      <CommandMenu />

      {/* Toast Notifications */}
      <ToastContainer />
    </div>
  );
};
