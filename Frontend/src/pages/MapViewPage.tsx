import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layers, ZoomIn, ZoomOut, Download, Eye, RefreshCw, Calendar } from 'lucide-react';
import { useData } from '../context/DataContext';

const MapViewPage: React.FC = () => {
  const navigate = useNavigate();
  const { alerts, detectionData, selectedRegion, selectedDate } = useData();
  const [mapLayer, setMapLayer] = useState<'satellite' | 'thermal' | 'ndvi'>('satellite');
  const [zoom, setZoom] = useState(12);
  const [showDetections, setShowDetections] = useState(true);
  const [severityFilter, setSeverityFilter] = useState('all');
  const [beforeDate, setBeforeDate] = useState('');
  const [afterDate, setAfterDate] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [mapKey, setMapKey] = useState(0); // Used to force iframe reload only when needed

  // Build backend map URL with date params if provided
  const buildMapUrl = () => {
    // Use the detection markers endpoint that shows all 100+ deforestation sites
    const params = new URLSearchParams();
    params.append('limit', '100'); // Show up to 100 detection markers
    if (beforeDate) params.append('before_date', beforeDate);
    if (afterDate) params.append('after_date', afterDate);
    return `http://localhost:8001/api/map/with-detections?${params.toString()}`;
  };

  const backendMapUrl = buildMapUrl();

  // Refresh map with latest data
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      const params = new URLSearchParams();
      params.append('refresh', 'true');
      if (beforeDate) params.append('before_date', beforeDate);
      if (afterDate) params.append('after_date', afterDate);
      
      const response = await fetch(`http://localhost:8001/api/tiles/generate?${params.toString()}`);
      const data = await response.json();
      
      if (data.success) {
        setLastUpdate(new Date().toLocaleString());
        // Force iframe reload by incrementing key
        setMapKey(prev => prev + 1);
      }
    } catch (error) {
      console.error('Failed to refresh map:', error);
      alert('Failed to refresh map. Please try again.');
    } finally {
      setIsRefreshing(false);
    }
  };

  const regionCoords = {
    bulawayo: { lat: -20.1667, lng: 28.5833 },
    amazon: { lat: -3.4653, lng: -62.2159 },
    congo: { lat: -0.2280, lng: 18.8361 },
    borneo: { lat: 1.5533, lng: 110.3592 }
  };

  const coords = regionCoords[selectedRegion];
  
  const filteredAlerts = alerts.filter(alert => {
    if (severityFilter === 'all') return true;
    return alert.severity === severityFilter;
  });

  const handleMarkerClick = (alert: any) => {
    navigate(`/case/${alert.id}`);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Satellite Map View</h1>
          <p className="text-gray-600">
            Interactive monitoring of {selectedRegion} region • {filteredAlerts.length} detections shown
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className={`px-4 py-2 rounded-lg transition-colors flex items-center space-x-2 ${
              isRefreshing 
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                : 'bg-emerald-600 text-white hover:bg-emerald-700'
            }`}
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh Map'}</span>
          </button>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm"
            title="Filter by severity"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical Only</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Date Selection Controls */}
      <div className="bg-white rounded-lg shadow-sm p-4">
        <div className="flex items-center space-x-4">
          <Calendar className="h-5 w-5 text-gray-400" />
          <div className="flex items-center space-x-4 flex-1">
            <div className="flex items-center space-x-2">
              <label htmlFor="before-date" className="text-sm font-medium text-gray-700">Before:</label>
              <input
                id="before-date"
                type="date"
                value={beforeDate}
                onChange={(e) => setBeforeDate(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            <div className="flex items-center space-x-2">
              <label htmlFor="after-date" className="text-sm font-medium text-gray-700">After:</label>
              <input
                id="after-date"
                type="date"
                value={afterDate}
                onChange={(e) => setAfterDate(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              Apply Dates
            </button>
          </div>
          {lastUpdate && (
            <span className="text-xs text-gray-500">
              Updated: {lastUpdate}
            </span>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          💡 Leave dates empty to use the most recent available imagery (last 60 days)
        </p>
      </div>

      {/* Real Detection Statistics Banner */}
      {detectionData && (
        <div className="bg-gradient-to-r from-emerald-50 to-blue-50 border border-emerald-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="bg-emerald-600 text-white p-2 rounded-lg">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">🛰️ Real Sentinel-2 Satellite Detection</h3>
                <p className="text-sm text-gray-600">
                  Showing {filteredAlerts.length} detected deforestation sites from Google Earth Engine NDVI analysis
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-6 text-sm">
              <div className="text-center">
                <div className="text-2xl font-bold text-emerald-700">{detectionData.activeIncidents.toLocaleString()}</div>
                <div className="text-xs text-gray-600">Total Detections</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{detectionData.deforestedArea.toLocaleString()}</div>
                <div className="text-xs text-gray-600">Hectares Affected</div>
              </div>
              <div className="text-center px-3 py-2 bg-green-100 rounded-lg">
                <div className="text-xs font-semibold text-green-800">✓ LIVE DATA</div>
                <div className="text-xs text-green-700">Real Analysis</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Backend Map Integration */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-2 p-4">Deforestation Map with NDVI Layers</h2>
        <iframe
          key={mapKey}
          src={backendMapUrl}
          title="Deforestation Map"
          className="w-full"
          style={{ height: '600px', border: 'none' }}
        />
        {/* Map Controls integrated with backend map */}
        <div className="bg-gray-50 border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">
                  Region: {selectedRegion} • {filteredAlerts.length} alerts
                </span>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {/* Layer Selector (for backend map) */}
              <select
                value={mapLayer}
                onChange={(e) => setMapLayer(e.target.value as any)}
                className="px-3 py-1 text-sm border border-gray-300 rounded-md bg-white"
                title="Select map layer"
              >
                <option value="satellite">Satellite</option>
                <option value="thermal">Thermal</option>
                <option value="ndvi">NDVI</option>
              </select>
              {/* Detection Toggle (for backend map) */}
              <button
                onClick={() => setShowDetections(!showDetections)}
                className={`px-3 py-1 text-sm rounded-md transition-colors flex items-center space-x-1 ${
                  showDetections 
                    ? 'bg-emerald-100 text-emerald-700' 
                    : 'bg-gray-100 text-gray-700'
                }`}
              >
                <span>Detections</span>
              </button>
              {/* Zoom Controls (for backend map) */}
              <div className="flex items-center space-x-1 border border-gray-300 rounded-md">
                <button
                  onClick={() => setZoom(Math.min(18, zoom + 1))}
                  className="p-1 hover:bg-gray-100 transition-colors"
                >
                  <span>+</span>
                </button>
                <button
                  onClick={() => setZoom(Math.max(8, zoom - 1))}
                  className="p-1 hover:bg-gray-100 transition-colors border-l border-gray-300"
                >
                  <span>-</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MapViewPage;