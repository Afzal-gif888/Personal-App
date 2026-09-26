import React, { useState } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { Input } from '../../components/ui/Input';
import { Textarea } from '../../components/ui/Textarea';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/Card';
import { Avatar } from '../../components/ui/Avatar';
import { toast } from '../../stores/notificationStore';

export const ProfilePage: React.FC = () => {
  const { user, updateUser } = useAuthStore();
  const [name, setName] = useState(user?.name || 'Alex Rivera');
  const [email, setEmail] = useState(user?.email || 'student@agentos.demo');
  const [university, setUniversity] = useState(user?.university || 'Stanford University');
  const [major, setMajor] = useState(user?.major || 'Computer Science & AI');
  const [academicYear, setAcademicYear] = useState(user?.academicYear || 'Senior (Year 4)');
  const [bio, setBio] = useState(user?.bio || '');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    await updateUser({ name, email, university, major, academicYear, bio });
    setIsSaving(false);
    toast.success('Profile Saved', 'Your account and academic info have been updated.');
  };

  return (
    <form onSubmit={handleSave} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Personal Information</CardTitle>
          <CardDescription>Your public student identity and credentials</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4 pb-2">
            <Avatar name={name} src={user?.avatarUrl} size="lg" />
            <div>
              <h4 className="text-xs font-semibold text-[#111111]">{name}</h4>
              <p className="text-[11px] text-[#666666]">{university}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input label="Full Name" value={name} onChange={(e) => setName(e.target.value)} required />
            <Input label="Student Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Academic Details</CardTitle>
          <CardDescription>Helps AgentOS contextualize course timelines and difficulty levels</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input label="University / Institution" value={university} onChange={(e) => setUniversity(e.target.value)} />
            <Input label="Major / Field of Study" value={major} onChange={(e) => setMajor(e.target.value)} />
          </div>
          <Input label="Academic Year" value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} />
          <Textarea label="Academic Bio / Goals" value={bio} onChange={(e) => setBio(e.target.value)} rows={3} />
        </CardContent>
        <CardFooter className="justify-end">
          <Button type="submit" variant="primary" size="sm" isLoading={isSaving}>
            Save Changes
          </Button>
        </CardFooter>
      </Card>
    </form>
  );
};
