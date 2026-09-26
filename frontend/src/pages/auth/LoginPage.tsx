import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Lock, Mail } from 'lucide-react';
import { Logo } from '../../components/ui/Logo';
import { useAuthStore } from '../../stores/authStore';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Checkbox } from '../../components/ui/Checkbox';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('student@agentos.demo');
  const [password, setPassword] = useState('Demo123!');
  const [rememberMe, setRememberMe] = useState(true);
  const { login, isLoading } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    await login(email, password);
    navigate('/dashboard');
  };

  const fillDemoAccount = () => {
    setEmail('student@agentos.demo');
    setPassword('Demo123!');
  };

  return (
    <div className="min-h-screen bg-white flex flex-col justify-center items-center px-4 py-12 text-left">
      <div className="w-full max-w-sm space-y-6">
        {/* Brand Logo */}
        <div className="flex flex-col items-center text-center space-y-3">
          <Logo size="xl" />
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[#111111]">AgentOS</h1>
            <p className="text-xs text-[#666666] mt-0.5">Personal AI Operating System for Students</p>
          </div>
        </div>

        {/* Demo Banner Helper */}
        <div className="p-3 rounded-lg border border-[#EAEAEA] bg-[#F7F7F7] space-y-2 text-xs">
          <div className="flex items-center justify-between font-medium text-[#111111]">
            <span>Demo Account Credentials</span>
            <button
              type="button"
              onClick={fillDemoAccount}
              className="text-[11px] font-semibold text-black underline cursor-pointer"
            >
              Fill Demo Data
            </button>
          </div>
          <div className="text-[11px] text-[#666666] font-mono space-y-0.5">
            <div>Email: student@agentos.demo</div>
            <div>Password: Demo123!</div>
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Email address"
            type="email"
            placeholder="student@university.edu"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            leftIcon={<Mail className="w-4 h-4" />}
            required
          />

          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            leftIcon={<Lock className="w-4 h-4" />}
            required
          />

          <div className="flex items-center justify-between text-xs pt-1">
            <Checkbox
              label="Remember me"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            />
            <Link
              to="/forgot-password"
              className="text-xs text-[#666666] hover:text-[#111111] hover:underline"
            >
              Forgot password?
            </Link>
          </div>

          <Button
            type="submit"
            variant="primary"
            className="w-full h-10 mt-2"
            isLoading={isLoading}
            rightIcon={<ArrowRight className="w-4 h-4" />}
          >
            Sign in
          </Button>
        </form>

        <p className="text-center text-xs text-[#666666]">
          Don't have an account?{' '}
          <Link to="/register" className="font-semibold text-[#111111] hover:underline">
            Create account
          </Link>
        </p>
      </div>
    </div>
  );
};
