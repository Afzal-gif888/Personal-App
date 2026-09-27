import React, { useState } from 'react';
import { storage } from '../../services/storage';
import type { NotificationSettings } from '../../types';
import { Switch } from '../../components/ui/Switch';
import { Button } from '../../components/ui/Button';
import { toast } from '../../stores/notificationStore';
import { SettingsSection } from './SettingsLayout';

const OPTIONS: { key: keyof NotificationSettings; label: string; description: string }[] = [
  {
    key: 'aiNotifications',
    label: 'Assistant approvals',
    description: 'Notify me when the assistant proposes an action that needs my review.',
  },
  {
    key: 'reminders',
    label: 'Reminders and deadlines',
    description: 'Alerts for scheduled reminders, task due dates and bills.',
  },
  {
    key: 'studyNotifications',
    label: 'Study sessions',
    description: 'A heads-up 15 minutes before a study session starts.',
  },
  {
    key: 'emailNotifications',
    label: 'Weekly summary email',
    description: 'Completed tasks, study hours and spending, every Monday.',
  },
];

export const NotificationsPage: React.FC = () => {
  const [settings, setSettings] = useState<NotificationSettings>(() => storage.getNotifications());
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = () => {
    setIsSaving(true);
    storage.setNotifications(settings);
    setTimeout(() => {
      setIsSaving(false);
      toast.success('Notification settings saved');
    }, 200);
  };

  return (
    <SettingsSection
      title="Notifications"
      description="Choose what AgentOS alerts you about."
      footer={
        <Button size="sm" onClick={handleSave} isLoading={isSaving}>
          Save changes
        </Button>
      }
    >
      <div className="divide-y divide-line -my-2">
        {OPTIONS.map((opt) => (
          <Switch
            key={opt.key}
            className="py-4"
            label={opt.label}
            description={opt.description}
            checked={settings[opt.key]}
            onChange={(checked) => setSettings((s) => ({ ...s, [opt.key]: checked }))}
          />
        ))}
      </div>
    </SettingsSection>
  );
};
