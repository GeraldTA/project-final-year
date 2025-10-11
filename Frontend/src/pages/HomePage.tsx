import React from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, AlertTriangle, MapPin, Activity, ArrowRight } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { useData } from '../context/DataContext';

const HomePage: React.FC = () => {
  const { alerts, detectionData, loading } = useData();

  if (loading || !detectionData) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-theme-card rounded-lg p-6 shadow-sm animate-pulse">
              <div className="h-4 bg-theme-hover rounded w-3/4 mb-4"></div>
              <div className="h-8 bg-theme-hover rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const activeAlerts = alerts.filter(alert => alert.status === 'active');
  const criticalAlerts = activeAlerts.filter(alert => alert.severity === 'critical');
  const recentAlerts = alerts.slice(0, 5);

  const weeklyChange = detectionData.trendsData.length > 1 
    ? detectionData.trendsData[detectionData.trendsData.length - 1].deforestation - 
      detectionData.trendsData[detectionData.trendsData.length - 2].deforestation
    : 0;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-theme-card rounded-lg p-6 shadow-sm border-l-4 border-red-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-theme-text-secondary">Critical Alerts</p>
              <p className="text-3xl font-bold text-red-600">{criticalAlerts.length}</p>
            </div>
            <AlertTriangle className="h-8 w-8 text-red-500" />
          </div>
          <div className="mt-4">
            <Link 
              to="/flagged-areas" 
              className="text-sm text-red-600 hover:text-red-700 font-medium flex items-center"
            >
              View Details <ArrowRight className="h-3 w-3 ml-1" />
            </Link>
          </div>
        </div>

        <div className="bg-theme-card rounded-lg p-6 shadow-sm border-l-4 border-orange-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-theme-text-secondary">Active Cases</p>
              <p className="text-3xl font-bold text-orange-600">{activeAlerts.length}</p>
            </div>
            <Activity className="h-8 w-8 text-orange-500" />
          </div>
          <div className="mt-4">
            <span className="text-sm text-theme-text-secondary">
              {alerts.filter(a => a.status === 'investigating').length} under investigation
            </span>
          </div>
        </div>

        <div className="bg-theme-card rounded-lg p-6 shadow-sm border-l-4 border-emerald-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-theme-text-secondary">Forest Loss</p>
              <p className="text-3xl font-bold text-emerald-600">{detectionData.deforestedArea.toLocaleString()}</p>
              <p className="text-xs text-theme-text-secondary">hectares</p>
            </div>
            <TrendingUp className="h-8 w-8 text-emerald-500" />
          </div>
          <div className="mt-4">
            <span className={`text-sm font-medium ${weeklyChange > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
              {weeklyChange > 0 ? '+' : ''}{weeklyChange.toFixed(1)}% this week
            </span>
          </div>
        </div>

        <div className="bg-theme-card rounded-lg p-6 shadow-sm border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-theme-text-secondary">Mining Activity</p>
              <p className="text-3xl font-bold text-blue-600">{detectionData.miningArea.toLocaleString()}</p>
              <p className="text-xs text-theme-text-secondary">hectares</p>
            </div>
            <MapPin className="h-8 w-8 text-blue-500" />
          </div>
          <div className="mt-4">
            <Link 
              to="/map" 
              className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center"
            >
              View on Map <ArrowRight className="h-3 w-3 ml-1" />
            </Link>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trends Chart */}
        <div className="bg-theme-card rounded-lg p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-theme-text-primary mb-4">Activity Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={detectionData.trendsData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" />
              <YAxis />
              <Tooltip />
              <Line 
                type="monotone" 
                dataKey="deforestation" 
                stroke="#DC2626" 
                strokeWidth={2}
                name="Deforestation (ha)"
              />
              <Line 
                type="monotone" 
                dataKey="mining" 
                stroke="#2563EB" 
                strokeWidth={2}
                name="Mining (ha)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Risk Zones Chart */}
        <div className="bg-theme-card rounded-lg p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-theme-text-primary mb-4">Risk Zone Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={detectionData.riskZones}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar 
                dataKey="area" 
                fill="#059669"
                name="Area (hectares)"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Alerts */}
      <div className="bg-theme-card rounded-lg shadow-sm">
        <div className="px-6 py-4 border-b border-theme-border">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-theme-text-primary">Recent Alerts</h3>
            <Link 
              to="/flagged-areas"
              className="text-sm text-emerald-600 hover:text-emerald-700 font-medium flex items-center"
            >
              View All <ArrowRight className="h-3 w-3 ml-1" />
            </Link>
          </div>
        </div>
        <div className="divide-y divide-theme-border">
          {recentAlerts.map((alert) => (
            <Link
              key={alert.id}
              to={`/case/${alert.id}`}
              className="block px-6 py-4 hover:bg-theme-hover transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`w-3 h-3 rounded-full ${
                    alert.severity === 'critical' ? 'bg-red-500' :
                    alert.severity === 'high' ? 'bg-orange-500' :
                    alert.severity === 'medium' ? 'bg-yellow-500' :
                    'bg-blue-500'
                  }`}></div>
                  <div>
                    <p className="text-sm font-medium text-theme-text-primary">
                      {alert.type.charAt(0).toUpperCase() + alert.type.slice(1)} Detected
                    </p>
                    <p className="text-xs text-theme-text-secondary">{alert.location.address}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-theme-text-primary">{alert.area} ha</p>
                  <p className="text-xs text-theme-text-secondary">
                    {new Date(alert.detectedAt).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};

export default HomePage;