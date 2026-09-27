import React from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { User, Bell, SlidersHorizontal } from 'lucide-react';
import { Page, PageHeader } from '../../components/ui/PageHeader';
import { Tabs } from '../../components/ui/Tabs';
import { cn } from '../../utils/cn';

const SECTIONS = [
  { path: '/settings/profile', label: 'Profile', icon: User },
  { path: '/settings/notifications', label: 'Notifications', icon: Bell },
  { path: '/settings/preferences', label: 'Preferences', icon: SlidersHorizontal },
];

export const SettingsLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const current = SECTIONS.find((s) => location.pathname.startsWith(s.path))?.path ?? SECTIONS[0].path;

  return (
    <Page>
      <PageHeader title="Settings" description="Manage your profile, notifications and assistant defaults." />

      <Tabs
        className="md:hidden"
        activeTab={current}
        onChange={(path) => navigate(path)}
        tabs={SECTIONS.map((s) => ({ id: s.path, label: s.label }))}
      />

      <div className="flex gap-10">
        <nav aria-label="Settings" className="hidden md:block w-52 shrink-0 space-y-0.5">
          {SECTIONS.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2.5 h-9 px-3 rounded-md text-sm font-medium transition-colors',
                  isActive ? 'bg-surface border border-line shadow-xs text-fg' : 'text-fg-muted hover:text-fg hover:bg-subtle'
                )
              }
            >
              <Icon className="size-4 text-fg-subtle" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="flex-1 min-w-0 max-w-3xl">
          <Outlet />
        </div>
      </div>
    </Page>
  );
};

/** Titled settings card with an optional footer action row. */
export const SettingsSection: React.FC<{
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}> = ({ title, description, children, footer }) => (
  <section className="rounded-xl border border-line bg-surface shadow-xs">
    <header className="px-6 pt-5 pb-4 border-b border-line">
      <h2 className="text-base font-semibold text-fg">{title}</h2>
      {description && <p className="text-sm text-fg-subtle mt-0.5">{description}</p>}
    </header>
    <div className="px-6 py-5">{children}</div>
    {footer && (
      <footer className="flex items-center justify-end gap-2 px-6 py-3 border-t border-line bg-subtle/50 rounded-b-xl">{footer}</footer>
    )}
  </section>
);
