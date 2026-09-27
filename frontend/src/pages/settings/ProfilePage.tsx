import React, { useState } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { Input } from '../../components/ui/Input';
import { Textarea } from '../../components/ui/Textarea';
import { Button } from '../../components/ui/Button';
import { Avatar } from '../../components/ui/Avatar';
import { toast } from '../../stores/notificationStore';
import { SettingsSection } from './SettingsLayout';

export const ProfilePage: React.FC = () => {
  const { user, updateUser } = useAuthStore();
  const [name, setName] = useState(user?.name ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [university, setUniversity] = useState(user?.university ?? '');
  const [major, setMajor] = useState(user?.major ?? '');
  const [academicYear, setAcademicYear] = useState(user?.academicYear ?? '');
  const [bio, setBio] = useState(user?.bio ?? '');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    await updateUser({ name, email, university, major, academicYear, bio });
    setIsSaving(false);
    toast.success('Profile updated');
  };

  return (
    <form onSubmit={handleSave} className="space-y-6">
      <SettingsSection title="Personal information" description="How you appear across AgentOS.">
        <div className="flex items-center gap-4 mb-6">
          <Avatar name={name || 'User'} src={user?.avatarUrl} size="lg" />
          <div>
            <p className="text-sm font-medium text-fg">{name || 'Your name'}</p>
            <p className="text-sm text-fg-subtle">{email}</p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input label="Full name" value={name} onChange={(e) => setName(e.target.value)} required />
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
      </SettingsSection>

      <SettingsSection
        title="Academic details"
        description="Gives the assistant context when planning coursework and study sessions."
        footer={
          <Button type="submit" size="sm" isLoading={isSaving}>
            Save changes
          </Button>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input label="Institution" value={university} onChange={(e) => setUniversity(e.target.value)} />
            <Input label="Field of study" value={major} onChange={(e) => setMajor(e.target.value)} />
          </div>
          <Input label="Academic year" value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} />
          <Textarea
            label="About you"
            helperText="Goals or context you'd like the assistant to keep in mind."
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            rows={3}
          />
        </div>
      </SettingsSection>
    </form>
  );
};
