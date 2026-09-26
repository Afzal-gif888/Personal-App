import React from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { User, Bell, Sliders } from 'lucide-react';
import { Tabs } from '../../components/ui/Tabs';

export const SettingsLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const tabs = [
    { id: '/settings/profile', label: <span className="flex items-center gap-1.5"><User className="w-3.5 h-3.5" /> Profile</span> },
    { id: '/settings/notifications', label: <span className="flex items-center gap-1.5"><Bell className="w-3.5 h-3.5" /> Notifications</span> },
    { id: '/settings/preferences', label: <span className="flex items-center gap-1.5"><Sliders className="w-3.5 h-3.5" /> Preferences</span> },
  ];

  const currentTab = tabs.find((t) => location.pathname.startsWith(t.id))?.id || '/settings/profile';

  return (
    <div className="space-y-6 text-left max-w-4xl">
      <div>
        <h2 className="text-base font-semibold text-[#111111]">Account & Settings</h2>
        <p className="text-xs text-[#666666]">Manage your profile details, study goals, and notification channels</p>
      </div>

      <Tabs
        tabs={tabs}
        activeTab={currentTab}
        onChange={(path) => navigate(path)}
        variant="underline"
      />

      <div className="pt-2">
        <Outlet />
      </div>
    </div>
  );
};
