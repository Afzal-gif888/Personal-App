import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { userService } from '../../services/userService';
import { errorMessage } from '../../services/api';
import type { PreferenceSettings } from '../../types';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Button } from '../../components/ui/Button';
import { toast } from '../../stores/notificationStore';
import { SettingsSection } from './SettingsLayout';

const TIMEZONES = [
  { value: 'Asia/Kolkata', label: 'India Standard Time (IST)' },
  { value: 'Europe/London', label: 'London (GMT/BST)' },
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
  { value: 'UTC', label: 'UTC' },
];

export const PreferencesPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: saved } = useQuery({ queryKey: ['preferences'], queryFn: userService.getPreferences });
  // Unsaved edits; until the user changes something the form shows the saved values.
  const [draft, setDraft] = useState<PreferenceSettings | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const form = draft ?? saved ?? null;

  const update = (patch: Partial<PreferenceSettings>) => setDraft((d) => {
    const base = d ?? saved;
    return base ? { ...base, ...patch } : d;
  });

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setIsSaving(true);
    try {
      queryClient.setQueryData(['preferences'], await userService.updatePreferences(form));
      setDraft(null);
      toast.success('Preferences saved');
    } catch (err) {
      toast.error('Could not save preferences', errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  };

  // Keep a timezone set elsewhere (e.g. at sign-up) selectable.
  const timezones =
    form && !TIMEZONES.some((t) => t.value === form.timezone)
      ? [{ value: form.timezone, label: form.timezone }, ...TIMEZONES]
      : TIMEZONES;

  return (
    <form onSubmit={handleSave}>
      <SettingsSection
        title="Assistant defaults"
        description="Used when the assistant schedules study sessions and reminders for you."
        footer={
          <Button type="submit" size="sm" isLoading={isSaving} disabled={!form}>
            Save changes
          </Button>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Daily study goal (hours)"
              type="number"
              min="0"
              max="16"
              step="0.5"
              value={form?.dailyStudyGoalHours ?? ''}
              disabled={!form}
              onChange={(e) => update({ dailyStudyGoalHours: Number(e.target.value) })}
            />
            <Input
              label="Default reminder time"
              type="time"
              value={form?.defaultReminderTime ?? ''}
              disabled={!form}
              onChange={(e) => update({ defaultReminderTime: e.target.value })}
            />
          </div>
          <Input
            label="Preferred study window"
            value={form?.preferredStudyHours ?? ''}
            disabled={!form}
            onChange={(e) => update({ preferredStudyHours: e.target.value })}
            placeholder="18:00 – 22:00"
            helperText="The assistant schedules new sessions inside this window."
          />
          <Select
            label="Time zone"
            value={form?.timezone ?? ''}
            disabled={!form}
            onChange={(e) => update({ timezone: e.target.value })}
            options={timezones}
          />
        </div>
      </SettingsSection>
    </form>
  );
};
