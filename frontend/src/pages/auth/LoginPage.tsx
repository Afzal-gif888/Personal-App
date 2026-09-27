import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Checkbox } from '../../components/ui/Checkbox';
import { Alert } from '../../components/ui/Alert';
import { AuthLayout } from './AuthLayout';

const DEMO = { email: 'student@agentos.demo', password: 'Demo123!' };

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const { login, isLoading } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = (location.state as { from?: string } | null)?.from || '/dashboard';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    await login(email, password);
    navigate(redirectTo, { replace: true });
  };

  return (
    <AuthLayout title="Sign in" description="Welcome back. Sign in to your workspace.">
      <Alert
        variant="info"
        title="Demo account"
        className="mb-6"
        action={
          <Button
            variant="secondary"
            size="xs"
            onClick={() => {
              setEmail(DEMO.email);
              setPassword(DEMO.password);
            }}
          >
            Use
          </Button>
        }
      >
        <span className="font-mono text-xs">{DEMO.email}</span>
      </Alert>

      <form onSubmit={handleSubmit} className="space-y-4">
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
        New to AgentOS?{' '}
        <Link to="/register" className="font-medium text-accent hover:text-accent-hover">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  );
};
