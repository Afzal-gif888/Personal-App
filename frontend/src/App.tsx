import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { useAuthStore } from './stores/authStore';
import { toast } from './stores/notificationStore';
import { ApiError, errorMessage } from './services/api';

// Layouts
import { AppLayout } from './components/layout/AppLayout';
import { SettingsLayout } from './pages/settings/SettingsLayout';

// Auth Pages
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { ForgotPasswordPage } from './pages/auth/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/auth/ResetPasswordPage';
import { VerifyOtpPage } from './pages/auth/VerifyOtpPage';

// Main Application Pages
import { DashboardPage } from './pages/DashboardPage';
import { ChatPage } from './pages/ChatPage';
import { TasksPage } from './pages/TasksPage';
import { StudyPlanPage } from './pages/StudyPlanPage';
import { RemindersPage } from './pages/RemindersPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { AgentRunsPage } from './pages/AgentRunsPage';
import { AgentRunDetailPage } from './pages/AgentRunDetailPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { CalendarPage } from './pages/CalendarPage';
import { BillsPage } from './pages/BillsPage';
import { ExpensesPage } from './pages/ExpensesPage';
import { BudgetsPage } from './pages/BudgetsPage';
import { GoalsPage } from './pages/GoalsPage';

// Settings Pages
import { ProfilePage } from './pages/settings/ProfilePage';
import { NotificationsPage } from './pages/settings/NotificationsPage';
import { PreferencesPage } from './pages/settings/PreferencesPage';

const queryClient = new QueryClient({
  // Hooks with their own onError show a specific message; everything else gets this one.
  mutationCache: new MutationCache({
    onError: (err, _vars, _ctx, mutation) => {
      if (!mutation.options.onError) toast.error('Something went wrong', errorMessage(err));
    },
  }),
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      // Retry network blips and server errors once, but not 4xx responses.
      retry: (count, err) => count < 1 && !(err instanceof ApiError && err.status >= 400 && err.status < 500),
      staleTime: 1000 * 60 * 5,
    },
  },
});

export const App: React.FC = () => {
  const { initialize } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/verify-otp" element={<VerifyOtpPage />} />

          {/* Protected App Routes */}
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/study-plan" element={<StudyPlanPage />} />
            <Route path="/reminders" element={<RemindersPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/agent-runs" element={<AgentRunsPage />} />
            <Route path="/agent-runs/:id" element={<AgentRunDetailPage />} />
            <Route path="/approvals" element={<ApprovalsPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/bills" element={<BillsPage />} />
            <Route path="/expenses" element={<ExpensesPage />} />
            <Route path="/budgets" element={<BudgetsPage />} />
            <Route path="/goals" element={<GoalsPage />} />

            {/* Settings Sub-routes */}
            <Route path="/settings" element={<SettingsLayout />}>
              <Route index element={<Navigate to="/settings/profile" replace />} />
              <Route path="profile" element={<ProfilePage />} />
              <Route path="notifications" element={<NotificationsPage />} />
              <Route path="preferences" element={<PreferencesPage />} />
            </Route>

            {/* Default Protected Route */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
