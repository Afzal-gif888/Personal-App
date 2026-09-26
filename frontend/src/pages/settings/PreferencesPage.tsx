import React, { useState } from 'react';
import { storage } from '../../services/storage';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/Card';
import { toast } from '../../stores/notificationStore';

export const PreferencesPage: React.FC = () => {
  const initial = storage.getPreferences();
  const [dailyGoalHours, setDailyGoalHours] = useState(initial.dailyStudyGoalHours);
  const [preferredStudyHours, setPreferredStudyHours] = useState(initial.preferredStudyHours);
  const [defaultReminderTime, setDefaultReminderTime] = useState(initial.defaultReminderTime);
  const [timezone, setTimezone] = useState(initial.timezone);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = () => {
    setIsSaving(true);
    storage.setPreferences({
      dailyStudyGoalHours: Number(dailyGoalHours),
      preferredStudyHours,
      defaultReminderTime,
      timezone,
    });
    setTimeout(() => {
      setIsSaving(false);
      toast.success('Preferences Saved');
    }, 200);
  };

  return (
    <Card className="max-w-xl">
      <CardHeader>
        <CardTitle>Productivity & AI Preferences</CardTitle>
        <CardDescription>Customize your daily study targets and scheduling defaults</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Input
          label="Daily Study Goal (Hours)"
          type="number"
          min="1"
          max="16"
          value={dailyGoalHours}
          onChange={(e) => setDailyGoalHours(Number(e.target.value))}
          helperText="Target hours used to calculate weekly progress on dashboard"
        />

        <Input
          label="Preferred Study Hours Window"
          value={preferredStudyHours}
          onChange={(e) => setPreferredStudyHours(e.target.value)}
          placeholder="18:00 - 22:00"
          helperText="Preferred time slot used by AI when generating study sessions"
        />

        <Input
          label="Default Reminder Time"
          type="time"
          value={defaultReminderTime}
          onChange={(e) => setDefaultReminderTime(e.target.value)}
        />

        <Select
          label="Timezone"
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
          options={[
            { value: 'America/Los_Angeles (PST)', label: 'Pacific Time (PST)' },
            { value: 'America/New_York (EST)', label: 'Eastern Time (EST)' },
            { value: 'Europe/London (GMT)', label: 'London (GMT)' },
            { value: 'Asia/Kolkata (IST)', label: 'India Standard Time (IST)' },
          ]}
        />
      </CardContent>
      <CardFooter className="justify-end">
        <Button variant="primary" size="sm" onClick={handleSave} isLoading={isSaving}>
          Save Preferences
        </Button>
      </CardFooter>
    </Card>
  );
};
