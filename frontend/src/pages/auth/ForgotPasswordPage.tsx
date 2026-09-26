import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, Mail, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { authService } from '../../services/authService';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';

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

  return (
    <div className="min-h-screen bg-white flex flex-col justify-center items-center px-4 py-12 text-left">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-black text-white font-bold">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[#111111]">Reset Password</h1>
          <p className="text-xs text-[#666666]">Enter your student email to receive reset instructions</p>
        </div>

        {submitted ? (
          <div className="p-4 rounded-lg border border-emerald-200 bg-emerald-50/60 text-emerald-900 space-y-3 text-xs text-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
            <div className="font-semibold text-sm">Reset link sent!</div>
            <p className="text-emerald-800 text-[11px]">
              We've dispatched password recovery steps to <span className="font-semibold">{email}</span>.
            </p>
            <Link to="/login" className="inline-block mt-2 font-semibold text-black underline">
              Return to Login
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Student email address"
              type="email"
              placeholder="student@university.edu"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              leftIcon={<Mail className="w-4 h-4" />}
              required
            />

            <Button type="submit" variant="primary" className="w-full h-10 mt-2" isLoading={isLoading}>
              Send reset link
            </Button>
          </form>
        )}

        <div className="text-center pt-2">
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 text-xs text-[#666666] hover:text-[#111111]"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to sign in
          </Link>
        </div>
      </div>
    </div>
  );
};
