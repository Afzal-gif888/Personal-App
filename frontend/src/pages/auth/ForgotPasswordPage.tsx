import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, MailCheck } from 'lucide-react';
import { authService } from '../../services/authService';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { AuthLayout } from './AuthLayout';

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    await authService.forgotPassword(email);
    setIsLoading(false);
    setSubmitted(true);
  };

  const backLink = (
    <Link to="/login" className="inline-flex items-center gap-1.5 text-sm font-medium text-fg-subtle hover:text-fg">
      <ArrowLeft className="size-4" />
      Back to sign in
    </Link>
  );

  if (submitted) {
    return (
      <AuthLayout title="Check your email" description={`If an account exists for ${email}, we've sent a link to reset your password.`}>
        <div className="flex items-center gap-3 p-4 rounded-lg border border-success-line bg-success-subtle">
          <MailCheck className="size-5 text-success shrink-0" />
          <p className="text-sm text-fg-muted">The link expires in 30 minutes.</p>
        </div>
        <div className="mt-6">{backLink}</div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Reset your password" description="Enter your account email and we'll send you a reset link.">
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
        <Button type="submit" size="lg" className="w-full" isLoading={isLoading}>
          Send reset link
        </Button>
      </form>
      <div className="mt-6 text-center">{backLink}</div>
    </AuthLayout>
  );
};
