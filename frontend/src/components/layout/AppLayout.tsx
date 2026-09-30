import React, { Suspense } from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { MobileNav } from './MobileNav';
import { BottomNav } from './BottomNav';
import { CommandMenu } from '../ui/CommandMenu';
import { ToastContainer } from '../ui/Toast';
import { useAuthStore } from '../../stores/authStore';
import { cn } from '../../utils/cn';

/** Shown in the content area while a page's code downloads (first visit only). */
export const PageLoading: React.FC = () => (
  <div className="flex items-center justify-center py-24 gap-2 text-sm text-fg-subtle" role="status">
    <Loader2 className="size-4 animate-spin" />
    Loading…
  </div>
);

export const AppLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuthStore();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen gap-2 text-sm text-fg-subtle">
        <Loader2 className="size-4 animate-spin" />
        Loading workspace…
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  const isChatRoute = location.pathname.startsWith('/chat');

  return (
    <div className="min-h-screen flex bg-canvas text-fg">
      <Sidebar />
      <MobileNav />

      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        <Header />
        <main
          className={cn(
            'flex-1 w-full min-w-0',
            isChatRoute
              ? 'flex flex-col'
              : 'mx-auto max-w-screen-2xl px-4 sm:px-6 lg:px-8 py-5 sm:py-6 lg:py-8 pb-24 md:pb-10'
          )}
        >
          <Suspense fallback={<PageLoading />}>
            <Outlet />
          </Suspense>
        </main>
      </div>

      <BottomNav />
      <CommandMenu />
      <ToastContainer />
    </div>
  );
};
