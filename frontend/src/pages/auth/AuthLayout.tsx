import React from 'react';
import { Logo } from '../../components/ui/Logo';

export const AuthLayout: React.FC<{ title: string; description: string; children: React.ReactNode }> = ({
  title,
  description,
  children,
}) => (
  <div className="min-h-screen flex flex-col bg-surface px-6 sm:px-10 py-8">
    <Logo size="sm" withText />
    <div className="flex-1 flex items-center justify-center py-10">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold tracking-tight text-fg">{title}</h1>
        <p className="mt-1.5 text-sm text-fg-subtle">{description}</p>
        <div className="mt-8">{children}</div>
      </div>
    </div>
    <p className="text-xs text-fg-faint">© {new Date().getFullYear()} It's Personal</p>
  </div>
);
