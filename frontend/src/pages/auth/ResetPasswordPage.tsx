import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { authService } from '../../services/authService';
import { errorMessage } from '../../services/api';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import { AuthLayout } from './AuthLayout';

/** Target of the link in the password-reset email: /reset-password?token=… */
export const ResetPasswordPage: React.FC = () => {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) return setError('Use at least 8 characters.');
    if (password !== confirm) return setError("The two passwords don't match.");
    setIsLoading(true);
    try {
      await authService.resetPassword(token, password);
      navigate('/login', { replace: true, state: { passwordReset: true } });
    } catch (err) {
      setError(errorMessage(err, 'This link is no longer valid. Request a new one.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout title="Choose a new password" description="This signs you out on every other device.">
      {!token ? (
        <Alert variant="error" title="Invalid link">
          This link is missing its token. Request a new reset email.
        </Alert>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <Alert variant="error" title="Couldn't reset your password">
              {error}{' '}
              <Link to="/forgot-password" className="font-medium underline">
                Request a new link
              </Link>
            </Alert>
          )}
          <Input
            label="New password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Input
            label="Confirm new password"
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
          />
          <Button type="submit" size="lg" className="w-full" isLoading={isLoading}>
            Change password
          </Button>
        </form>
      )}
      <div className="mt-6 text-center">
        <Link to="/login" className="inline-flex items-center gap-1.5 text-sm font-medium text-fg-subtle hover:text-fg">
          <ArrowLeft className="size-4" />
          Back to sign in
        </Link>
      </div>
    </AuthLayout>
  );
};
