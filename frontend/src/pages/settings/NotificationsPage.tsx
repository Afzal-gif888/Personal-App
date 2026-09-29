import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { userService } from '../../services/userService';
import { errorMessage } from '../../services/api';
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
    label: 'Email me reminders',
    description: 'Also send reminders, bill due dates and upcoming events to my email address.',
  },
];

export const NotificationsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: saved } = useQuery({ queryKey: ['notificationSettings'], queryFn: userService.getNotifications });
  // Unsaved edits; until the user toggles something the switches show the saved values.
  const [draft, setDraft] = useState<NotificationSettings | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const settings = draft ?? saved ?? null;

  const handleSave = async () => {
    if (!settings) return;
    setIsSaving(true);
    try {
      queryClient.setQueryData(['notificationSettings'], await userService.updateNotifications(settings));
      setDraft(null);
      toast.success('Notification settings saved');
    } catch (err) {
      toast.error('Could not save settings', errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <SettingsSection
      title="Notifications"
      description="Choose what It's Personal alerts you about."
      footer={
        <Button size="sm" onClick={handleSave} isLoading={isSaving} disabled={!settings}>
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
            checked={settings?.[opt.key] ?? false}
            disabled={!settings}
            onChange={(checked) => settings && setDraft({ ...settings, [opt.key]: checked })}
          />
        ))}
      </div>
    </SettingsSection>
  );
};
