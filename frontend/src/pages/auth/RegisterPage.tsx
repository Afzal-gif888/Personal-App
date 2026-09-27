import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { AuthLayout } from './AuthLayout';

export const RegisterPage: React.FC = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const { register, isLoading } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError('Use at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setError('');
    await register(name, email);
    navigate('/dashboard', { replace: true });
  };

  return (
    <AuthLayout title="Create your account" description="Set up your workspace in under a minute.">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label="Full name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required />
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@university.edu"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <Input
          label="Password"
          type="password"
          autoComplete="new-password"
          helperText="At least 8 characters."
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <Input
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          error={error}
          required
        />
        <Button type="submit" size="lg" className="w-full" isLoading={isLoading}>
          Create account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-fg-subtle">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-accent hover:text-accent-hover">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
};
