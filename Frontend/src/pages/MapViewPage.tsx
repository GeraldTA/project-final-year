import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layers, ZoomIn, ZoomOut, Download, Eye } from 'lucide-react';
import { useData } from '../context/DataContext';

const MapViewPage: React.FC = () => {
  const navigate = useNavigate();
  const { alerts, detectionData, selectedRegion, selectedDate } = useData();
  const [mapLayer, setMapLayer] = useState<'satellite' | 'thermal' | 'ndvi'>('satellite');
  const [zoom, setZoom] = useState(12);
  const [showDetections, setShowDetections] = useState(true);
  const [severityFilter, setSeverityFilter] = useState('all');

  // Build backend map URL with query params
  const backendMapUrl = `http://localhost:8000/realistic-photos?t=${Date.now()}`;

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
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical Only</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Backend Map Integration */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Deforestation Map (Backend)</h2>
        <iframe
          src={backendMapUrl}
          title="Deforestation Map"
          width="100%"
          height="600"
          style={{ border: 'none', borderRadius: '12px' }}
        />
        {/* Map Controls integrated with backend map */}
        <div className="bg-gray-50 border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">
                  Last Update: {selectedDate.toLocaleDateString()}
                </span>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {/* Layer Selector (for backend map) */}
              <select
                value={mapLayer}
                onChange={(e) => setMapLayer(e.target.value as any)}
                className="px-3 py-1 text-sm border border-gray-300 rounded-md bg-white"
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