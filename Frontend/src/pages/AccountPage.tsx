import React, { useState } from 'react';
import { User, Shield, Lock, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const AccountPage: React.FC = () => {
  const { user, authFetch } = useAuth();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMsg('');
    setErrorMsg('');

    if (newPassword !== confirmPassword) {
      setErrorMsg('New passwords do not match.');
      return;
    }
    if (newPassword.length < 6) {
      setErrorMsg('New password must be at least 6 characters.');
      return;
    }

    setLoading(true);
    try {
      const res = await authFetch('/api/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail ?? 'Failed to change password.');
        return;
      }

      setSuccessMsg(data.message ?? 'Password changed successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch {
      setErrorMsg('Could not reach server. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const roleBadge =
    user?.role === 'admin'
      ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
      : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300';

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-theme-text-primary">My Account</h1>
        <p className="text-theme-text-secondary mt-1">Manage your profile and security settings</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Profile card */}
        <div className="lg:col-span-1">
          <div className="bg-theme-card border border-theme-border rounded-xl p-6">
            <div className="flex flex-col items-center text-center">
              <div className="w-20 h-20 rounded-full bg-theme-primary/10 flex items-center justify-center mb-4">
                <User className="h-10 w-10 text-theme-primary" />
              </div>
              <h2 className="text-lg font-semibold text-theme-text-primary">
                {user?.full_name}
              </h2>
              <span className={`mt-2 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${roleBadge}`}>
                <Shield className="h-3 w-3" />
                {user?.role === 'admin' ? 'Administrator' : 'Employee'}
              </span>
            </div>

            <div className="mt-6 pt-6 border-t border-theme-border space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-theme-text-secondary">Full Name</span>
                <span className="font-medium text-theme-text-primary">{user?.full_name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-theme-text-secondary">Email</span>
                <span className="font-medium text-theme-text-primary font-mono text-xs">{user?.email}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-theme-text-secondary">Role</span>
                <span className="font-medium text-theme-text-primary capitalize">{user?.role}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-theme-text-secondary">Access</span>
                <span className="font-medium text-theme-text-primary text-right text-xs">
                  {user?.role === 'admin'
                    ? 'Full system access'
                    : 'Dashboard, Reports, Flagged Areas'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Change password form */}
        <div className="lg:col-span-2">
          <div className="bg-theme-card border border-theme-border rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Lock className="h-5 w-5 text-theme-primary" />
              <h3 className="text-lg font-semibold text-theme-text-primary">Change Password</h3>
            </div>

            <form onSubmit={handleChangePassword} className="space-y-5">

              {/* Success */}
              {successMsg && (
                <div className="flex items-center gap-2 px-4 py-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-emerald-700 dark:text-emerald-400 text-sm">
                  <CheckCircle className="h-4 w-4 flex-shrink-0" />
                  <span>{successMsg}</span>
                </div>
              )}

              {/* Error */}
              {errorMsg && (
                <div className="flex items-center gap-2 px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {/* Current password */}
              <div>
                <label className="block text-sm font-medium text-theme-text-primary mb-1.5">
                  Current Password
                </label>
                <div className="relative">
                  <input
                    type={showCurrent ? 'text' : 'password'}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    required
                    placeholder="Enter current password"
                    className="w-full pr-10 pl-4 py-2.5 bg-theme-bg border border-theme-border rounded-lg text-theme-text-primary placeholder:text-theme-text-secondary focus:outline-none focus:ring-2 focus:ring-theme-primary/50 focus:border-theme-primary transition-colors"
                  />
                  <button type="button" onClick={() => setShowCurrent(v => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-theme-text-secondary hover:text-theme-text-primary" tabIndex={-1}>
                    {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* New password */}
              <div>
                <label className="block text-sm font-medium text-theme-text-primary mb-1.5">
                  New Password
                </label>
                <div className="relative">
                  <input
                    type={showNew ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    minLength={6}
                    placeholder="Enter new password (min. 6 characters)"
                    className="w-full pr-10 pl-4 py-2.5 bg-theme-bg border border-theme-border rounded-lg text-theme-text-primary placeholder:text-theme-text-secondary focus:outline-none focus:ring-2 focus:ring-theme-primary/50 focus:border-theme-primary transition-colors"
                  />
                  <button type="button" onClick={() => setShowNew(v => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-theme-text-secondary hover:text-theme-text-primary" tabIndex={-1}>
                    {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Confirm password */}
              <div>
                <label className="block text-sm font-medium text-theme-text-primary mb-1.5">
                  Confirm New Password
                </label>
                <div className="relative">
                  <input
                    type={showConfirm ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    placeholder="Repeat new password"
                    className="w-full pr-10 pl-4 py-2.5 bg-theme-bg border border-theme-border rounded-lg text-theme-text-primary placeholder:text-theme-text-secondary focus:outline-none focus:ring-2 focus:ring-theme-primary/50 focus:border-theme-primary transition-colors"
                  />
                  <button type="button" onClick={() => setShowConfirm(v => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-theme-text-secondary hover:text-theme-text-primary" tabIndex={-1}>
                    {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-2.5 bg-theme-primary hover:bg-theme-primary/90 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
                >
                  {loading ? 'Updating…' : 'Update Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AccountPage;
