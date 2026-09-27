import React, { useState } from 'react';
import { storage } from '../../services/storage';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Button } from '../../components/ui/Button';
import { toast } from '../../stores/notificationStore';
import { SettingsSection } from './SettingsLayout';

export const PreferencesPage: React.FC = () => {
  const initial = storage.getPreferences();
  const [dailyGoalHours, setDailyGoalHours] = useState(initial.dailyStudyGoalHours);
  const [preferredStudyHours, setPreferredStudyHours] = useState(initial.preferredStudyHours);
  const [defaultReminderTime, setDefaultReminderTime] = useState(initial.defaultReminderTime);
  const [timezone, setTimezone] = useState(initial.timezone);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    storage.setPreferences({
      dailyStudyGoalHours: Number(dailyGoalHours),
      preferredStudyHours,
      defaultReminderTime,
      timezone,
    });
    setTimeout(() => {
      setIsSaving(false);
      toast.success('Preferences saved');
    }, 200);
  };

  return (
    <form onSubmit={handleSave}>
      <SettingsSection
        title="Assistant defaults"
        description="Used when the assistant schedules study sessions and reminders for you."
        footer={
          <Button type="submit" size="sm" isLoading={isSaving}>
            Save changes
          </Button>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Daily study goal (hours)"
              type="number"
              min="1"
              max="16"
              value={dailyGoalHours}
              onChange={(e) => setDailyGoalHours(Number(e.target.value))}
            />
            <Input
              label="Default reminder time"
              type="time"
              value={defaultReminderTime}
              onChange={(e) => setDefaultReminderTime(e.target.value)}
            />
          </div>
          <Input
            label="Preferred study window"
            value={preferredStudyHours}
            onChange={(e) => setPreferredStudyHours(e.target.value)}
            placeholder="18:00 – 22:00"
            helperText="The assistant schedules new sessions inside this window."
          />
          <Select
            label="Time zone"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            options={[
              { value: 'Asia/Kolkata (IST)', label: 'India Standard Time (IST)' },
              { value: 'Europe/London (GMT)', label: 'London (GMT)' },
              { value: 'America/New_York (EST)', label: 'Eastern Time (EST)' },
              { value: 'America/Los_Angeles (PST)', label: 'Pacific Time (PST)' },
            ]}
          />
        </div>
      </SettingsSection>
    </form>
  );
};
