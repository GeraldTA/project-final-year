import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Satellite, 
  Home, 
  Map, 
  AlertTriangle, 
  FileText, 
  Settings,
  Bell,
  RefreshCw
} from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { useData } from '../context/DataContext';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { alerts, selectedRegion, setSelectedRegion, refreshData, loading } = useData();
  
  const activeAlerts = alerts.filter(alert => alert.status === 'active');
  const criticalAlerts = activeAlerts.filter(alert => alert.severity === 'critical');

  const navigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'Map View', href: '/map', icon: Map },
    { name: 'Flagged Areas', href: '/flagged-areas', icon: AlertTriangle },
    { name: 'Reports', href: '/reports', icon: FileText },
    { name: 'Admin', href: '/admin', icon: Settings },
  ];

  const regionLabels: Record<Region, string> = {
    bulawayo: 'Bulawayo, Zimbabwe',
    amazon: 'Amazon Rainforest, Brazil',
    congo: 'Congo Basin, DRC',
    borneo: 'Borneo, Malaysia'
  };

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

            <div className="flex items-center space-x-4">
              {/* Region Selector */}
              <select
                value={selectedRegion}
                onChange={(e) => setSelectedRegion(e.target.value as Region)}
                className="px-3 py-2 border border-theme-border rounded-lg bg-theme-card text-theme-text-primary text-sm focus:ring-2 focus:ring-theme-primary focus:border-transparent"
              >
                {Object.entries(regionLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>

              {/* Refresh Button */}
              <ThemeToggle />

              <button
                onClick={refreshData}
                disabled={loading}
                className="flex items-center space-x-2 px-3 py-2 border border-theme-border rounded-lg hover:bg-theme-hover transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 text-theme-text-secondary ${loading ? 'animate-spin' : ''}`} />
                <span className="text-sm">Refresh</span>
              </button>

              {/* Alert Indicator */}
              <Link
                to="/flagged-areas"
                className="relative flex items-center space-x-2 px-4 py-2 bg-red-50 hover:bg-red-100 text-red-700 dark:bg-red-900/20 dark:hover:bg-red-900/30 dark:text-red-400 rounded-lg transition-colors"
              >
                {criticalAlerts.length > 0 && (
                  <div className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                    {criticalAlerts.length}
                  </div>
                )}
                <Bell className="h-4 w-4" />
                <span className="text-sm font-medium">
                  {activeAlerts.length} Active
                </span>
              </Link>

              {/* Status Indicator */}
              <div className="flex items-center space-x-2 px-3 py-2 bg-theme-primary/10 rounded-lg">
                <div className="h-2 w-2 bg-theme-primary rounded-full animate-pulse"></div>
                <span className="text-sm text-theme-primary font-medium">Live</span>
              </div>
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