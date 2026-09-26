import React, { useState } from 'react';
import { storage } from '../../services/storage';
import { Switch } from '../../components/ui/Switch';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/Card';
import { toast } from '../../stores/notificationStore';

export const NotificationsPage: React.FC = () => {
  const initial = storage.getNotifications();
  const [reminders, setReminders] = useState(initial.reminders);
  const [studyNotifications, setStudyNotifications] = useState(initial.studyNotifications);
  const [aiNotifications, setAiNotifications] = useState(initial.aiNotifications);
  const [emailNotifications, setEmailNotifications] = useState(initial.emailNotifications);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = () => {
    setIsSaving(true);
    storage.setNotifications({ reminders, studyNotifications, aiNotifications, emailNotifications });
    setTimeout(() => {
      setIsSaving(false);
      toast.success('Notification Settings Saved');
    }, 200);
  };

  return (
    <Card className="max-w-xl">
      <CardHeader>
        <CardTitle>Notification Preferences</CardTitle>
        <CardDescription>Control when and how AgentOS alerts you</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <Switch
          label="Upcoming Reminder Alerts"
          description="Receive simulated pop-up notifications for scheduled task & study deadlines."
          checked={reminders}
          onChange={setReminders}
        />
        <div className="h-px bg-[#EAEAEA]" />
        <Switch
          label="Study Session Countdown"
          description="Alert 15 minutes before an AI-generated study session begins."
          checked={studyNotifications}
          onChange={setStudyNotifications}
        />
        <div className="h-px bg-[#EAEAEA]" />
        <Switch
          label="AI Action Approvals"
          description="Notify when the AI agent drafts a new task, reminder, or schedule modification."
          checked={aiNotifications}
          onChange={setAiNotifications}
        />
        <div className="h-px bg-[#EAEAEA]" />
        <Switch
          label="Weekly Performance Digest"
          description="Receive a summary email of completed tasks and logged study hours."
          checked={emailNotifications}
          onChange={setEmailNotifications}
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
