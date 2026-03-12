import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, AlertTriangle, MapPin, Activity, ArrowRight, Eye } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend, Cell } from 'recharts';
import { useData } from '../context/DataContext';
import { apiFetch } from '../utils/api';

interface MonitoredArea {
  id: string;
  name: string;
  description: string;
  coordinates: [number, number][];
  created_at: string;
  last_monitored: string | null;
  monitoring_enabled: boolean;
  active_monitoring: boolean;
  detection_count: number;
  detection_history: DetectionRecord[];
}

interface DetectionRecord {
  timestamp: string;
  before_date: string;
  after_date: string;
  deforestation_detected: boolean;
  forest_loss_percent: number;
  vegetation_trend: string;
}

const HomePage: React.FC = () => {
  const { alerts, detectionData, loading } = useData();
  const [monitoredAreas, setMonitoredAreas] = useState<MonitoredArea[]>([]);
  const [loadingAreas, setLoadingAreas] = useState(true);

  useEffect(() => {
    const fetchMonitoredAreas = async () => {
      try {
        const res = await apiFetch('/api/monitored-areas');
        if (res.ok) {
          const data = await res.json();
          setMonitoredAreas(data.areas || []);
        }
      } catch (e) {
        console.error('Failed to fetch monitored areas:', e);
      } finally {
        setLoadingAreas(false);
      }
    };

    fetchMonitoredAreas();
  }, []);

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
  
  // Calculate stats from monitored areas
  const areasWithDeforestation = monitoredAreas.filter(area => 
    area.detection_history?.[0]?.deforestation_detected
  );
  const activeMonitoringCount = monitoredAreas.filter(area => area.active_monitoring).length;

  const weeklyChange = detectionData.trendsData.length > 1 
    ? detectionData.trendsData[detectionData.trendsData.length - 1].deforestation - 
      detectionData.trendsData[detectionData.trendsData.length - 2].deforestation
    : 0;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-theme-card rounded-lg p-6 shadow-sm border-l-4 border-indigo-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-theme-text-secondary">Monitored Areas</p>
              <p className="text-3xl font-bold text-indigo-600">{monitoredAreas.length}</p>
            </div>
            <MapPin className="h-8 w-8 text-indigo-500" />
          </div>
          <div className="mt-4">
            <Link 
              to="/flagged-areas" 
              className="text-sm text-indigo-600 hover:text-indigo-700 font-medium flex items-center"
            >
              View All <ArrowRight className="h-3 w-3 ml-1" />
            </Link>
          </div>
        </div>

        <div className="bg-theme-card rounded-lg p-6 shadow-sm border-l-4 border-red-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-theme-text-secondary">Deforestation Detected</p>
              <p className="text-3xl font-bold text-red-600">{areasWithDeforestation.length}</p>
            </div>
            <AlertTriangle className="h-8 w-8 text-red-500" />
          </div>
          <div className="mt-4">
            <span className="text-sm text-theme-text-secondary">
              of {monitoredAreas.length} monitored areas
            </span>
          </div>
        </div>

        <div className="bg-theme-card rounded-lg p-6 shadow-sm border-l-4 border-emerald-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-theme-text-secondary">Active Monitoring</p>
              <p className="text-3xl font-bold text-emerald-600">{activeMonitoringCount}</p>
            </div>
            <Activity className="h-8 w-8 text-emerald-500" />
          </div>
          <div className="mt-4">
            <span className="text-sm text-theme-text-secondary">
              Auto-checking every 5 days
            </span>
          </div>
        </div>

        <div className="bg-theme-card rounded-lg p-6 shadow-sm border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-theme-text-secondary">Total Detections</p>
              <p className="text-3xl font-bold text-blue-600">
                {monitoredAreas.reduce((sum, area) => sum + area.detection_count, 0)}
              </p>
            </div>
            <TrendingUp className="h-8 w-8 text-blue-500" />
          </div>
          <div className="mt-4">
            <Link 
              to="/map" 
              className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center"
            >
              Run Detection <ArrowRight className="h-3 w-3 ml-1" />
            </Link>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Activity Trends Chart */}
        <div className="bg-theme-card rounded-lg p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-theme-text-primary mb-1">Activity Trends</h3>
          <p className="text-xs text-theme-text-secondary mb-4">Forest loss (%) detected per week across all monitored areas</p>
          {detectionData.trendsData.length === 0 ? (
            <div className="flex items-center justify-center h-[300px] text-theme-text-secondary text-sm">
              No detection history yet. Start monitoring areas to see trends.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={detectionData.trendsData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value: number, name: string) => [
                  name === 'deforestation' ? `${value}%` : value,
                  name === 'deforestation' ? 'Forest Loss (%)' : 'Scans'
                ]} />
                <Legend formatter={(value) => value === 'deforestation' ? 'Forest Loss (%)' : 'Scans'} />
                <Line
                  type="monotone"
                  dataKey="deforestation"
                  stroke="#DC2626"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  name="deforestation"
                />
                <Line
                  type="monotone"
                  dataKey="scans"
                  stroke="#2563EB"
                  strokeWidth={2}
                  strokeDasharray="4 2"
                  dot={{ r: 3 }}
                  name="scans"
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Risk Zone Distribution Chart */}
        <div className="bg-theme-card rounded-lg p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-theme-text-primary mb-1">Risk Zone Distribution</h3>
          <p className="text-xs text-theme-text-secondary mb-4">Monitored areas ranked by deforestation risk level</p>
          {detectionData.riskZones.length === 0 ? (
            <div className="flex items-center justify-center h-[300px] text-theme-text-secondary text-sm">
              No monitored areas with detection history yet.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={detectionData.riskZones} layout="vertical" margin={{ left: 10, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fontSize: 11 }} unit=" ha" />
                <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value: number) => [`${value} ha`, 'Area']} />
                <Bar dataKey="area" name="Area (ha)" radius={[0, 4, 4, 0]}>
                  {detectionData.riskZones.map((zone: any) => {
                    const colour =
                      zone.riskLevel === 'critical' ? '#DC2626' :
                      zone.riskLevel === 'high'     ? '#EA580C' :
                      zone.riskLevel === 'medium'   ? '#D97706' : '#059669';
                    return <Cell key={zone.id} fill={colour} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          {/* Legend */}
          <div className="flex gap-4 mt-3 text-xs text-theme-text-secondary">
            {([['bg-red-600','Critical'],['bg-orange-600','High'],['bg-amber-600','Medium'],['bg-emerald-600','Low']] as const).map(([cls, label]) => (
              <span key={label} className="flex items-center gap-1">
                <span className={`inline-block w-3 h-3 rounded-sm ${cls}`} />{label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Monitored Areas */}
      <div className="bg-theme-card rounded-lg shadow-sm">
        <div className="px-6 py-4 border-b border-theme-border">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-theme-text-primary">Your Monitored Areas</h3>
            <Link 
              to="/flagged-areas"
              className="text-sm text-emerald-600 hover:text-emerald-700 font-medium flex items-center"
            >
              View All <ArrowRight className="h-3 w-3 ml-1" />
            </Link>
          </div>
        </div>
        <div className="divide-y divide-theme-border">
          {loadingAreas ? (
            <div className="px-6 py-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto"></div>
              <p className="text-theme-text-secondary mt-2 text-sm">Loading monitored areas...</p>
            </div>
          ) : monitoredAreas.length === 0 ? (
            <div className="px-6 py-8 text-center">
              <MapPin className="h-12 w-12 text-gray-400 mx-auto mb-2" />
              <p className="text-theme-text-secondary mb-2">No monitored areas yet</p>
              <Link
                to="/map"
                className="text-sm text-emerald-600 hover:text-emerald-700 font-medium"
              >
                Add your first area →
              </Link>
            </div>
          ) : (
            monitoredAreas.slice(0, 5).map((area) => {
              const latestDetection = area.detection_history?.[0];
              const hasDeforestation = latestDetection?.deforestation_detected;
              
              return (
                <Link
                  key={area.id}
                  to="/map"
                  state={{ selectedAreaId: area.id }}
                  className="block px-6 py-4 hover:bg-theme-hover transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className={`w-3 h-3 rounded-full ${
                        hasDeforestation ? 'bg-red-500' :
                        area.active_monitoring ? 'bg-green-500' :
                        'bg-gray-400'
                      }`}></div>
                      <div>
                        <p className="text-sm font-medium text-theme-text-primary">
                          {area.name}
                        </p>
                        <p className="text-xs text-theme-text-secondary">
                          {area.active_monitoring ? 'Active Monitoring' : 'Manual'} • {area.detection_count} detection{area.detection_count !== 1 ? 's' : ''}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      {hasDeforestation ? (
                        <>
                          <p className="text-sm font-medium text-red-600">
                            ⚠️ {latestDetection.forest_loss_percent.toFixed(1)}% Loss
                          </p>
                          <p className="text-xs text-theme-text-secondary">
                            {new Date(latestDetection.timestamp).toLocaleDateString()}
                          </p>
                        </>
                      ) : area.last_monitored ? (
                        <>
                          <p className="text-sm text-green-600">✓ No Change</p>
                          <p className="text-xs text-theme-text-secondary">
                            {new Date(area.last_monitored).toLocaleDateString()}
                          </p>
                        </>
                      ) : (
                        <p className="text-sm text-theme-text-secondary">Not checked yet</p>
                      )}
                    </div>
                  </div>
                </Link>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

export default HomePage;