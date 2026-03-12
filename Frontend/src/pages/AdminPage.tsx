import React, { useState, useEffect } from 'react';
import { Users, Settings, Bell, Shield, Database, Activity, X, UserPlus, Loader2, AlertTriangle, CheckCircle, ClipboardCheck, MapPin } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiUrl } from '../utils/api';

interface ApiUser {
  id: string;
  full_name: string;
  email: string;
  role: 'admin' | 'employee';
  is_active: boolean;
  last_login: string | null;
  created_at: string | null;
}

interface DeforestedAreaAlert {
  id: string;
  name: string;
  description?: string;
  last_monitored: string | null;
  latest_forest_loss_percent: number | null;
  detection_history?: {
    deforestation_detected: boolean;
    forest_loss_percent: number;
    before_date: string;
    after_date: string;
  }[];
}

interface DispatchRecord {
  respondedAt: string;
  note: string;
  respondedBy: string;
}

const EMPTY_FORM = { full_name: '', email: '', password: '', role: 'employee' as 'admin' | 'employee' };

const AdminPage: React.FC = () => {
  const { authFetch } = useAuth();
  const [activeTab, setActiveTab] = useState<'users' | 'settings' | 'alerts' | 'system'>('users');

  // ── User list state ──────────────────────────────────────────────────────
  const [users, setUsers] = useState<ApiUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState<string | null>(null);

  // ── Add-user modal state ─────────────────────────────────────────────────
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // ── Deforestation alerts state ────────────────────────────────────────────
  const [deforestedAreas, setDeforestedAreas] = useState<DeforestedAreaAlert[]>([]);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [respondedAlerts, setRespondedAlerts] = useState<Record<string, DispatchRecord>>(() => {
    try { return JSON.parse(localStorage.getItem('ecoguard_dispatched') ?? '{}'); } catch { return {}; }
  });
  const [respondingAlert, setRespondingAlert] = useState<string | null>(null);
  const [dispatchNote, setDispatchNote] = useState('');

  // ── Email notification preferences (stored in DB) ──────────────────────
  const defaultPrefs = { adminEmail: '', onNewDetection: true, weeklyReport: false, monthlyReport: true, annualReport: false, smtpServer: 'smtp.gmail.com', smtpPort: 587, smtpUser: '', smtpPassword: '' };
  const [emailPrefs, setEmailPrefs] = useState(defaultPrefs);
  const [prefsLoading, setPrefsLoading] = useState(false);
  const [prefsSaving, setPrefsSaving] = useState(false);
  const [prefsSaved, setPrefsSaved] = useState(false);
  const [prefsError, setPrefsError] = useState<string | null>(null);
  const [testEmailAddr, setTestEmailAddr] = useState('');
  const [testEmailSending, setTestEmailSending] = useState(false);
  const [testEmailResult, setTestEmailResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [showSmtpPassword, setShowSmtpPassword] = useState(false);

  const fetchEmailPrefs = async () => {
    setPrefsLoading(true);
    setPrefsError(null);
    try {
      const res = await authFetch(apiUrl('/api/auth/notification-preferences'));
      if (!res.ok) throw new Error(`Server responded ${res.status}`);
      const data = await res.json();
      setEmailPrefs({ ...defaultPrefs, ...data });
    } catch (err: any) {
      setPrefsError('Could not load preferences: ' + (err.message ?? 'Unknown error'));
    } finally {
      setPrefsLoading(false);
    }
  };

  const saveEmailPrefs = async () => {
    setPrefsSaving(true);
    setPrefsError(null);
    try {
      const res = await authFetch(apiUrl('/api/auth/notification-preferences'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(emailPrefs),
      });
      if (!res.ok) throw new Error(`Server responded ${res.status}`);
      setPrefsSaved(true);
      setTimeout(() => setPrefsSaved(false), 2500);
    } catch (err: any) {
      setPrefsError('Could not save preferences: ' + (err.message ?? 'Unknown error'));
    } finally {
      setPrefsSaving(false);
    }
  };

  const sendTestEmail = async () => {
    const target = testEmailAddr.trim() || emailPrefs.adminEmail;
    if (!target) { setTestEmailResult({ ok: false, msg: 'Enter an email address to test.' }); return; }
    setTestEmailSending(true);
    setTestEmailResult(null);
    try {
      const res = await authFetch(apiUrl('/api/auth/test-email'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ toEmail: target }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Server responded ${res.status}`);
      setTestEmailResult({ ok: true, msg: data.message ?? `Test email sent to ${target}` });
    } catch (err: any) {
      setTestEmailResult({ ok: false, msg: err.message ?? 'Failed to send test email' });
    } finally {
      setTestEmailSending(false);
    }
  };

  const tabs = [
    { id: 'users', label: 'User Management', icon: Users },
    { id: 'settings', label: 'System Settings', icon: Settings },
    { id: 'alerts', label: 'Alert Configuration', icon: Bell },
    { id: 'system', label: 'System Status', icon: Database }
  ];

  // ── Fetch users ───────────────────────────────────────────────────────────
  const fetchUsers = async () => {
    setUsersLoading(true);
    setUsersError(null);
    try {
      const res = await authFetch(apiUrl('/api/auth/users'));
      if (!res.ok) throw new Error(`Server responded ${res.status}`);
      const data = await res.json();
      setUsers(data.users ?? []);
    } catch (err: any) {
      setUsersError(err.message ?? 'Failed to load users');
    } finally {
      setUsersLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'users') fetchUsers();
    if (activeTab === 'alerts') { fetchDeforestedAreas(); fetchEmailPrefs(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  // ── Fetch deforested areas for alert panel ───────────────────────────────
  const fetchDeforestedAreas = async () => {
    setAlertsLoading(true);
    try {
      const res = await authFetch(apiUrl('/api/monitored-areas/grouped'));
      if (!res.ok) throw new Error('Failed to fetch monitored areas');
      const data = await res.json();
      setDeforestedAreas(data.deforested ?? []);
    } catch (e) {
      console.error('Alert fetch error:', e);
    } finally {
      setAlertsLoading(false);
    }
  };

  const markDispatched = (areaId: string) => {
    const record: DispatchRecord = {
      respondedAt: new Date().toISOString(),
      note: dispatchNote.trim(),
      respondedBy: 'Admin',
    };
    const updated = { ...respondedAlerts, [areaId]: record };
    setRespondedAlerts(updated);
    localStorage.setItem('ecoguard_dispatched', JSON.stringify(updated));
    setRespondingAlert(null);
    setDispatchNote('');
  };

  const unmarkDispatched = (areaId: string) => {
    const updated = { ...respondedAlerts };
    delete updated[areaId];
    setRespondedAlerts(updated);
    localStorage.setItem('ecoguard_dispatched', JSON.stringify(updated));
  };

  // ── Deactivate user ───────────────────────────────────────────────────────
  const handleDeactivate = async (userId: string) => {
    if (!window.confirm('Deactivate this user? They will no longer be able to log in.')) return;
    try {
      const res = await authFetch(apiUrl(`/api/auth/users/${userId}`), { method: 'DELETE' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? 'Failed to deactivate user');
      }
      fetchUsers();
    } catch (err: any) {
      alert(err.message);
    }
  };

  // ── Create user ───────────────────────────────────────────────────────────
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!form.full_name.trim()) { setFormError('Full name is required'); return; }
    if (!form.email.trim()) { setFormError('Email is required'); return; }
    if (form.password.length < 6) { setFormError('Password must be at least 6 characters'); return; }

    setSubmitting(true);
    try {
      const res = await authFetch(apiUrl('/api/auth/users'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail ?? 'Failed to create user');
      setShowModal(false);
      setForm(EMPTY_FORM);
      fetchUsers();
    } catch (err: any) {
      setFormError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const openModal = () => { setForm(EMPTY_FORM); setFormError(null); setShowModal(true); };

  const formatDate = (iso: string | null) => {
    if (!iso) return 'Never';
    return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' });
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Administration Panel</h1>
        <p className="text-gray-600">Manage users, system settings, and monitoring configuration</p>
      </div>

      {/* Tab Navigation */}
      <div className="bg-theme-card rounded-lg shadow-sm">
        <div className="border-b border-theme-border">
          <nav className="flex space-x-8 px-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'border-emerald-500 text-emerald-600'
                    : 'border-transparent text-theme-text-secondary hover:text-theme-text-primary hover:border-theme-border'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* Users Tab */}
          {activeTab === 'users' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">User Management</h3>
                <button
                  onClick={openModal}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm font-medium"
                >
                  <UserPlus className="h-4 w-4" />
                  Add New User
                </button>
              </div>

              {usersError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  {usersError}
                  <button onClick={fetchUsers} className="ml-3 underline">Retry</button>
                </div>
              )}

              {usersLoading ? (
                <div className="flex items-center justify-center py-12 text-gray-500">
                  <Loader2 className="h-6 w-6 animate-spin mr-2" /> Loading users…
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Login</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {users.length === 0 && !usersLoading && (
                        <tr>
                          <td colSpan={5} className="px-6 py-8 text-center text-sm text-gray-500">No users found.</td>
                        </tr>
                      )}
                      {users.map((u) => (
                        <tr key={u.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div>
                              <div className="text-sm font-medium text-gray-900">{u.full_name}</div>
                              <div className="text-sm text-gray-500">{u.email}</div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full capitalize ${
                              u.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'
                            }`}>
                              {u.role}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                              u.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'
                            }`}>
                              {u.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDate(u.last_login)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            {u.is_active && (
                              <button
                                onClick={() => handleDeactivate(u.id)}
                                className="text-red-600 hover:text-red-700"
                              >
                                Deactivate
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* ── Add User Modal ─────────────────────────────────────────────────── */}
          {showModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
              {/* backdrop */}
              <div className="absolute inset-0 bg-black/40" onClick={() => setShowModal(false)} />

              <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md p-6 space-y-5">
                {/* header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <UserPlus className="h-5 w-5 text-emerald-600" />
                    <h2 className="text-lg font-semibold text-gray-900">Add New User</h2>
                  </div>
                  <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                    <X className="h-5 w-5" />
                  </button>
                </div>

                {formError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">
                    {formError}
                  </div>
                )}

                <form onSubmit={handleCreateUser} className="space-y-4">
                  {/* Full name */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                    <input
                      type="text"
                      required
                      value={form.full_name}
                      onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                      placeholder="Jane Smith"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>

                  {/* Email */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
                    <input
                      type="email"
                      required
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      placeholder="jane@example.com"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>

                  {/* Password */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        required
                        value={form.password}
                        onChange={(e) => setForm({ ...form, password: e.target.value })}
                        placeholder="Min. 6 characters"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 pr-16"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-500 hover:text-gray-700 px-1"
                      >
                        {showPassword ? 'Hide' : 'Show'}
                      </button>
                    </div>
                  </div>

                  {/* Role */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                    <select
                      value={form.role}
                      onChange={(e) => setForm({ ...form, role: e.target.value as 'admin' | 'employee' })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option value="employee">Employee</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>

                  {/* actions */}
                  <div className="flex gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowModal(false)}
                      className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-60 text-sm font-medium transition-colors"
                    >
                      {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                      {submitting ? 'Creating…' : 'Create User'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">System Settings</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Detection Sensitivity</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>High (90% confidence threshold)</option>
                      <option>Medium (80% confidence threshold)</option>
                      <option>Low (70% confidence threshold)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Minimum Area Threshold</label>
                    <input
                      type="number"
                      defaultValue="5"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      placeholder="Hectares"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Scan Frequency</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Every 5 days (Sentinel-2 revisit)</option>
                      <option>Daily (when available)</option>
                      <option>Weekly</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Auto-Alert Threshold</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Critical alerts only</option>
                      <option>High priority and above</option>
                      <option>All alerts</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Data Retention</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>1 year</option>
                      <option>2 years</option>
                      <option>5 years</option>
                      <option>Indefinite</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">API Rate Limit</label>
                    <input
                      type="number"
                      defaultValue="1000"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      placeholder="Requests per hour"
                    />
                  </div>
                </div>
              </div>

              <button className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">
                Save Settings
              </button>
            </div>
          )}

          {/* Alerts Tab */}
          {activeTab === 'alerts' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">Alert Configuration</h3>

              {/* ── Deforestation Alert Panel ───────────────────────────── */}
              <div className="bg-white border border-red-200 rounded-lg overflow-hidden shadow-sm">
                <div className="bg-red-700 text-white px-5 py-3 flex items-center gap-3">
                  <AlertTriangle className="h-5 w-5 text-red-200 flex-shrink-0" />
                  <h4 className="font-bold text-base">Deforestation Alerts</h4>
                  <span className="ml-auto text-sm font-medium bg-red-800 px-2 py-0.5 rounded-full">
                    {deforestedAreas.length} active alert{deforestedAreas.length !== 1 ? 's' : ''}
                  </span>
                  <button
                    onClick={fetchDeforestedAreas}
                    className="ml-2 text-red-200 hover:text-white text-xs underline"
                  >
                    Refresh
                  </button>
                </div>

                {alertsLoading ? (
                  <div className="flex items-center justify-center py-10 text-gray-500">
                    <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading alerts…
                  </div>
                ) : deforestedAreas.length === 0 ? (
                  <div className="px-5 py-10 text-center text-gray-500 text-sm">
                    <CheckCircle className="h-10 w-10 text-green-400 mx-auto mb-3" />
                    No deforestation alerts at this time. All monitored areas are clean.
                  </div>
                ) : (
                  <div className="divide-y divide-gray-100">
                    {deforestedAreas.map(area => {
                      const dispatched = respondedAlerts[area.id];
                      const latestDetection = area.detection_history?.[0];
                      const forestLoss = latestDetection?.forest_loss_percent ?? area.latest_forest_loss_percent ?? 0;
                      const isResponding = respondingAlert === area.id;

                      return (
                        <div
                          key={area.id}
                          className={`p-4 ${dispatched ? 'bg-green-50' : 'bg-red-50'}`}
                        >
                          {/* Alert header */}
                          <div className="flex items-start gap-3">
                            <div className="flex-shrink-0 mt-0.5">
                              {dispatched
                                ? <CheckCircle className="h-5 w-5 text-green-600" />
                                : <AlertTriangle className="h-5 w-5 text-red-600" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-semibold text-gray-900">{area.name}</span>
                                {dispatched ? (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                    <ClipboardCheck className="h-3 w-3" /> Responded &amp; Dispatched
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                    <AlertTriangle className="h-3 w-3" /> Awaiting Response
                                  </span>
                                )}
                              </div>
                              {area.description && (
                                <p className="text-xs text-gray-500 mt-0.5">{area.description}</p>
                              )}
                              <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1 text-xs text-gray-600">
                                {forestLoss > 0 && (
                                  <span className="text-red-700 font-medium">
                                    Forest Loss: {forestLoss.toFixed(2)}%
                                  </span>
                                )}
                                {latestDetection?.before_date && (
                                  <span>
                                    Detection: {new Date(latestDetection.before_date).toLocaleDateString()} → {new Date(latestDetection.after_date).toLocaleDateString()}
                                  </span>
                                )}
                                {area.last_monitored && (
                                  <span>
                                    Last scan: {new Date(area.last_monitored).toLocaleDateString()}
                                  </span>
                                )}
                              </div>

                              {/* Dispatched info */}
                              {dispatched && (
                                <div className="mt-2 bg-green-100 border border-green-200 rounded px-3 py-2 text-xs text-green-800">
                                  <span className="font-semibold">Response recorded</span> by {dispatched.respondedBy} on {new Date(dispatched.respondedAt).toLocaleString()}
                                  {dispatched.note && (
                                    <p className="mt-1 text-green-700">Note: {dispatched.note}</p>
                                  )}
                                </div>
                              )}
                            </div>

                            {/* Action buttons */}
                            <div className="flex-shrink-0 flex flex-col gap-1.5">
                              {!dispatched && !isResponding && (
                                <button
                                  onClick={() => { setRespondingAlert(area.id); setDispatchNote(''); }}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-medium hover:bg-emerald-700 transition-colors"
                                >
                                  <ClipboardCheck className="h-3.5 w-3.5" />
                                  Mark Responded
                                </button>
                              )}
                              {dispatched && (
                                <button
                                  onClick={() => unmarkDispatched(area.id)}
                                  className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-200 transition-colors"
                                >
                                  Undo
                                </button>
                              )}
                              <a
                                href="/map"
                                className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700 transition-colors"
                              >
                                <MapPin className="h-3.5 w-3.5" />
                                View on Map
                              </a>
                            </div>
                          </div>

                          {/* Inline dispatch form */}
                          {isResponding && (
                            <div className="mt-3 ml-8 border border-emerald-200 rounded-lg p-3 bg-white space-y-2">
                              <p className="text-xs font-semibold text-gray-700">Confirm field response &amp; dispatch</p>
                              <textarea
                                rows={2}
                                placeholder="Optional: add notes (team dispatched, ETA, contact person…)"
                                value={dispatchNote}
                                onChange={e => setDispatchNote(e.target.value)}
                                className="w-full text-xs border border-gray-300 rounded px-2 py-1.5 focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none"
                              />
                              <div className="flex gap-2">
                                <button
                                  onClick={() => markDispatched(area.id)}
                                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded text-xs font-medium hover:bg-emerald-700 transition-colors"
                                >
                                  <CheckCircle className="h-3.5 w-3.5" />
                                  Confirm — Team Dispatched
                                </button>
                                <button
                                  onClick={() => setRespondingAlert(null)}
                                  className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded text-xs hover:bg-gray-200 transition-colors"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
              {/* ── Email Notification Preferences ─────────────────────── */}
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
                <div className="bg-gray-700 text-white px-5 py-3 flex items-center gap-3">
                  <Bell className="h-5 w-5 text-gray-300 flex-shrink-0" />
                  <h4 className="font-bold text-base">Email Notification Preferences</h4>
                </div>
                <div className="p-5 space-y-5">

                  {prefsLoading ? (
                    <div className="flex items-center justify-center py-8 text-gray-500">
                      <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading preferences…
                    </div>
                  ) : (<>

                  {/* Admin email address */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Admin Email Address
                      <span className="ml-1 text-xs font-normal text-gray-500">(reports &amp; alerts will be sent here)</span>
                    </label>
                    <input
                      type="email"
                      placeholder="e.g. admin@example.com"
                      value={emailPrefs.adminEmail}
                      onChange={e => setEmailPrefs({ ...emailPrefs, adminEmail: e.target.value })}
                      className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>

                  {/* Instant detection alert */}
                  <div className="border border-amber-200 bg-amber-50 rounded-lg p-4">
                    <h5 className="text-sm font-semibold text-amber-900 mb-3">🛰️ Detection Alerts</h5>
                    <label className="flex items-start gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={emailPrefs.onNewDetection}
                        onChange={e => setEmailPrefs({ ...emailPrefs, onNewDetection: e.target.checked })}
                        className="mt-0.5 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                      />
                      <div>
                        <span className="text-sm font-medium text-gray-800">Send email immediately when a new deforestation is detected</span>
                        <p className="text-xs text-gray-500 mt-0.5">You will receive an alert email as soon as the ML model flags a new area with deforestation.</p>
                      </div>
                    </label>
                  </div>

                  {/* Periodic reports */}
                  <div className="border border-blue-200 bg-blue-50 rounded-lg p-4">
                    <h5 className="text-sm font-semibold text-blue-900 mb-3">📋 Periodic Report Emails</h5>
                    <div className="space-y-3">
                      <label className="flex items-start gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={emailPrefs.weeklyReport}
                          onChange={e => setEmailPrefs({ ...emailPrefs, weeklyReport: e.target.checked })}
                          className="mt-0.5 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                        />
                        <div>
                          <span className="text-sm font-medium text-gray-800">Weekly summary report</span>
                          <p className="text-xs text-gray-500 mt-0.5">A weekly digest of all detections, scans performed, and area status changes.</p>
                        </div>
                      </label>

                      <label className="flex items-start gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={emailPrefs.monthlyReport}
                          onChange={e => setEmailPrefs({ ...emailPrefs, monthlyReport: e.target.checked })}
                          className="mt-0.5 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                        />
                        <div>
                          <span className="text-sm font-medium text-gray-800">Monthly summary report</span>
                          <p className="text-xs text-gray-500 mt-0.5">A monthly overview of forest cover trends, total deforested areas, and response records.</p>
                        </div>
                      </label>

                      <label className="flex items-start gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={emailPrefs.annualReport}
                          onChange={e => setEmailPrefs({ ...emailPrefs, annualReport: e.target.checked })}
                          className="mt-0.5 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                        />
                        <div>
                          <span className="text-sm font-medium text-gray-800">Annual report</span>
                          <p className="text-xs text-gray-500 mt-0.5">A full annual deforestation analysis report sent at the end of each year.</p>
                        </div>
                      </label>
                    </div>
                  </div>

                  {/* SMTP configuration */}
                  <div className="border border-gray-200 bg-gray-50 rounded-lg p-4">
                    <h5 className="text-sm font-semibold text-gray-800 mb-3">⚙️ SMTP Configuration</h5>
                    <p className="text-xs text-gray-500 mb-3">
                      For Gmail, use <strong>smtp.gmail.com</strong> port <strong>587</strong> with your Gmail address and a{' '}
                      <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" className="text-emerald-600 underline">Gmail App Password</a>{' '}
                      (requires 2-Step Verification enabled on your Google account).
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">SMTP Server</label>
                        <input
                          type="text"
                          value={emailPrefs.smtpServer}
                          onChange={e => setEmailPrefs({ ...emailPrefs, smtpServer: e.target.value })}
                          placeholder="smtp.gmail.com"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">SMTP Port</label>
                        <input
                          type="number"
                          value={emailPrefs.smtpPort}
                          onChange={e => setEmailPrefs({ ...emailPrefs, smtpPort: parseInt(e.target.value) || 587 })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">SMTP Username (Gmail address)</label>
                        <input
                          type="email"
                          value={emailPrefs.smtpUser}
                          onChange={e => setEmailPrefs({ ...emailPrefs, smtpUser: e.target.value })}
                          placeholder="you@gmail.com"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">App Password</label>
                        <div className="relative">
                          <input
                            type={showSmtpPassword ? 'text' : 'password'}
                            value={emailPrefs.smtpPassword}
                            onChange={e => setEmailPrefs({ ...emailPrefs, smtpPassword: e.target.value })}
                            placeholder="Gmail App Password"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 pr-14"
                          />
                          <button
                            type="button"
                            onClick={() => setShowSmtpPassword(p => !p)}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-500 hover:text-gray-700 px-1"
                          >
                            {showSmtpPassword ? 'Hide' : 'Show'}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Send Test Email */}
                  <div className="border border-indigo-200 bg-indigo-50 rounded-lg p-4">
                    <h5 className="text-sm font-semibold text-indigo-900 mb-2">📧 Send Test Email</h5>
                    <p className="text-xs text-gray-600 mb-3">Save your SMTP settings first, then send a test detection-alert email to verify everything is working.</p>
                    <div className="flex gap-2 items-center flex-wrap">
                      <input
                        type="email"
                        value={testEmailAddr}
                        onChange={e => setTestEmailAddr(e.target.value)}
                        placeholder={emailPrefs.adminEmail || 'recipient@example.com'}
                        className="flex-1 min-w-0 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                      <button
                        onClick={sendTestEmail}
                        disabled={testEmailSending || prefsSaving}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-60 transition-colors whitespace-nowrap"
                      >
                        {testEmailSending && <Loader2 className="h-4 w-4 animate-spin" />}
                        {testEmailSending ? 'Sending…' : 'Send Test Email'}
                      </button>
                    </div>
                    {testEmailResult && (
                      <p className={`mt-2 text-sm font-medium ${testEmailResult.ok ? 'text-emerald-700' : 'text-red-700'}`}>
                        {testEmailResult.ok ? '✓ ' : '✗ '}{testEmailResult.msg}
                      </p>
                    )}
                  </div>

                  {/* Save button */}
                  {prefsError && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm">{prefsError}</div>
                  )}
                  <div className="flex items-center gap-3">
                    <button
                      onClick={saveEmailPrefs}
                      disabled={prefsSaving || prefsLoading}
                      className="inline-flex items-center gap-2 px-5 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-60 transition-colors"
                    >
                      {prefsSaving && <Loader2 className="h-4 w-4 animate-spin" />}
                      {prefsSaving ? 'Saving…' : 'Save Preferences'}
                    </button>
                    {prefsSaved && (
                      <span className="text-sm text-emerald-600 font-medium">✓ Saved to database</span>
                    )}
                  </div>
                  </>)}
                </div>
              </div>
            </div>
          )}

          {/* System Tab */}
          {activeTab === 'system' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">System Status</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      <span className="font-medium text-green-800">Satellite Data Feed</span>
                    </div>
                    <p className="text-sm text-green-700">Connected • Last update: 2 hours ago</p>
                  </div>

                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      <span className="font-medium text-green-800">AI Processing Engine</span>
                    </div>
                    <p className="text-sm text-green-700">Operational • 99.8% uptime</p>
                  </div>

                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                      <span className="font-medium text-yellow-800">Database Storage</span>
                    </div>
                    <p className="text-sm text-yellow-700">78% capacity • Consider cleanup</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-medium text-gray-900 mb-3">Processing Statistics</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Images Processed Today:</span>
                        <span className="font-medium">1,247</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Alerts Generated:</span>
                        <span className="font-medium">23</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Average Processing Time:</span>
                        <span className="font-medium">2.3 seconds</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Queue Size:</span>
                        <span className="font-medium">12 images</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-medium text-gray-900 mb-3">System Resources</h4>
                    <div className="space-y-3">
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600">CPU Usage</span>
                          <span className="font-medium">34%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div className="bg-blue-500 h-2 rounded-full" style={{ width: '34%' }}></div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600">Memory Usage</span>
                          <span className="font-medium">67%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div className="bg-yellow-500 h-2 rounded-full" style={{ width: '67%' }}></div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600">Storage Usage</span>
                          <span className="font-medium">78%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div className="bg-orange-500 h-2 rounded-full" style={{ width: '78%' }}></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">System Configuration</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Detection Model</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>ResNet-50 (Current)</option>
                      <option>U-Net Segmentation</option>
                      <option>EfficientNet-B7</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Processing Priority</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Real-time (High CPU)</option>
                      <option>Balanced</option>
                      <option>Batch Processing (Low CPU)</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Backup Frequency</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Daily</option>
                      <option>Weekly</option>
                      <option>Monthly</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Log Level</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Error</option>
                      <option>Warning</option>
                      <option>Info</option>
                      <option>Debug</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Alerts Tab */}
          {activeTab === 'alerts' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">Alert Configuration</h3>
              
            </div>
          )}

          {/* System Tab */}
          {activeTab === 'system' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">System Monitoring</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                  <Activity className="h-8 w-8 text-green-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-green-600">99.8%</div>
                  <div className="text-sm text-green-700">System Uptime</div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                  <Shield className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-blue-600">1,247</div>
                  <div className="text-sm text-blue-700">Images Processed Today</div>
                </div>

                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 text-center">
                  <Database className="h-8 w-8 text-purple-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-purple-600">2.3TB</div>
                  <div className="text-sm text-purple-700">Data Stored</div>
                </div>
              </div>

              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-3">Recent System Events</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-gray-700">Model retrained with new data</span>
                    <span className="text-gray-500">2 hours ago</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-gray-700">Database backup completed</span>
                    <span className="text-gray-500">6 hours ago</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-gray-700">New satellite data ingested</span>
                    <span className="text-gray-500">8 hours ago</span>
                  </div>
                  <div className="flex justify-between items-center py-2">
                    <span className="text-gray-700">System maintenance completed</span>
                    <span className="text-gray-500">1 day ago</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminPage;