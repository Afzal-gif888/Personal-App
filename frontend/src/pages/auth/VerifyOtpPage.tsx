import React, { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, MailCheck } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { authService } from '../../services/authService';
import { ApiError, errorMessage } from '../../services/api';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import { AuthLayout } from './AuthLayout';

const RESEND_SECONDS = 30;

type Problem = { kind: 'invalid' | 'expired' | 'locked' | 'resend' | 'other'; message: string } | null;

/**
 * Step 2 of sign-in. The password was accepted and the server emailed a 6-digit code; no session
 * exists yet. Only the server decides whether the code is right; this page just collects it.
 */
export const VerifyOtpPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const navState = location.state as { email?: string; from?: string } | null;
  const email = navState?.email ?? '';
  const redirectTo = navState?.from || '/dashboard';
  const verifyOtp = useAuthStore((s) => s.verifyOtp);

  const [otp, setOtp] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [verified, setVerified] = useState(false);
  const [problem, setProblem] = useState<Problem>(null);
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState('');
  const [cooldown, setCooldown] = useState(RESEND_SECONDS);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setTimeout(() => setCooldown((s) => s - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  if (!email) return <Navigate to="/login" replace />;

  const locked = problem?.kind === 'locked';

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^\d{6}$/.test(otp) || verifying || locked) return;
    setVerifying(true);
    setProblem(null);
    setResent('');
    try {
      await verifyOtp(email, otp);
      setVerified(true);
      window.setTimeout(() => navigate(redirectTo, { replace: true }), 600);
    } catch (err) {
      const code = err instanceof ApiError ? err.code : '';
      const kind =
        code === 'OTP_EXPIRED' ? 'expired' : code === 'OTP_TOO_MANY_ATTEMPTS' ? 'locked' : code === 'OTP_INVALID' ? 'invalid' : 'other';
      setProblem({ kind, message: errorMessage(err, "Couldn't verify the code.") });
      setOtp('');
      inputRef.current?.focus();
    } finally {
      setVerifying(false);
    }
  };

  const resend = async () => {
    if (cooldown > 0 || resending) return;
    setResending(true);
    setProblem(null);
    setResent('');
    try {
      setResent(await authService.resendOtp(email));
      setCooldown(RESEND_SECONDS);
      setOtp('');
      inputRef.current?.focus();
    } catch (err) {
      const retryAfter = (err instanceof ApiError && (err.details as { retryAfter?: number } | undefined)?.retryAfter) || 0;
      if (retryAfter) setCooldown(Math.min(retryAfter, 15 * 60));
      setProblem({ kind: 'resend', message: errorMessage(err, "Couldn't send a new code.") });
    } finally {
      setResending(false);
    }
  };

  if (verified) {
    return (
      <AuthLayout title="You're signed in" description="Opening It's Personal…">
        <div className="flex items-center gap-3 p-4 rounded-lg border border-line bg-subtle">
          <CheckCircle2 className="size-5 text-success" />
          <p className="text-sm text-fg-muted">Code verified.</p>
        </div>
      </AuthLayout>
    );
  }

  const problemTitle = {
    invalid: 'Incorrect code',
    expired: 'Code expired',
    locked: 'Too many attempts',
    resend: "Couldn't send a new code",
    other: "Couldn't verify",
  } as const;

  return (
    <AuthLayout title="Verify your email" description="We've sent a 6-digit verification code to:">
      <div className="flex items-center gap-3 p-4 rounded-lg border border-line bg-subtle">
        <MailCheck className="size-5 text-accent shrink-0" />
        <p className="text-sm font-medium text-fg break-all">{email}</p>
      </div>

      <form onSubmit={submit} className="mt-6 space-y-4">
        {problem && (
          <Alert variant={problem.kind === 'expired' ? 'warning' : 'error'} title={problemTitle[problem.kind]}>
            {problem.message}
            {problem.kind === 'expired' && ' Use "Resend OTP" below.'}
          </Alert>
        )}
        {resent && !problem && (
          <Alert variant="success" title="New code sent">
            {resent} The previous code no longer works.
          </Alert>
        )}

        <div className="space-y-1.5">
          <label htmlFor="otp" className="block text-sm font-medium text-fg">
            Verification code
          </label>
          <input
            id="otp"
            ref={inputRef}
            autoFocus
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="\d{6}"
            maxLength={6}
            placeholder="000000"
            value={otp}
            disabled={locked}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
            aria-invalid={problem?.kind === 'invalid'}
            className="w-full h-12 rounded-lg border border-line bg-canvas text-center text-2xl font-mono tracking-[0.5em] text-fg placeholder:text-fg-subtle/40 focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
          />
          <p className="text-xs text-fg-subtle">The code expires in 5 minutes.</p>
        </div>

        <Button type="submit" size="lg" className="w-full" isLoading={verifying} disabled={otp.length !== 6 || locked}>
          Verify OTP
        </Button>
      </form>

      <div className="mt-6 text-center text-sm text-fg-subtle space-y-2">
        {locked ? (
          <Link to="/login" className="font-medium text-accent hover:text-accent-hover">
            Sign in again to get a new code
          </Link>
        ) : (
          <>
            <p>Didn't receive the code? Check your spam folder.</p>
            <Button type="button" variant="secondary" className="w-full" onClick={resend} isLoading={resending} disabled={cooldown > 0}>
              {cooldown > 0 ? `Resend OTP in ${cooldown}s` : 'Resend OTP'}
            </Button>
          </>
        )}
      </div>

      <div className="mt-6 text-center">
        <Link to="/login" className="inline-flex items-center gap-1.5 text-sm font-medium text-fg-subtle hover:text-fg">
          <ArrowLeft className="size-4" />
          Back to sign in
        </Link>
      </div>
    </AuthLayout>
  );
};
