import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Checkbox } from '../../components/ui/Checkbox';
import { Alert } from '../../components/ui/Alert';
import { AuthLayout } from './AuthLayout';
import { errorMessage } from '../../services/api';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState('');
  const { login, isLoading } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const navState = location.state as { from?: string; passwordReset?: boolean; registered?: boolean } | null;
  const redirectTo = navState?.from || '/dashboard';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setError('');
    try {
      const sentTo = await login(email, password);
      navigate('/verify-otp', { state: { email: sentTo, from: redirectTo } });
    } catch (err) {
      setError(errorMessage(err, 'Sign in failed.'));
    }
  };

  return (
    <AuthLayout title="Sign in" description="Welcome back. Sign in to your workspace.">
      <form onSubmit={handleSubmit} className="space-y-4">
        {navState?.registered && !error && (
          <Alert variant="success" title="Account created">
            Sign in to continue. We'll email you a 6-digit code.
          </Alert>
        )}
        {navState?.passwordReset && !error && (
          <Alert variant="success" title="Password changed">
            Sign in with your new password.
          </Alert>
        )}
        {error && (
          <Alert variant="error" title="Couldn't sign in">
            {error}
          </Alert>
        )}
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@university.edu"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <div className="space-y-1.5">
          <Input
            label="Password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        <div className="flex items-center justify-between">
          <Checkbox label="Remember me" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} />
          <Link to="/forgot-password" className="text-sm font-medium text-accent hover:text-accent-hover">
            Forgot password?
          </Link>
        </div>

        <Button type="submit" size="lg" className="w-full" isLoading={isLoading}>
          Sign in
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-fg-subtle">
        New to It's Personal?{' '}
        <Link to="/register" className="font-medium text-accent hover:text-accent-hover">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  );
};
