import React, { useState, useEffect } from 'react';
import {
  Download, FileText, Clock, BarChart3, TrendingUp,
  Activity, MapPin, Shield, AlertTriangle, CheckCircle,
  Search, RefreshCw
} from 'lucide-react';
import { apiFetch } from '../utils/api';

interface DetectionEvent {
  areaId: string;
  areaName: string;
  date: string;
  deforestation_detected: boolean;
  confidence: number;
  ndvi_before?: number;
  ndvi_after?: number;
  ndvi_change?: number;
  prediction?: string;
}

interface MonitoredArea {
  id: string;
  name: string;
  description?: string;
  active_monitoring?: boolean;
  monitoring_enabled?: boolean;
  created_at?: string;
  last_monitored?: string;
  monitoring_interval_days?: number;
  detection_history?: any[];
  coordinates?: any[];
}

const ReportsPage: React.FC = () => {
  const [areas, setAreas] = useState<MonitoredArea[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'areas'>('overview');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [filterResult, setFilterResult] = useState<'all' | 'detected' | 'clear'>('all');
  const [searchArea, setSearchArea] = useState('');

  const fetchAreas = async () => {
    try {
      setLoading(true);
      const res = await apiFetch('/api/monitored-areas');
      const data = await res.json();
      setAreas(data.areas || []);
    } catch (e) {
      console.error('Failed to fetch areas:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAreas(); }, []);

  const allEvents: DetectionEvent[] = areas
    .flatMap(area =>
      (area.detection_history || []).map((h: any) => ({
        areaId: area.id,
        areaName: area.name,
        date: h.timestamp || h.date || '',
        deforestation_detected: h.deforestation_detected ?? false,
        confidence: h.confidence ?? 0,
        ndvi_before: h.ndvi_before,
        ndvi_after: h.ndvi_after,
        ndvi_change: h.ndvi_change,
        prediction: h.prediction,
      }))
    )
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  const filteredEvents = allEvents.filter(e => {
    if (filterResult === 'detected' && !e.deforestation_detected) return false;
    if (filterResult === 'clear' && e.deforestation_detected) return false;
    if (dateFrom && e.date < dateFrom) return false;
    if (dateTo && e.date > dateTo + 'T23:59:59') return false;
    if (searchArea && !e.areaName.toLowerCase().includes(searchArea.toLowerCase())) return false;
    return true;
  });

  const totalScans = allEvents.length;
  const deforestationEvents = allEvents.filter(e => e.deforestation_detected).length;
  const activeAreas = areas.filter(a => a.active_monitoring).length;
  const flaggedAreas = areas.filter(a =>
    (a.detection_history || []).some((h: any) => h.deforestation_detected)
  ).length;
  const lastScan = allEvents.length > 0 ? allEvents[0].date : null;

  const formatDate = (iso: string) => {
    if (!iso) return '\u2014';
    const d = new Date(iso);
    return isNaN(d.getTime()) ? iso : d.toLocaleString();
  };

  const formatDateShort = (iso: string) => {
    if (!iso) return '\u2014';
    const d = new Date(iso);
    return isNaN(d.getTime()) ? iso : d.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 text-emerald-500 animate-spin mx-auto mb-3" />
          <p className="text-gray-600">Loading report data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
          <p className="text-gray-500 text-sm mt-1">
            Live data from {areas.length} monitored area(s) &middot; {totalScans} total scan record(s)
          </p>
        </div>
        <div className="flex space-x-2">
          <button onClick={fetchAreas} className="flex items-center space-x-1 px-3 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 transition-colors">
            <RefreshCw className="h-4 w-4" />
            <span>Refresh</span>
          </button>
          <button onClick={() => window.print()} className="flex items-center space-x-1 px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700 transition-colors">
            <Download className="h-4 w-4" />
            <span>Print / Export</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: 'Monitored Areas', value: areas.length, icon: MapPin, color: 'blue', sub: `${activeAreas} active` },
          { label: 'Active Monitoring', value: activeAreas, icon: Activity, color: 'green', sub: `${areas.length - activeAreas} paused` },
          { label: 'Total Scans', value: totalScans, icon: BarChart3, color: 'purple', sub: lastScan ? `Last: ${formatDateShort(lastScan)}` : 'No scans yet' },
          { label: 'Deforestation Events', value: deforestationEvents, icon: AlertTriangle, color: deforestationEvents > 0 ? 'red' : 'green', sub: `${totalScans - deforestationEvents} clear` },
          { label: 'Areas Flagged', value: flaggedAreas, icon: Shield, color: flaggedAreas > 0 ? 'red' : 'green', sub: flaggedAreas > 0 ? 'Need attention' : 'All clear' },
        ].map(stat => {
          const Icon = stat.icon;
          const colorMap: Record<string, string> = {
            blue: 'bg-blue-50 text-blue-700 border-blue-200',
            green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
            purple: 'bg-purple-50 text-purple-700 border-purple-200',
            red: 'bg-red-50 text-red-700 border-red-200',
          };
          return (
            <div key={stat.label} className={`border rounded-lg p-4 ${colorMap[stat.color]}`}>
              <div className="flex items-center justify-between mb-2">
                <Icon className="h-5 w-5 opacity-70" />
                <span className="text-2xl font-bold">{stat.value}</span>
              </div>
              <div className="text-sm font-medium">{stat.label}</div>
              <div className="text-xs opacity-70 mt-0.5">{stat.sub}</div>
            </div>
          );
        })}
      </div>

      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {[
            { id: 'overview', label: 'Overview', icon: BarChart3 },
            { id: 'history', label: `Detection History (${allEvents.length})`, icon: Clock },
            { id: 'areas', label: `Monitored Areas (${areas.length})`, icon: MapPin },
          ].map(tab => {
            const Icon = tab.icon;
            return (
              <button key={tab.id} onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 pb-3 border-b-2 text-sm font-medium transition-colors ${activeTab === tab.id ? 'border-emerald-500 text-emerald-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center space-x-2">
              <Activity className="h-4 w-4 text-emerald-600" />
              <span>Area Monitoring Status</span>
            </h2>
            {areas.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-6">No monitored areas defined yet</p>
            ) : (
              <div className="divide-y divide-gray-100">
                {areas.map(area => {
                  const scans = (area.detection_history || []).length;
                  const detected = (area.detection_history || []).filter((h: any) => h.deforestation_detected).length;
                  return (
                    <div key={area.id} className="py-3 flex items-center justify-between">
                      <div className="flex-1 min-w-0 pr-3">
                        <div className="flex items-center space-x-2">
                          <span className={`h-2 w-2 rounded-full flex-shrink-0 ${area.active_monitoring ? 'bg-emerald-500' : 'bg-gray-300'}`} />
                          <span className="text-sm font-medium text-gray-900 truncate">{area.name}</span>
                        </div>
                        <p className="text-xs text-gray-400 mt-0.5 pl-4">
                          {area.last_monitored ? `Last scan: ${formatDateShort(area.last_monitored)}` : 'Not yet scanned'}
                          {scans > 0 && ` · ${scans} scan(s)`}
                        </p>
                      </div>
                      <div className="flex-shrink-0">
                        {detected > 0 ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                            {detected} alert{detected > 1 ? 's' : ''}
                          </span>
                        ) : scans > 0 ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">Clear</span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">No scans</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center space-x-2">
              <Clock className="h-4 w-4 text-emerald-600" />
              <span>Recent Scan Events</span>
            </h2>
            {allEvents.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-6">No scan events recorded yet</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {allEvents.slice(0, 15).map((e, i) => (
                  <div key={i} className={`flex items-start space-x-3 p-2 rounded-lg ${e.deforestation_detected ? 'bg-red-50' : 'bg-gray-50'}`}>
                    {e.deforestation_detected
                      ? <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                      : <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-gray-800 truncate">{e.areaName}</span>
                        <span className="text-xs text-gray-400 flex-shrink-0 ml-2">{formatDateShort(e.date)}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {e.deforestation_detected
                          ? `Deforestation detected${e.confidence ? ` (${(e.confidence * 100).toFixed(0)}% confidence)` : ''}`
                          : `No deforestation${e.confidence ? ` (${(e.confidence * 100).toFixed(0)}% confidence)` : ''}`}
                        {typeof e.ndvi_change === 'number' && ` · NDVI ${e.ndvi_change > 0 ? '+' : ''}${e.ndvi_change.toFixed(3)}`}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {areas.some(a => (a.detection_history || []).length > 0) && (
            <div className="lg:col-span-2 bg-white rounded-lg shadow-sm border p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center space-x-2">
                <TrendingUp className="h-4 w-4 text-emerald-600" />
                <span>NDVI Summary by Area</span>
              </h2>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase text-gray-500 border-b">
                      <th className="py-2 pr-6">Area</th>
                      <th className="py-2 pr-6">Scans</th>
                      <th className="py-2 pr-6">Latest NDVI Before</th>
                      <th className="py-2 pr-6">Latest NDVI After</th>
                      <th className="py-2 pr-6">NDVI Change</th>
                      <th className="py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {areas.filter(a => (a.detection_history || []).length > 0).map(area => {
                      const history = area.detection_history || [];
                      const latest = history[history.length - 1];
                      const detected = history.filter((h: any) => h.deforestation_detected).length;
                      return (
                        <tr key={area.id}>
                          <td className="py-2.5 pr-6 font-medium text-gray-900">{area.name}</td>
                          <td className="py-2.5 pr-6 text-gray-600">{history.length}</td>
                          <td className="py-2.5 pr-6 text-gray-600">{typeof latest?.ndvi_before === 'number' ? latest.ndvi_before.toFixed(3) : '\u2014'}</td>
                          <td className="py-2.5 pr-6 text-gray-600">{typeof latest?.ndvi_after === 'number' ? latest.ndvi_after.toFixed(3) : '\u2014'}</td>
                          <td className={`py-2.5 pr-6 font-medium ${typeof latest?.ndvi_change === 'number' && latest.ndvi_change < -0.05 ? 'text-red-600' : 'text-emerald-600'}`}>
                            {typeof latest?.ndvi_change === 'number' ? (latest.ndvi_change > 0 ? '+' : '') + latest.ndvi_change.toFixed(3) : '\u2014'}
                          </td>
                          <td className="py-2.5">
                            {detected > 0
                              ? <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700">{detected} alert(s)</span>
                              : <span className="px-2 py-0.5 rounded-full text-xs bg-emerald-100 text-emerald-700">Clear</span>}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'history' && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow-sm border p-4">
            <div className="flex flex-wrap gap-3 items-end">
              <div>
                <label className="block text-xs text-gray-500 mb-1">From Date</label>
                <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} title="From date filter"
                  className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">To Date</label>
                <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} title="To date filter"
                  className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Result</label>
                <select value={filterResult} onChange={e => setFilterResult(e.target.value as any)} title="Filter by result"
                  className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500">
                  <option value="all">All results</option>
                  <option value="detected">Deforestation detected</option>
                  <option value="clear">Clear / no detection</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Area Name</label>
                <div className="relative">
                  <Search className="h-3.5 w-3.5 text-gray-400 absolute left-2 top-2" />
                  <input type="text" placeholder="Filter by area..." value={searchArea} onChange={e => setSearchArea(e.target.value)}
                    className="pl-7 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500" />
                </div>
              </div>
              {(dateFrom || dateTo || filterResult !== 'all' || searchArea) && (
                <button onClick={() => { setDateFrom(''); setDateTo(''); setFilterResult('all'); setSearchArea(''); }}
                  className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
                  Clear filters
                </button>
              )}
              <div className="ml-auto text-sm text-gray-500 self-end pb-0.5">{filteredEvents.length} event(s) shown</div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
            {filteredEvents.length === 0 ? (
              <div className="text-center py-12">
                <FileText className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">No detection events match the current filters</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr className="text-left text-xs uppercase text-gray-500 border-b">
                      <th className="px-4 py-3">Date / Time</th>
                      <th className="px-4 py-3">Area</th>
                      <th className="px-4 py-3">Result</th>
                      <th className="px-4 py-3">Confidence</th>
                      <th className="px-4 py-3">NDVI Before</th>
                      <th className="px-4 py-3">NDVI After</th>
                      <th className="px-4 py-3">NDVI Change</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredEvents.map((e, i) => (
                      <tr key={i} className={e.deforestation_detected ? 'bg-red-50' : ''}>
                        <td className="px-4 py-2.5 text-gray-600 whitespace-nowrap text-xs">{formatDate(e.date)}</td>
                        <td className="px-4 py-2.5 font-medium text-gray-900">{e.areaName}</td>
                        <td className="px-4 py-2.5">
                          {e.deforestation_detected
                            ? <span className="inline-flex items-center space-x-1 text-red-700 text-xs font-medium"><AlertTriangle className="h-3.5 w-3.5" /><span>Detected</span></span>
                            : <span className="inline-flex items-center space-x-1 text-emerald-700 text-xs font-medium"><CheckCircle className="h-3.5 w-3.5" /><span>Clear</span></span>}
                        </td>
                        <td className="px-4 py-2.5 text-gray-600">{e.confidence ? `${(e.confidence * 100).toFixed(1)}%` : '\u2014'}</td>
                        <td className="px-4 py-2.5 text-gray-600">{typeof e.ndvi_before === 'number' ? e.ndvi_before.toFixed(3) : '\u2014'}</td>
                        <td className="px-4 py-2.5 text-gray-600">{typeof e.ndvi_after === 'number' ? e.ndvi_after.toFixed(3) : '\u2014'}</td>
                        <td className={`px-4 py-2.5 font-medium ${typeof e.ndvi_change === 'number' && e.ndvi_change < -0.05 ? 'text-red-600' : 'text-gray-600'}`}>
                          {typeof e.ndvi_change === 'number' ? (e.ndvi_change > 0 ? '+' : '') + e.ndvi_change.toFixed(3) : '\u2014'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'areas' && (
        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
          {areas.length === 0 ? (
            <div className="text-center py-12">
              <MapPin className="h-10 w-10 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No monitored areas defined yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr className="text-left text-xs uppercase text-gray-500 border-b">
                    <th className="px-4 py-3">Area Name</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3">Last Scan</th>
                    <th className="px-4 py-3">Interval</th>
                    <th className="px-4 py-3">Total Scans</th>
                    <th className="px-4 py-3">Deforestation Events</th>
                    <th className="px-4 py-3">Avg Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {areas.map(area => {
                    const history = area.detection_history || [];
                    const detected = history.filter((h: any) => h.deforestation_detected).length;
                    const avgConf = history.length > 0
                      ? history.reduce((s: number, h: any) => s + (h.confidence || 0), 0) / history.length
                      : null;
                    return (
                      <tr key={area.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-900">{area.name}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-medium ${area.active_monitoring ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${area.active_monitoring ? 'bg-emerald-500' : 'bg-gray-400'}`} />
                            <span>{area.active_monitoring ? 'Active' : 'Paused'}</span>
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-500 text-xs">{area.created_at ? formatDateShort(area.created_at) : '\u2014'}</td>
                        <td className="px-4 py-3 text-gray-500 text-xs">{area.last_monitored ? formatDateShort(area.last_monitored) : '\u2014'}</td>
                        <td className="px-4 py-3 text-gray-500">{area.monitoring_interval_days ? `${area.monitoring_interval_days}d` : '\u2014'}</td>
                        <td className="px-4 py-3 text-gray-700">{history.length}</td>
                        <td className="px-4 py-3">{detected > 0 ? <span className="text-red-600 font-medium">{detected}</span> : <span className="text-emerald-600">0</span>}</td>
                        <td className="px-4 py-3 text-gray-600">{avgConf !== null ? `${(avgConf * 100).toFixed(1)}%` : '\u2014'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ReportsPage;
