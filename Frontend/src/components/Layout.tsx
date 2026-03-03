import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  Satellite, 
  Home, 
  Map, 
  AlertTriangle, 
  FileText, 
  Settings,
  Bell,
  RefreshCw,
  User,
  LogOut,
  UserCircle,
} from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { useData } from '../context/DataContext';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../utils/api';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { refreshData, loading } = useData();
  const { user, isAdmin, isAuthenticated, logout } = useAuth();

  const [monitoredAreas, setMonitoredAreas] = useState<any[]>([]);

  const fetchAreas = () => {
    apiFetch('/api/monitored-areas')
      .then(r => r.json())
      .then(d => setMonitoredAreas(d.areas || []))
      .catch(() => {});
  };

  useEffect(() => {
    fetchAreas();
    const t = setInterval(fetchAreas, 60_000);
    return () => clearInterval(t);
  }, []);

  const activeMonitoringCount = monitoredAreas.filter((a: any) => a.active_monitoring).length;
  const flaggedCount = monitoredAreas.filter((a: any) =>
    (a.detection_history || []).some((h: any) => h.deforestation_detected)
  ).length;

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  // Build nav based on role
  const adminNavigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'Map View', href: '/map', icon: Map },
    { name: 'Flagged Areas', href: '/flagged-areas', icon: AlertTriangle },
    { name: 'Reports', href: '/reports', icon: FileText },
    { name: 'Admin', href: '/admin', icon: Settings },
  ];

  const employeeNavigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'Flagged Areas', href: '/flagged-areas', icon: AlertTriangle },
    { name: 'Reports', href: '/reports', icon: FileText },
    { name: 'Account', href: '/account', icon: UserCircle },
  ];

  const navigation = isAdmin ? adminNavigation : employeeNavigation;

  return (
    <div className="min-h-screen bg-theme-bg transition-colors duration-300">
      {/* Header */}
      <header className="bg-theme-card border-b border-theme-border shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <Link to="/" className="flex items-center space-x-2">
                <div className="p-2 bg-theme-primary/10 rounded-lg">
                  <Satellite className="h-6 w-6 text-theme-primary" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-theme-text-primary">EcoGuard AI</h1>
                  <p className="text-sm text-theme-text-secondary">Environmental Protection System</p>
                </div>
              </Link>
            </div>

            <div className="flex items-center space-x-3">
              <ThemeToggle />

              <button
                onClick={refreshData}
                disabled={loading}
                className="flex items-center space-x-2 px-3 py-2 border border-theme-border rounded-lg hover:bg-theme-hover transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 text-theme-text-secondary ${loading ? 'animate-spin' : ''}`} />
                <span className="text-sm">Refresh</span>
              </button>

              {/* Monitored Areas Badge */}
              <Link
                to="/flagged-areas"
                className="relative flex items-center space-x-2 px-4 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:hover:bg-emerald-900/30 dark:text-emerald-400 rounded-lg transition-colors"
              >
                {flaggedCount > 0 && (
                  <div className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                    {flaggedCount}
                  </div>
                )}
                <Bell className="h-4 w-4" />
                <span className="text-sm font-medium">
                  {activeMonitoringCount} Monitoring
                </span>
              </Link>

              {/* Live indicator */}
              <div className="flex items-center space-x-2 px-3 py-2 bg-theme-primary/10 rounded-lg">
                <div className="h-2 w-2 bg-theme-primary rounded-full animate-pulse"></div>
                <span className="text-sm text-theme-primary font-medium">Live</span>
              </div>

              {/* User info + logout */}
              {isAuthenticated && (
                <div className="flex items-center gap-2 pl-2 border-l border-theme-border">
                  <Link
                    to="/account"
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg hover:bg-theme-hover transition-colors"
                    title="My account"
                  >
                    <User className="h-4 w-4 text-theme-text-secondary" />
                    <span className="text-sm font-medium text-theme-text-primary">
                      {user?.full_name || user?.email}
                    </span>
                    <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${
                      isAdmin
                        ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
                        : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                    }`}>
                      {user?.role}
                    </span>
                  </Link>
                  <button
                    onClick={handleLogout}
                    title="Sign out"
                    className="p-2 rounded-lg text-theme-text-secondary hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                  >
                    <LogOut className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-theme-card border-b border-theme-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center space-x-2 py-4 px-1 border-b-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'border-theme-primary text-theme-primary'
                      : 'border-transparent text-theme-text-secondary hover:text-theme-text-primary hover:border-theme-border'
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>
    </div>
  );
};

export default Layout;