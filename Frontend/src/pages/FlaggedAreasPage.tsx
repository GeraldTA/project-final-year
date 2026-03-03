import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, MapPin, CheckCircle, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import { apiFetch, apiUrl } from '../utils/api';

interface MonitoredArea {
  id: string;
  name: string;
  description: string;
  coordinates: [number, number][];
  created_at: string;
  last_monitored: string | null;
  monitoring_enabled: boolean;
  active_monitoring: boolean;
  monitoring_started_date: string | null;
  next_scheduled_detection: string | null;
  monitoring_interval_days: number | null;
  detection_count: number;
  detection_history: DetectionRecord[];
  monitoring_summary?: {
    monitoring_started_date: string | null;
    next_scheduled_detection: string | null;
    monitoring_interval_days: number;
    last_monitored: string | null;
    scan_count: number;
    ever_deforested: boolean;
    latest_forest_loss_percent: number | null;
    active_monitoring: boolean;
  };
}

interface DetectionRecord {
  timestamp: string;
  before_date: string;
  after_date: string;
  deforestation_detected: boolean;
  forest_loss_percent: number;
  vegetation_trend: string;
}

const FlaggedAreasPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [monitoredAreas, setMonitoredAreas] = useState<MonitoredArea[]>([]);
  const [groupTotals, setGroupTotals] = useState({ total: 0, clean: 0, deforested: 0, not_monitoring: 0 });
  const [loadingAreas, setLoadingAreas] = useState(true);
  const [togglingMonitoring, setTogglingMonitoring] = useState<string | null>(null);
  const [runningDetection, setRunningDetection] = useState<string | null>(null);
  const [showDetectionPicker, setShowDetectionPicker] = useState<string | null>(null);
  const [detectionDates, setDetectionDates] = useState<Record<string, { before: string; after: string }>>({});
  const [detectionResults, setDetectionResults] = useState<Record<string, any>>({});
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});
  const [showImages, setShowImages] = useState<Record<string, boolean>>({});
  const [imageViz, setImageViz] = useState<Record<string, 'rgb' | 'nir' | 'ndvi'>>({});

  const toggleCard = (id: string) =>
    setExpandedCards(prev => ({ ...prev, [id]: !prev[id] }));

  const getDefaultDates = () => {
    const today = new Date();
    const before = new Date(today);
    before.setDate(before.getDate() - 30);
    return {
      before: before.toISOString().split('T')[0],
      after:  today.toISOString().split('T')[0],
    };
  };

  const getDates = (areaId: string) =>
    detectionDates[areaId] ?? getDefaultDates();

  const runDetection = async (area: MonitoredArea) => {
    const dates = getDates(area.id);
    setRunningDetection(area.id);
    setShowDetectionPicker(null);
    try {
      const res = await apiFetch(`/api/monitored-areas/${area.id}/detect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ before_date: dates.before, after_date: dates.after }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setDetectionResults(prev => ({ ...prev, [area.id]: data.detection_result }));
      if (data.area) {
        setMonitoredAreas(prev =>
          prev.map(a => a.id === area.id ? { ...a, ...data.area } : a)
        );
      }
    } catch (e: any) {
      setDetectionResults(prev => ({ ...prev, [area.id]: { error: e?.message ?? 'Detection failed' } }));
    } finally {
      setRunningDetection(null);
    }
  };

  const toggleMonitoring = async (area: MonitoredArea) => {
    setTogglingMonitoring(area.id);
    const action = area.active_monitoring ? 'stop' : 'start';
    try {
      const res = await apiFetch(`/api/monitored-areas/${area.id}/active-monitoring/${action}`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setMonitoredAreas(prev =>
        prev.map(a => a.id === area.id ? { ...a, ...data.area } : a)
      );
    } catch (e) {
      console.error(`Failed to ${action} monitoring:`, e);
      alert(`Could not ${action} monitoring. Make sure the backend is running.`);
    } finally {
      setTogglingMonitoring(null);
    }
  };

  // Fetch monitored areas grouped by deforestation status
  useEffect(() => {
    const fetchMonitoredAreas = async () => {
      try {
        const res = await apiFetch('/api/monitored-areas/grouped');
        if (res.ok) {
          const data = await res.json();
          // Flatten all groups into a single list for card operations
          const all: MonitoredArea[] = [
            ...(data.deforested || []),
            ...(data.clean || []),
            ...(data.not_monitoring || []),
          ];
          setMonitoredAreas(all);
          setGroupTotals(data.totals || { total: 0, clean: 0, deforested: 0, not_monitoring: 0 });
        }
      } catch (e) {
        console.error('Failed to fetch monitored areas:', e);
      } finally {
        setLoadingAreas(false);
      }
    };

    fetchMonitoredAreas();
  }, []);

  // ── Helpers ──────────────────────────────────────────────────────────────
  const fmtDate = (d: string | null | undefined) => {
    if (!d) return null;
    try { return new Date(d).toLocaleDateString(); } catch { return String(d); }
  };
  const daysUntil = (d: string | null | undefined): number | null => {
    if (!d) return null;
    try { return Math.ceil((new Date(d).getTime() - Date.now()) / 86_400_000); } catch { return null; }
  };

  // ── Derive groups from flat list ──────────────────────────────────────────
  const filteredAreas = monitoredAreas.filter(area =>
    area.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    area.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );
  const deforestationAreas = filteredAreas.filter(a =>
    a.detection_history?.some(r => r.deforestation_detected)
  );
  const cleanAreas = filteredAreas.filter(a =>
    a.monitoring_started_date &&
    !a.detection_history?.some(r => r.deforestation_detected)
  );
  const notMonitoringAreas = filteredAreas.filter(a => !a.monitoring_started_date);

  // ── Shared card renderer ──────────────────────────────────────────────────
  const renderAreaCard = (area: MonitoredArea) => {
    const latestDetection = area.detection_history?.[0];
    const hasDeforestation = latestDetection?.deforestation_detected;
    const forestLoss = latestDetection?.forest_loss_percent || 0;
    const startedDate = area.monitoring_started_date ?? area.monitoring_summary?.monitoring_started_date ?? null;
    const nextScan = area.next_scheduled_detection ?? area.monitoring_summary?.next_scheduled_detection ?? null;
    const interval = area.monitoring_interval_days ?? area.monitoring_summary?.monitoring_interval_days ?? 5;
    const days = daysUntil(nextScan);

    return (
      <div
        key={area.id}
        className={`border rounded-lg overflow-hidden hover:shadow-lg transition-shadow ${
          hasDeforestation
            ? 'border-red-300 bg-red-50'
            : startedDate
            ? 'border-green-200'
            : 'border-gray-200'
        }`}
      >
        {/* ── Card Header (always visible) ─────────────────────────── */}
        <button
          onClick={() => toggleCard(area.id)}
          className={`w-full flex items-center justify-between px-4 py-3 text-left ${
            hasDeforestation ? 'bg-red-50 hover:bg-red-100' : 'bg-white hover:bg-gray-50'
          } transition-colors`}
        >
          <div className="flex items-center gap-2 min-w-0">
            {hasDeforestation
              ? <AlertTriangle className="h-4 w-4 text-red-600 flex-shrink-0" />
              : startedDate
              ? <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
              : <MapPin className="h-4 w-4 text-gray-400 flex-shrink-0" />}
            <div className="min-w-0">
              <h3 className="font-semibold text-gray-900 truncate">{area.name}</h3>
              {area.description && (
                <p className="text-xs text-gray-500 truncate">{area.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0 ml-2">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
              area.active_monitoring ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
            }`}>
              {area.active_monitoring ? 'Active' : 'Manual'}
            </span>
            {expandedCards[area.id]
              ? <ChevronUp className="h-4 w-4 text-gray-400" />
              : <ChevronDown className="h-4 w-4 text-gray-400" />}
          </div>
        </button>

        {/* ── Collapsed schedule pill ──────────────────────────────── */}
        {!expandedCards[area.id] && startedDate && (
          <div className="px-4 py-1.5 border-t border-gray-100 bg-gray-50 text-xs text-gray-500 flex flex-wrap gap-x-4 gap-y-0.5">
            <span>📅 Started {fmtDate(startedDate)}</span>
            {nextScan && (
              <span className={days !== null && days <= 0 ? 'text-orange-600 font-medium' : ''}>
                🔄 Next scan {fmtDate(nextScan)}
                {days !== null && days > 0 ? ` (${days}d)` : days !== null && days <= 0 ? ' — overdue' : ''}
              </span>
            )}
          </div>
        )}

        {/* ── Collapsible body ─────────────────────────────────────── */}
        {expandedCards[area.id] && (
          <div className="px-4 pb-4 pt-2">

            {/* Monitoring Schedule Banner */}
            {startedDate && (
              <div className="mb-3 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-xs text-blue-800">
                <div className="font-semibold text-blue-900 mb-1">📡 Monitoring Schedule</div>
                <div className="flex flex-wrap gap-x-5 gap-y-1">
                  <span>Started: <strong>{fmtDate(startedDate)}</strong></span>
                  <span>Interval: <strong>every {interval} days</strong></span>
                  {nextScan && (
                    <span className={days !== null && days <= 0 ? 'text-orange-700 font-bold' : ''}>
                      Next auto-scan: <strong>{fmtDate(nextScan)}</strong>
                      {days !== null && days > 0 ? ` (in ${days} day${days !== 1 ? 's' : ''})` : ''}
                      {days !== null && days <= 0 ? ' ⚠️ overdue' : ''}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Status Row */}
            <div className="space-y-2 mb-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Status:</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  area.active_monitoring ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {area.active_monitoring ? 'Active Monitoring' : 'Manual'}
                </span>
              </div>
              {area.last_monitored && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Last Scan:</span>
                  <span className="text-gray-900">{fmtDate(area.last_monitored)}</span>
                </div>
              )}
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Total Scans:</span>
                <span className="font-medium text-gray-900">{area.detection_count}</span>
              </div>
            </div>

            {/* Latest Detection Result */}
            {latestDetection && (
              <div className={`p-3 rounded-lg mb-3 ${hasDeforestation ? 'bg-red-100' : 'bg-green-100'}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-gray-700">Latest Result:</span>
                  <span className={`text-xs font-bold ${hasDeforestation ? 'text-red-700' : 'text-green-700'}`}>
                    {hasDeforestation ? '⚠️ Deforestation Detected' : '✓ No Change'}
                  </span>
                </div>
                {hasDeforestation && (
                  <div className="text-sm font-medium text-red-800 mt-1">
                    Forest Loss: {forestLoss.toFixed(2)}%
                  </div>
                )}
                <div className="text-xs text-gray-600 mt-1">
                  {fmtDate(latestDetection.before_date)} → {fmtDate(latestDetection.after_date)}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <Link
                to="/map"
                state={{ selectedAreaId: area.id }}
                className="flex-1 text-center px-3 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 transition-colors"
              >
                View on Map
              </Link>
              <button
                onClick={() => toggleMonitoring(area)}
                disabled={togglingMonitoring === area.id}
                className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50 ${
                  area.active_monitoring
                    ? 'bg-red-100 text-red-700 hover:bg-red-200'
                    : 'bg-emerald-600 text-white hover:bg-emerald-700'
                }`}
              >
                {togglingMonitoring === area.id
                  ? '…'
                  : area.active_monitoring ? 'Stop Monitoring' : 'Start Monitoring'}
              </button>
            </div>

            {/* ML Detection */}
            <div className="mt-2">
              {showDetectionPicker === area.id ? (
                <div className="border border-gray-200 rounded-lg p-3 bg-gray-50 space-y-2">
                  <p className="text-xs font-medium text-gray-700">Select date range for ML scan:</p>
                  <div className="flex gap-2 items-center">
                    <div className="flex-1">
                      <label className="text-xs text-gray-500">Before</label>
                      <input
                        type="date"
                        title="Before date"
                        value={getDates(area.id).before}
                        onChange={e => setDetectionDates(prev => ({ ...prev, [area.id]: { ...getDates(area.id), before: e.target.value } }))}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-xs"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-xs text-gray-500">After</label>
                      <input
                        type="date"
                        title="After date"
                        value={getDates(area.id).after}
                        onChange={e => setDetectionDates(prev => ({ ...prev, [area.id]: { ...getDates(area.id), after: e.target.value } }))}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-xs"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => runDetection(area)}
                      className="flex-1 px-3 py-1.5 bg-purple-600 text-white rounded text-xs font-medium hover:bg-purple-700"
                    >
                      Run Detection
                    </button>
                    <button
                      onClick={() => setShowDetectionPicker(null)}
                      className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setShowDetectionPicker(area.id)}
                  disabled={runningDetection === area.id}
                  className="w-full px-3 py-2 bg-purple-600 text-white rounded text-sm font-medium hover:bg-purple-700 transition-colors disabled:opacity-50"
                >
                  {runningDetection === area.id ? '🔄 Running ML Detection…' : '🛰️ Run ML Detection'}
                </button>
              )}

              {/* Inline detection result */}
              {detectionResults[area.id] && runningDetection !== area.id && (() => {
                const r = detectionResults[area.id];
                if (r.error) return (
                  <div className="mt-2 p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700">
                    ❌ {r.error}
                  </div>
                );
                const ch = r.change ?? {};
                const bf = r.before ?? {};
                const af = r.after ?? {};
                const detected = r.deforestation_detected;
                return (
                  <div className={`mt-2 rounded-lg border overflow-hidden text-xs ${detected ? 'border-red-300' : 'border-green-300'}`}>
                    <div className={`px-3 py-2 font-bold flex items-center justify-between ${detected ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`}>
                      <span>{detected ? '⚠️ Deforestation Detected' : '✅ No Deforestation'}</span>
                      <span className="font-normal opacity-80 text-xs">{bf.date} → {af.date}</span>
                    </div>
                    {r.seasonal_warning && (
                      <div className="px-3 py-2 bg-amber-50 border-b border-amber-200 text-amber-800 text-xs">
                        ⚠️ {r.seasonal_warning}
                      </div>
                    )}
                    <div className="p-3 bg-white space-y-3">
                      <div>
                        <p className="font-semibold text-gray-700 mb-1">🌳 Forest Cover</p>
                        <div className="grid grid-cols-3 gap-2 text-center">
                          <div className="bg-gray-50 rounded p-2">
                            <div className="text-gray-500">Before</div>
                            <div className="font-bold text-gray-800">{bf.forest_cover_percent?.toFixed(1) ?? '—'}%</div>
                            <div className="text-gray-400">p={bf.forest_probability?.toFixed(3) ?? '—'}</div>
                          </div>
                          <div className="bg-gray-50 rounded p-2">
                            <div className="text-gray-500">After</div>
                            <div className="font-bold text-gray-800">{af.forest_cover_percent?.toFixed(1) ?? '—'}%</div>
                            <div className="text-gray-400">p={af.forest_probability?.toFixed(3) ?? '—'}</div>
                          </div>
                          <div className={`rounded p-2 ${detected ? 'bg-red-50' : 'bg-green-50'}`}>
                            <div className="text-gray-500">Change</div>
                            <div className={`font-bold ${detected ? 'text-red-700' : 'text-green-700'}`}>
                              {ch.forest_drop_percent != null
                                ? `${ch.forest_drop_percent > 0 ? '−' : '+'}${Math.abs(ch.forest_drop_percent).toFixed(1)}%`
                                : '—'}
                            </div>
                            <div className="text-gray-400">
                              {ch.forest_loss_percent != null ? `${ch.forest_loss_percent.toFixed(1)}% relative` : ''}
                            </div>
                          </div>
                        </div>
                      </div>
                      {(bf.ndvi_mean != null || af.ndvi_mean != null) && (
                        <div>
                          <p className="font-semibold text-gray-700 mb-1">📊 NDVI</p>
                          <div className="grid grid-cols-3 gap-2 text-center">
                            <div className="bg-gray-50 rounded p-2">
                              <div className="text-gray-500">Before</div>
                              <div className="font-bold text-gray-800">{bf.ndvi_mean?.toFixed(4) ?? '—'}</div>
                            </div>
                            <div className="bg-gray-50 rounded p-2">
                              <div className="text-gray-500">After</div>
                              <div className="font-bold text-gray-800">{af.ndvi_mean?.toFixed(4) ?? '—'}</div>
                            </div>
                            <div className={`rounded p-2 ${(ch.ndvi_drop ?? 0) > 0.05 ? 'bg-red-50' : 'bg-green-50'}`}>
                              <div className="text-gray-500">Drop</div>
                              <div className={`font-bold ${(ch.ndvi_drop ?? 0) > 0.05 ? 'text-red-700' : 'text-green-700'}`}>
                                {ch.ndvi_drop != null ? ch.ndvi_drop.toFixed(4) : '—'}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                      <div className="grid grid-cols-2 gap-2">
                        {ch.greenness_increase != null && (
                          <div className="bg-gray-50 rounded p-2">
                            <div className="text-gray-500">Greenness Change</div>
                            <div className={`font-bold ${ch.greenness_increase >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                              {ch.greenness_increase >= 0 ? '+' : ''}{ch.greenness_increase.toFixed(4)}
                            </div>
                          </div>
                        )}
                        <div className="bg-gray-50 rounded p-2">
                          <div className="text-gray-500">Vegetation Trend</div>
                          <div className={`font-bold capitalize ${
                            ch.vegetation_trend === 'growth' ? 'text-green-700' :
                            ch.vegetation_trend === 'decline' ? 'text-red-700' : 'text-gray-700'
                          }`}>
                            {ch.vegetation_trend === 'growth' ? '📈' : ch.vegetation_trend === 'decline' ? '📉' : '➡️'} {ch.vegetation_trend ?? '—'}
                          </div>
                        </div>
                      </div>
                      {ch.interpretation && (
                        <div className="bg-blue-50 border border-blue-200 rounded p-2 text-blue-800">
                          💡 {ch.interpretation}
                        </div>
                      )}
                      {/* Satellite Images */}
                      {r.exports?.before?.path && r.exports?.after?.path && (
                        <div className="border-t border-gray-200 pt-2 mt-1">
                          <button
                            onClick={() => setShowImages(prev => ({ ...prev, [area.id]: !prev[area.id] }))}
                            className="text-xs text-blue-600 hover:text-blue-800 underline"
                          >
                            {showImages[area.id] ? '▼ Hide' : '▶ View'} Before/After Satellite Images
                          </button>
                          {showImages[area.id] && (
                            <div className="mt-2 space-y-2">
                              <div className="flex items-center gap-2">
                                <label className="text-xs text-gray-600">View:</label>
                                <select
                                  title="Image visualization mode"
                                  value={imageViz[area.id] ?? 'rgb'}
                                  onChange={e => setImageViz(prev => ({ ...prev, [area.id]: e.target.value as 'rgb' | 'nir' | 'ndvi' }))}
                                  className="text-xs border border-gray-300 rounded px-1 py-0.5"
                                >
                                  <option value="rgb">True Color (RGB)</option>
                                  <option value="nir">False Color (NIR)</option>
                                  <option value="ndvi">NDVI (Vegetation)</option>
                                </select>
                              </div>
                              <div className="grid grid-cols-2 gap-2">
                                <div>
                                  <p className="text-xs font-medium text-gray-600 mb-1">Before ({bf.date ?? ''})</p>
                                  <img
                                    src={apiUrl(`/api/ml/preview-geotiff/${r.exports.before.path.split(/[/\\]/).pop()}?band_combo=${imageViz[area.id] ?? 'rgb'}`)}
                                    alt="Before"
                                    className="w-full h-auto rounded border border-gray-300"
                                    onError={e => { (e.currentTarget as HTMLImageElement).src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="120"%3E%3Crect fill="%23ddd" width="200" height="120"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" fill="%23666" font-size="12"%3EImage unavailable%3C/text%3E%3C/svg%3E'; }}
                                  />
                                </div>
                                <div>
                                  <p className="text-xs font-medium text-gray-600 mb-1">After ({af.date ?? ''})</p>
                                  <img
                                    src={apiUrl(`/api/ml/preview-geotiff/${r.exports.after.path.split(/[/\\]/).pop()}?band_combo=${imageViz[area.id] ?? 'rgb'}`)}
                                    alt="After"
                                    className="w-full h-auto rounded border border-gray-300"
                                    onError={e => { (e.currentTarget as HTMLImageElement).src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="120"%3E%3Crect fill="%23ddd" width="200" height="120"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" fill="%23666" font-size="12"%3EImage unavailable%3C/text%3E%3C/svg%3E'; }}
                                  />
                                </div>
                              </div>
                              <p className="text-xs text-gray-400 italic">RGB = true color · NIR = vegetation red · NDVI = health green</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* Coordinates Info */}
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="text-xs text-gray-500">
                {area.coordinates?.length || 0} coordinates · Created {fmtDate(area.created_at)}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  // ── Group section renderer ────────────────────────────────────────────────
  const renderGroup = (
    title: string,
    icon: React.ReactNode,
    areas: MonitoredArea[],
    headerClassName: string,
    emptyMsg: string
  ) => (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden">
      <div className={`px-6 py-4 flex items-center gap-3 ${headerClassName}`}>
        {icon}
        <h2 className="font-bold text-lg">{title}</h2>
        <span className="ml-auto text-sm font-medium opacity-80">{areas.length} area{areas.length !== 1 ? 's' : ''}</span>
      </div>
      {areas.length === 0 ? (
        <p className="px-6 py-8 text-center text-gray-500 text-sm">{emptyMsg}</p>
      ) : (
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {areas.map(renderAreaCard)}
        </div>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Monitored Areas</h1>
          <p className="text-gray-600">{monitoredAreas.length} area{monitoredAreas.length !== 1 ? 's' : ''} total</p>
        </div>
        <Link
          to="/map"
          className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
        >
          <MapPin className="h-4 w-4" />
          <span>Add New Area</span>
        </Link>
      </div>

      {/* Summary Stats */}
      {!loadingAreas && monitoredAreas.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow-sm p-4 border-l-4 border-red-500">
            <div className="text-2xl font-bold text-red-700">{deforestationAreas.length}</div>
            <div className="text-sm text-gray-600 mt-1">⚠️ Deforestation Detected</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-4 border-l-4 border-green-500">
            <div className="text-2xl font-bold text-green-700">{cleanAreas.length}</div>
            <div className="text-sm text-gray-600 mt-1">✅ Clean — Under Monitoring</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-4 border-l-4 border-gray-400">
            <div className="text-2xl font-bold text-gray-600">{notMonitoringAreas.length}</div>
            <div className="text-sm text-gray-600 mt-1">🔘 Not Yet Monitored</div>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="bg-white rounded-lg p-4 shadow-sm">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search monitored areas..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Loading */}
      {loadingAreas && (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mx-auto" />
          <p className="text-gray-600 mt-4">Loading monitored areas…</p>
        </div>
      )}

      {/* No areas at all */}
      {!loadingAreas && monitoredAreas.length === 0 && (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center border-2 border-dashed border-gray-300">
          <MapPin className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-2">No monitored areas yet</p>
          <p className="text-sm text-gray-500 mb-4">Draw an area on the map and click Save Area to start monitoring</p>
          <Link to="/map" className="inline-flex items-center px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">
            Go to Map
          </Link>
        </div>
      )}

      {/* No search results */}
      {!loadingAreas && monitoredAreas.length > 0 && filteredAreas.length === 0 && (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">No areas match your search</p>
        </div>
      )}

      {/* ── Grouped Sections ────────────────────────────────────────── */}
      {!loadingAreas && filteredAreas.length > 0 && (
        <>
          {renderGroup(
            'Deforestation Detected',
            <AlertTriangle className="h-6 w-6 text-red-200" />,
            deforestationAreas,
            'bg-red-700 text-white',
            'No areas with confirmed deforestation — great news!'
          )}

          {renderGroup(
            'Clean Areas — No Deforestation Detected',
            <CheckCircle className="h-6 w-6 text-green-200" />,
            cleanAreas,
            'bg-green-700 text-white',
            'No actively-monitored clean areas yet. Start monitoring an area to track it here.'
          )}

          {notMonitoringAreas.length > 0 && renderGroup(
            'Not Yet Monitored',
            <MapPin className="h-6 w-6 text-gray-400" />,
            notMonitoringAreas,
            'bg-gray-500 text-white',
            'All areas have monitoring started.'
          )}
        </>
      )}
    </div>
  );
};

export default FlaggedAreasPage;
