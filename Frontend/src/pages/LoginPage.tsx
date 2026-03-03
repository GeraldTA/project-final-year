import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Satellite, Lock, User, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { useAuth, AuthUser } from '../context/AuthContext';
import { apiUrl } from '../utils/api';

const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Redirect to wherever the user was trying to go, or to dashboard
  const from = (location.state as any)?.from?.pathname ?? '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // FastAPI OAuth2 form login expects application/x-www-form-urlencoded
      const body = new URLSearchParams();
      body.append('username', email.trim().toLowerCase()); // backend treats 'username' field as email
      body.append('password', password);

      const res = await fetch(apiUrl('/api/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? 'Invalid credentials');
        return;
      }

      const data = await res.json();
      const user: AuthUser = { email: data.email, full_name: data.full_name, role: data.role };
      login(data.access_token, user);

      // Navigate to intended route (or role-appropriate default)
      const target = from === '/login' ? '/' : from;
      navigate(target, { replace: true });
    } catch {
      setError('Could not reach server. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-theme-bg flex items-center justify-center px-4 transition-colors duration-300">
      <div className="w-full max-w-md">
        {/* Card */}
        <div className="bg-theme-card border border-theme-border rounded-2xl shadow-xl p-8">

          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="p-3 bg-theme-primary/10 rounded-2xl mb-4">
              <Satellite className="h-10 w-10 text-theme-primary" />
            </div>
            <h1 className="text-2xl font-bold text-theme-text-primary">EcoGuard AI</h1>
            <p className="text-sm text-theme-text-secondary mt-1">Environmental Protection System</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">

            {/* Error banner */}
            {error && (
              <div className="flex items-center gap-2 px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-theme-text-primary mb-1.5">
                Email
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-theme-text-secondary" />
                <input
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="Enter your email address"
                  className="w-full pl-10 pr-4 py-2.5 bg-theme-bg border border-theme-border rounded-lg text-theme-text-primary placeholder:text-theme-text-secondary focus:outline-none focus:ring-2 focus:ring-theme-primary/50 focus:border-theme-primary transition-colors"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-theme-text-primary mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-theme-text-secondary" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="Enter your password"
                  className="w-full pl-10 pr-10 py-2.5 bg-theme-bg border border-theme-border rounded-lg text-theme-text-primary placeholder:text-theme-text-secondary focus:outline-none focus:ring-2 focus:ring-theme-primary/50 focus:border-theme-primary transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-theme-text-secondary hover:text-theme-text-primary transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-theme-primary hover:bg-theme-primary/90 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>

          {/* Hint */}
          <p className="mt-6 text-center text-xs text-theme-text-secondary">
            Default: <span className="font-mono">admin@ecoguard.ai / admin123</span>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
