import React, { useEffect, useState } from 'react';
import { RefreshCw, Calendar, Search, Eye, Pencil, Trash2, Play } from 'lucide-react';
import { useData } from '../context/DataContext';
import { apiFetch, apiUrl } from '../utils/api';
import InteractiveMap from '../components/InteractiveMap';

const MapViewPage: React.FC = () => {
  const { alerts, detectionData, selectedRegion } = useData();
  const [mapLayer, setMapLayer] = useState<'satellite' | 'thermal' | 'ndvi'>('satellite');
  const [zoom, setZoom] = useState(12);
  const [showDetections, setShowDetections] = useState(true);
  const [severityFilter, setSeverityFilter] = useState('all');
  const [beforeDate, setBeforeDate] = useState('');
  const [afterDate, setAfterDate] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [mapKey, setMapKey] = useState(0); // Used to force iframe reload only when needed
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<any>(null);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [mapError, setMapError] = useState(false);
  const [mlStatus, setMlStatus] = useState<{ model_loaded: boolean; model_type?: string; pretrained_repo?: string } | null>(null);
  const [mlStatusError, setMlStatusError] = useState<string | null>(null);
  const [mlAutoRunning, setMlAutoRunning] = useState(false);
  const [mlAutoResult, setMlAutoResult] = useState<any>(null);
  const [mlAutoError, setMlAutoError] = useState<string | null>(null);
  const [seasonalWarning, setSeasonalWarning] = useState<string | null>(null);
  const [showBeforeAfterImages, setShowBeforeAfterImages] = useState(false);
  const [imageVisualization, setImageVisualization] = useState<'rgb' | 'nir' | 'ndvi'>('rgb');
  const [gridScanRunning, setGridScanRunning] = useState(false);
  const [gridScanResult, setGridScanResult] = useState<any>(null);
  const [gridScanError, setGridScanError] = useState<string | null>(null);
  const [selectedCell, setSelectedCell] = useState<any>(null);
  const [testMlRunning, setTestMlRunning] = useState(false);
  const [testMlResult, setTestMlResult] = useState<any>(null);
  const [testMlError, setTestMlError] = useState<string | null>(null);
  const [showCellImages, setShowCellImages] = useState(false);
  const [zoomedImage, setZoomedImage] = useState<string | null>(null);
  const [imageZoom, setImageZoom] = useState(1);
  const [detectionMapUrl, setDetectionMapUrl] = useState<string | null>(null);
  const [showDetectionOverlay, setShowDetectionOverlay] = useState(true);
  const [zoomedImageContext, setZoomedImageContext] = useState<{
    isAfterImage: boolean;
    hasDetection: boolean;
    deforestationPercent?: number;
    forestLoss?: number;
  } | null>(null);

  // New states for monitored areas
  const [useInteractiveMap, setUseInteractiveMap] = useState(false);
  const [monitoredAreas, setMonitoredAreas] = useState<any[]>([]);
  const [drawnCoordinates, setDrawnCoordinates] = useState<[number, number][] | null>(null);
  const [showSaveAreaDialog, setShowSaveAreaDialog] = useState(false);
  const [newAreaName, setNewAreaName] = useState('');
  const [newAreaDescription, setNewAreaDescription] = useState('');
  const [selectedMonitoredArea, setSelectedMonitoredArea] = useState<any>(null);
  const [areaDetectionRunning, setAreaDetectionRunning] = useState(false);
  const [areaDetectionResult, setAreaDetectionResult] = useState<any>(null);
  const [areaDates, setAreaDates] = useState<{ [key: string]: { before: string; after: string } }>({});
  const [showDatePicker, setShowDatePicker] = useState<string | null>(null);
  const [areaError, setAreaError] = useState<string | null>(null);

  const fetchMlStatus = async () => {
    try {
      setMlStatusError(null);
      const res = await apiFetch('/api/ml/status');
      if (!res.ok) throw new Error(`ML status request failed (${res.status})`);
      const data = await res.json();
      setMlStatus(data);
    } catch (e: any) {
      setMlStatus(null);
      setMlStatusError(e?.message || 'ML status unavailable');
    }
  };

  useEffect(() => {
    fetchMlStatus();
  }, []);

  // Keyboard shortcuts for zoom modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!zoomedImage) return;
      
      if (e.key === 'Escape') {
        setZoomedImage(null);
        setImageZoom(1);
        setZoomedImageContext(null);
      } else if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        setImageZoom(prev => Math.min(5, prev + 0.25));
      } else if (e.key === '-' || e.key === '_') {
        e.preventDefault();
        setImageZoom(prev => Math.max(0.5, prev - 0.25));
      } else if (e.key === '0') {
        e.preventDefault();
        setImageZoom(1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [zoomedImage]);

  const updateMapWithDetection = async (detectionData: any) => {
    try {
      const payload = {
        latitude: selectedLocation?.latitude || (selectedLocation?.bounds ? 
          (selectedLocation.bounds.min_lat + selectedLocation.bounds.max_lat) / 2 : 0),
        longitude: selectedLocation?.longitude || (selectedLocation?.bounds ? 
          (selectedLocation.bounds.min_lng + selectedLocation.bounds.max_lng) / 2 : 0),
        prediction: detectionData.prediction || 'Unknown',
        confidence: detectionData.confidence || 0,
        before_date: detectionData.before?.date || beforeDate || 'Unknown',
        after_date: detectionData.after?.date || afterDate || 'Unknown',
        zoom: 13
      };

      const res = await apiFetch('/api/map/set-ml-detection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        // Set the detection map URL which will cause iframe to reload
        setDetectionMapUrl(apiUrl('/api/map/with-ml-detection'));
        setMapKey(prev => prev + 1); // Force map reload
        console.log('✅ Detection map will be displayed');
      }
    } catch (e) {
      console.error('Failed to update map with detection:', e);
    }
  };

  const runGridScan = async () => {
    setGridScanError(null);
    setGridScanResult(null);
    setSelectedCell(null);

    if (!mlStatus?.model_loaded) {
      setGridScanError('ML model is offline. Start the backend first.');
      return;
    }
    if (!selectedLocation?.bounds) {
      setGridScanError('Select a location using Search first.');
      return;
    }
    if (!beforeDate || !afterDate) {
      setGridScanError('Pick both Before and After dates.');
      return;
    }

    const b = selectedLocation.bounds;
    const params = new URLSearchParams({
      location_name: selectedLocation.name || 'Unknown',
      before_date: beforeDate,
      after_date: afterDate,
      west: String(b.min_lng ?? b.west),
      south: String(b.min_lat ?? b.south),
      east: String(b.max_lng ?? b.east),
      north: String(b.max_lat ?? b.north),
      grid_size: '3',
      window_days: '30',
      max_cloud_cover: '50',
      dimensions: '256'
    });

    setGridScanRunning(true);
    try {
      const res = await apiFetch(`/api/ml/scan-area-grid?${params.toString()}`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error(`Grid scan failed (${res.status})`);
      const data = await res.json();
      console.log('Grid scan result:', data);
      console.log('First cell:', data.cells?.[0]);
      setGridScanResult(data);
    } catch (e: any) {
      setGridScanError(e?.message || 'Grid scan failed');
    } finally {
      setGridScanRunning(false);
    }
  };

  const runTestMlDetection = async () => {
    setTestMlError(null);
    setTestMlResult(null);
    setTestMlRunning(true);

    try {
      const res = await apiFetch('/api/ml/test-with-cached', {
        method: 'POST'
      });
      if (!res.ok) throw new Error(`Test ML failed (${res.status})`);
      const data = await res.json();
      console.log('Test ML result:', data);
      setTestMlResult(data);
    } catch (e: any) {
      setTestMlError(e?.message || 'Test ML detection failed');
    } finally {
      setTestMlRunning(false);
    }
  };

  const runMlAutoChangeDetection = async () => {
    setMlAutoError(null);
    setMlAutoResult(null);
    setSeasonalWarning(null);

    if (!mlStatus?.model_loaded) {
      setMlAutoError('ML model is offline. Start the backend first.');
      return;
    }
    if (!selectedLocation?.bounds) {
      setMlAutoError('Select a location using Search first (so we have bounds).');
      return;
    }
    if (!beforeDate || !afterDate) {
      setMlAutoError('Pick both Before and After dates.');
      return;
    }

    const b = selectedLocation.bounds;
    const params = new URLSearchParams({
      before_date: beforeDate,
      after_date: afterDate,
      west: String(b.min_lng ?? b.west),
      south: String(b.min_lat ?? b.south),
      east: String(b.max_lng ?? b.east),
      north: String(b.max_lat ?? b.north),
      window_days: '30',  // Reduced from 60 to 30 days for better date accuracy
      max_cloud_cover: '80',
      scale: '10',
      dimensions: '512'
    });

    setMlAutoRunning(true);
    setMlAutoError(null);  // Clear previous errors
    try {
      const res = await apiFetch(`/api/ml/detect-change-auto?${params.toString()}`, {
        method: 'POST'
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        const errorMsg = errorData.detail || `Auto ML request failed (${res.status})`;
        throw new Error(errorMsg);
      }
      const data = await res.json();
      console.log('📊 ML Auto Result:', data);
      console.log('📁 Exports:', data.exports);
      if (data.exports) {
        console.log('   Before path:', data.exports.before?.path);
        console.log('   After path:', data.exports.after?.path);
        if (data.exports.before?.path) {
          const beforeFile = data.exports.before.path.split('/').pop();
          console.log('   ✅ Before filename:', beforeFile);
        }
      }
      setMlAutoResult(data);
      if (data.seasonal_warning) {
        setSeasonalWarning(data.seasonal_warning);
      }
      
      // Update map with detection markers
      if (data.prediction && selectedLocation?.latitude && selectedLocation?.longitude) {
        updateMapWithDetection(data);
      }
    } catch (e: any) {
      setMlAutoError(e?.message || 'Auto ML request failed');
    } finally {
      setMlAutoRunning(false);
    }
  };

  // Build backend map URL with date params if provided
  const buildMapUrl = () => {
    // If we have a detection map, use that
    if (detectionMapUrl) {
      return detectionMapUrl;
    }
    
    // Use fallback to static map if API server is having issues
    if (mapError) {
      return `http://localhost:8080/realistic_satellite_photos.html`;
    }
    
    // Use the detection markers endpoint that shows all 100+ deforestation sites
    const params = new URLSearchParams();
    params.append('limit', '100'); // Show up to 100 detection markers
    if (beforeDate) params.append('before_date', beforeDate);
    if (afterDate) params.append('after_date', afterDate);
    if (searchQuery) params.append('search', searchQuery);
    if (selectedLocation) {
      params.append('center_lat', selectedLocation.center.lat.toString());
      params.append('center_lng', selectedLocation.center.lng.toString());
      params.append('zoom', '10');
    }
    return apiUrl(`/api/map/with-detections?${params.toString()}`);
  };

  // Search for forest/location
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      setSelectedLocation(null);
      setMapKey(prev => prev + 1);
      return;
    }
    
    try {
      const response = await apiFetch(`/api/search/location?query=${encodeURIComponent(searchQuery)}`);
      const data = await response.json();
      
      if (data.success) {
        setSearchResults(data.results || []);
        // Auto-select first result if available
        if (data.results && data.results.length > 0) {
          const firstResult = data.results[0];
          setSelectedLocation({
            name: firstResult.display_name,
            latitude: firstResult.latitude,
            longitude: firstResult.longitude,
            bounds: firstResult.bounds,
            center: { 
              lat: firstResult.latitude, 
              lng: firstResult.longitude 
            }
          });
        }
      } else {
        setSearchResults([]);
        setSelectedLocation(null);
        alert(data.message || 'No results found. Try a different search term.');
      }
      
      setMapKey(prev => prev + 1); // Reload map with search filter
    } catch (error) {
      console.error('Search failed:', error);
      setSearchResults([]);
      setSelectedLocation(null);
      alert('Search failed. Please try again.');
    }
  };

  // Select a location from search results
  const selectSearchResult = (result: any) => {
    setSelectedLocation({
      name: result.display_name,
      latitude: result.latitude,
      longitude: result.longitude,
      bounds: result.bounds,
      center: { 
        lat: result.latitude, 
        lng: result.longitude 
      }
    });
    // Optionally close/collapse search results after selection
    // setSearchResults([]);
  };

  // Start monitoring a location
  const handleStartMonitoring = async () => {
    if (!selectedLocation) return;
    
    setIsMonitoring(true);
    try {
      const response = await apiFetch('/api/monitoring/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          location: selectedLocation.name,
          region: searchQuery,
          bounds: selectedLocation.bounds,
          start_date: new Date().toISOString()
        })
      });
      
      const data = await response.json();
      if (data.success) {
        alert(`✅ Monitoring started for ${selectedLocation.name}\n\nThe system will check this area every 5 days for deforestation activity.`);
      } else {
        alert('Failed to start monitoring: ' + (data.message || 'Unknown error'));
      }
    } catch (error) {
      console.error('Failed to start monitoring:', error);
      alert('Failed to start monitoring. Please try again.');
    } finally {
      setIsMonitoring(false);
    }
  };

  // ========================================
  // Monitored Areas Functions
  // ========================================

  const fetchMonitoredAreas = async () => {
    try {
      const res = await apiFetch('/api/monitored-areas');
      if (res.ok) {
        const data = await res.json();
        setMonitoredAreas(data.areas || []);
      }
    } catch (e) {
      console.error('Failed to fetch monitored areas:', e);
    }
  };

  useEffect(() => {
    if (useInteractiveMap) {
      fetchMonitoredAreas();
    }
  }, [useInteractiveMap]);

  const handleAreaDrawn = (coordinates: [number, number][]) => {
    setDrawnCoordinates(coordinates);
    setShowSaveAreaDialog(true);
  };

  const saveMonitoredArea = async () => {
    if (!drawnCoordinates || !newAreaName.trim()) {
      alert('Please provide an area name');
      return;
    }

    try {
      const res = await apiFetch('/api/monitored-areas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newAreaName,
          description: newAreaDescription,
          coordinates: drawnCoordinates,
          continuous_monitoring: true,
          alert_enabled: true
        })
      });

      if (res.ok) {
        const data = await res.json();
        setMonitoredAreas(prev => [...prev, data.area]);
        setShowSaveAreaDialog(false);
        setNewAreaName('');
        setNewAreaDescription('');
        setDrawnCoordinates(null);
        alert(`✅ Area "${data.area.name}" saved successfully!`);
      } else {
        const error = await res.json();
        alert(`Failed to save area: ${error.error}`);
      }
    } catch (e) {
      console.error('Error saving monitored area:', e);
      alert('Failed to save monitored area. Please try again.');
    }
  };

  const deleteMonitoredArea = async (areaId: string) => {
    if (!confirm('Are you sure you want to delete this monitored area?')) {
      return;
    }

    try {
      const res = await apiFetch(`/api/monitored-areas/${areaId}`, {
        method: 'DELETE'
      });

      if (res.ok) {
        setMonitoredAreas(prev => prev.filter(a => a.id !== areaId));
        if (selectedMonitoredArea?.id === areaId) {
          setSelectedMonitoredArea(null);
          setAreaDetectionResult(null);
        }
        alert('✅ Area deleted successfully!');
      } else {
        alert('Failed to delete area');
      }
    } catch (e) {
      console.error('Error deleting area:', e);
      alert('Failed to delete area. Please try again.');
    }
  };

  const runDetectionOnArea = async (areaId: string) => {
    // Get dates FIRST before setting any state
    const dates = areaDates[areaId];
    
    console.log('=== RUN DETECTION CALLED ===');
    console.log('Area ID:', areaId);
    console.log('Dates from state:', dates);
    console.log('All areaDates:', areaDates);
    
    // CRITICAL: Validate dates exist BEFORE starting
    if (!dates?.before || !dates?.after) {
      const errorMsg = 'ERROR: No dates selected!\n\n' +
                      'You must:\n' +
                      '1. Click "Select Date Range"\n' +
                      '2. Choose both Before and After dates\n' +
                      '3. Then click "Run Detection Now"';
      alert(errorMsg);
      console.error('DATES MISSING:', { areaId, dates, allDates: areaDates });
      return; // Exit immediately - don't even start the request
    }
    
    console.log('✓ Dates validated, starting detection...');
    console.log(`Before: ${dates.before}, After: ${dates.after}`);
    
    setAreaDetectionRunning(true);
    setAreaDetectionResult(null);
    setAreaError(null);

    try {
      const params = {
        before_date: dates.before,
        after_date: dates.after
      };
      
      console.log('=== SENDING REQUEST ===');
      console.log('Request body:', params);
      console.log('Request URL:', `/api/monitored-areas/${areaId}/detect`);

      const res = await apiFetch(`/api/monitored-areas/${areaId}/detect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });

      console.log('Response status:', res.status);
      console.log('Response OK:', res.ok);

      if (res.ok) {
        const data = await res.json();
        console.log('Detection result data:', data);
        setAreaDetectionResult(data.detection_result);
        
        // CRITICAL: Set selected area so results display
        const area = monitoredAreas.find(a => a.id === areaId);
        if (area) {
          setSelectedMonitoredArea({
            ...area,
            last_monitored: data.area.last_monitored,
            detection_history: data.area.detection_history
          });
        }
        
        // Update the area's last monitored time in the list
        setMonitoredAreas(prev => prev.map(a => 
          a.id === areaId ? { 
            ...a, 
            last_monitored: data.area.last_monitored,
            detection_history: data.area.detection_history,
            detection_count: data.area.detection_count
          } : a
        ));
        setAreaError(null);
        console.log('=== DETECTION SUCCESS - RESULTS SHOULD DISPLAY ===');
      } else {
        const errorData = await res.json();
        console.error('Error response:', errorData);
        setAreaError(`Detection failed for area: ${errorData.error || errorData.detail || 'Unknown error'}`);
        console.log('=== DETECTION FAILED ===');
      }
    } catch (e: any) {
      console.error('Exception during detection:', e);
      console.error('Error stack:', e.stack);
      setAreaError(`Detection failed: ${e.message || 'Please try again.'}`);
      console.log('=== DETECTION EXCEPTION ===');
    } finally {
      setAreaDetectionRunning(false);
      console.log('=== DETECTION REQUEST END ===');
    }
  };

  const handleAreaClick = (areaId: string) => {
    const area = monitoredAreas.find(a => a.id === areaId);
    if (area) {
      setSelectedMonitoredArea(area);
      setAreaDetectionResult(null);
    }
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
      
      const response = await apiFetch(`/api/tiles/generate?${params.toString()}`);
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

  const filteredAlerts = alerts.filter(alert => {
    if (severityFilter === 'all') return true;
    return alert.severity === severityFilter;
  });

  // (Navigation retained for other pages; map markers are rendered server-side in the iframe.)

  return (
    <div className="space-y-6">
      {/* Feature Highlight Banner */}
      <div className="bg-gradient-to-r from-emerald-500 to-green-600 text-white rounded-lg p-4 shadow-lg">
        <div className="flex items-start space-x-3">
          <div className="text-2xl">🌍</div>
          <div className="flex-1">
            <h3 className="font-bold text-lg">Search ANY Location in Zimbabwe!</h3>
            <p className="text-sm text-emerald-50 mt-1">
              Just like Google Maps - type any place name, city, park, or coordinates in the search box below. 
              The system will find it and you can analyze it for deforestation instantly!
            </p>
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              <span className="bg-white/20 px-2 py-1 rounded">🏙️ Cities</span>
              <span className="bg-white/20 px-2 py-1 rounded">🌳 National Parks</span>
              <span className="bg-white/20 px-2 py-1 rounded">🏘️ Villages</span>
              <span className="bg-white/20 px-2 py-1 rounded">🗺️ Regions</span>
              <span className="bg-white/20 px-2 py-1 rounded">📍 Coordinates</span>
            </div>
          </div>
        </div>
      </div>

      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Satellite Map View</h1>
          <p className="text-gray-600">
            Interactive monitoring of {selectedRegion} region • {filteredAlerts.length} detections shown
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="px-3 py-2 rounded-lg border bg-white text-sm">
            <div className="flex items-center gap-2">
              <span className="font-medium">ML</span>
              {mlStatus?.model_loaded ? (
                <span className="text-emerald-700">Online</span>
              ) : (
                <span className="text-amber-700">Offline</span>
              )}
            </div>
            <div className="text-xs text-gray-500">
              {mlStatus?.model_type || (mlStatusError ? mlStatusError : 'Checking...')}
            </div>
          </div>
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
          <button
            onClick={fetchMlStatus}
            className="px-4 py-2 rounded-lg transition-colors bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
            title="Refresh ML status"
          >
            ML Status
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

      {/* Search Bar */}
      <div className="bg-white rounded-lg shadow-sm p-4">
        <div className="flex items-center space-x-4">
          <Search className="h-5 w-5 text-gray-400" />
          <div className="flex-1 flex items-center space-x-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search anywhere in Zimbabwe (e.g., Harare, Victoria Falls, Mana Pools, -17.8252,31.0335...)"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
            <button
              onClick={handleSearch}
              className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors flex items-center space-x-2"
            >
              <Search className="h-4 w-4" />
              <span>Search</span>
            </button>
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSearchResults([]);
                  setSelectedLocation(null);
                  setMapKey(prev => prev + 1);
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors text-sm"
              >
                Clear
              </button>
            )}
          </div>
        </div>
        
        {/* Search Results Dropdown */}
        {searchResults.length > 0 && (
          <div className="mt-3 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-y-auto">
            <div className="p-3 bg-emerald-50 border-b border-emerald-200">
              <p className="text-sm font-medium text-emerald-800">
                Found {searchResults.length} location{searchResults.length !== 1 ? 's' : ''} for "{searchQuery}"
              </p>
              <p className="text-xs text-emerald-600 mt-1">
                Click any result to view on map and analyze for deforestation
              </p>
            </div>
            <div className="divide-y divide-gray-100">
              {searchResults.map((result, idx) => (
                <div 
                  key={result.place_id || idx}
                  onClick={() => selectSearchResult(result)}
                  className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                    selectedLocation?.latitude === result.latitude && 
                    selectedLocation?.longitude === result.longitude 
                      ? 'bg-emerald-50 border-l-4 border-emerald-500' 
                      : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg">📍</span>
                        <p className="text-sm font-medium text-gray-900">
                          {result.display_name}
                        </p>
                      </div>
                      <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                        <span>📐 {result.latitude.toFixed(4)}°, {result.longitude.toFixed(4)}°</span>
                        <span className="capitalize">🏷️ {result.type}</span>
                        {result.address?.state && (
                          <span>📍 {result.address.state}</span>
                        )}
                      </div>
                    </div>
                    <div className="ml-4 flex items-center space-x-2">
                      {selectedLocation?.latitude === result.latitude && 
                       selectedLocation?.longitude === result.longitude && (
                        <span className="px-2 py-1 bg-emerald-100 text-emerald-700 text-xs rounded-full font-medium">
                          Selected
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(selectedLocation) && (
          <div className="mt-3 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm text-blue-800 font-medium flex items-center space-x-2">
                  <span className="text-lg">🗺️</span>
                  <span>Selected Location: {selectedLocation?.name}</span>
                </p>
                {selectedLocation && (
                  <div className="mt-2 space-y-1 text-xs text-blue-600">
                    <p>📍 Coordinates: {selectedLocation.center.lat.toFixed(4)}°, {selectedLocation.center.lng.toFixed(4)}°</p>
                    <p>📏 Coverage: ~10km × 10km area</p>
                    <p className="font-medium text-emerald-700">
                      ✨ You can search ANY location in Zimbabwe! Just type the name above.
                    </p>
                  </div>
                )}
              </div>
              <button
                onClick={handleStartMonitoring}
                disabled={isMonitoring || !selectedLocation}
                className={`px-4 py-2 rounded-lg transition-colors flex items-center space-x-2 ${
                  isMonitoring || !selectedLocation
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                <Eye className="h-4 w-4" />
                <span>{isMonitoring ? 'Starting...' : '🛰️ Monitor'}</span>
              </button>
            </div>
            <div className="mt-3 text-xs text-blue-700 bg-blue-100 p-2 rounded">
              💡 <strong>Monitoring:</strong> Automatically checks this area every 5 days for deforestation
            </div>
            <div className="mt-3">
              <button
                onClick={runGridScan}
                disabled={gridScanRunning || !selectedLocation || !beforeDate || !afterDate}
                className={`w-full px-4 py-2 rounded-lg transition-colors flex items-center justify-center space-x-2 ${
                  gridScanRunning || !selectedLocation || !beforeDate || !afterDate
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-purple-600 text-white hover:bg-purple-700'
                }`}
              >
                {gridScanRunning && (
                  <svg className="animate-spin h-4 w-4 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                <span>{gridScanRunning ? 'Scanning Grid... (may take several minutes)' : '🗺️ Scan Area for Deforestation (Grid Analysis)'}</span>
              </button>
              <p className="text-xs text-gray-600 mt-1">
                Divides the area into a 3x3 grid and detects deforestation in each cell
              </p>
              {gridScanRunning && (
                <div className="mt-3 p-3 bg-purple-50 border border-purple-200 rounded-lg">
                  <div className="flex items-center space-x-2 mb-2">
                    <div className="animate-pulse h-2 w-2 bg-purple-500 rounded-full"></div>
                    <span className="text-sm font-medium text-purple-800">Analyzing area...</span>
                  </div>
                  <div className="text-xs text-purple-700 space-y-1">
                    <div>✓ Dividing area into 3×3 grid (9 cells)</div>
                    <div>✓ Downloading Sentinel-2 satellite imagery</div>
                    <div>✓ Running ML analysis on each cell</div>
                    <div className="animate-pulse">⏳ Please wait 2-5 minutes...</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Grid Scan Results */}
      {gridScanResult && (
        <div className="bg-white rounded-lg shadow-sm p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">📊 Grid Scan Results: {gridScanResult.location_name}</h2>
          <div className="mb-3 flex items-center space-x-4 text-sm">
            <span className="text-gray-700">Total Cells: {gridScanResult.total_cells}</span>
            <span className="text-red-600 font-semibold">⚠️ Deforested: {gridScanResult.deforested_cells}</span>
            <span className="text-emerald-600">✓ Stable: {gridScanResult.total_cells - gridScanResult.deforested_cells}</span>
          </div>
          {gridScanError && <div className="text-red-700 text-sm mb-3">{gridScanError}</div>}
          <div className="grid grid-cols-3 gap-2">
            {gridScanResult.cells.map((cell: any) => (
              <div
                key={cell.id}
                onClick={() => {
                  console.log('Selected cell:', cell);
                  console.log('Has before_image_file?', !!cell.before_image_file);
                  console.log('Has after_image_file?', !!cell.after_image_file);
                  setSelectedCell(cell);
                  setShowCellImages(true);
                }}
                className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                  cell.deforestation_detected
                    ? 'border-red-500 bg-red-50 hover:bg-red-100'
                    : 'border-emerald-500 bg-emerald-50 hover:bg-emerald-100'
                } ${selectedCell?.id === cell.id ? 'ring-2 ring-blue-500' : ''}`}
              >
                <div className="text-xs font-semibold mb-1">
                  {cell.deforestation_detected ? '🚨 Deforestation' : '✅ Stable'}
                </div>
                <div className="text-xs text-gray-700">
                  <div>Lat: {cell.center.lat.toFixed(4)}</div>
                  <div>Lng: {cell.center.lng.toFixed(4)}</div>
                  {cell.deforestation_detected && (
                    <div className="mt-1 text-red-700 font-medium">
                      Drop: {(cell.forest_drop * 100).toFixed(1)}%
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 text-xs text-gray-600 italic">
            💡 Click any cell to view before/after satellite images
          </div>
        </div>
      )}

      {/* Cell Image Viewer Modal */}
      {selectedCell && showCellImages && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowCellImages(false)}>
          <div className="bg-white rounded-lg p-6 max-w-5xl w-full m-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-xl font-bold">
                  {selectedCell.deforestation_detected ? '🚨 Deforestation Detected' : '✅ No Deforestation'}
                </h3>
                <p className="text-sm text-gray-600">Cell: {selectedCell.id} | Lat: {selectedCell.center.lat.toFixed(4)}, Lng: {selectedCell.center.lng.toFixed(4)}</p>
              </div>
              <button
                onClick={() => setShowCellImages(false)}
                className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
              >
                ×
              </button>
            </div>
            
            <div className="mb-4 grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium">Before Forest:</span> {(selectedCell.before_forest_probability * 100).toFixed(1)}%
              </div>
              <div>
                <span className="font-medium">After Forest:</span> {(selectedCell.after_forest_probability * 100).toFixed(1)}%
              </div>
              <div>
                <span className="font-medium">Forest Drop:</span> {(selectedCell.forest_drop * 100).toFixed(1)}%
              </div>
              <div>
                <span className="font-medium">NDVI Drop:</span> {selectedCell.ndvi_drop.toFixed(3)}
              </div>
            </div>

            <div className="flex gap-2 items-center mb-3">
              <label htmlFor="cell-viz" className="text-sm font-medium text-gray-700">Visualization:</label>
              <select
                id="cell-viz"
                value={imageVisualization}
                onChange={(e) => setImageVisualization(e.target.value as 'rgb' | 'nir' | 'ndvi')}
                className="text-sm px-2 py-1 border border-gray-300 rounded"
              >
                <option value="rgb">True Color (RGB)</option>
                <option value="nir">False Color (NIR)</option>
                <option value="ndvi">NDVI (Vegetation)</option>
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-sm font-semibold text-gray-700 mb-2">Before ({gridScanResult?.scan_dates?.before})</div>
                {selectedCell?.before_image_file ? (
                  <div 
                    className="relative group cursor-zoom-in"
                    onClick={() => {
                      console.log('🔍 Grid before image clicked!');
                      setZoomedImage(apiUrl(`/api/ml/preview-geotiff/${selectedCell.before_image_file}?band_combo=${imageVisualization}`));
                      setImageZoom(1);
                      setZoomedImageContext({ isAfterImage: false, hasDetection: false });
                    }}
                  >
                    <img
                      src={apiUrl(`/api/ml/preview-geotiff/${selectedCell.before_image_file}?band_combo=${imageVisualization}`)}
                      alt="Before satellite view"
                      className="w-full rounded border border-gray-300 pointer-events-none"
                      onLoad={() => console.log('✅ Before image loaded successfully')}
                      onError={(e) => {
                        console.error('❌ Failed to load before image:', apiUrl(`/api/ml/preview-geotiff/${selectedCell.before_image_file}?band_combo=${imageVisualization}`));
                        const img = e.target as HTMLImageElement;
                        img.style.display = 'none';
                        const parent = img.parentElement;
                        if (parent && !parent.querySelector('.bg-red-50')) {
                          const errorDiv = document.createElement('div');
                          errorDiv.className = 'bg-red-50 rounded p-4 text-center text-sm text-red-600';
                          errorDiv.textContent = `Image failed: ${selectedCell.before_image_file}`;
                          parent.appendChild(errorDiv);
                        }
                      }}
                    />
                    <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100 rounded pointer-events-none">
                      <span className="text-white text-sm bg-black bg-opacity-50 px-3 py-1 rounded">🔍 Click to zoom</span>
                    </div>
                  </div>
                ) : (
                  <div className="bg-gray-100 rounded p-8 text-center text-sm text-gray-500">
                    Before image not available (filename: {selectedCell?.before_image_file || 'null'})
                  </div>
                )}
              </div>
              <div>
                <div className="text-sm font-semibold text-gray-700 mb-2">After ({gridScanResult?.scan_dates?.after})</div>
                {selectedCell?.after_image_file ? (
                  <div 
                    className="relative group cursor-zoom-in"
                    onClick={() => {
                      console.log('🔍 Grid after image clicked!');
                      setZoomedImage(apiUrl(`/api/ml/preview-geotiff/${selectedCell.after_image_file}?band_combo=${imageVisualization}`));
                      setImageZoom(1);
                      setZoomedImageContext({
                        isAfterImage: true,
                        hasDetection: selectedCell?.forest_drop > 0.1,
                        forestLoss: selectedCell?.forest_drop ? selectedCell.forest_drop * 100 : undefined
                      });
                    }}
                  >
                    <img
                      src={apiUrl(`/api/ml/preview-geotiff/${selectedCell.after_image_file}?band_combo=${imageVisualization}`)}
                      alt="After satellite view"
                      className="w-full rounded border border-gray-300 pointer-events-none"
                      onLoad={() => console.log('✅ After image loaded successfully')}
                      onError={(e) => {
                        console.error('❌ Failed to load after image:', apiUrl(`/api/ml/preview-geotiff/${selectedCell.after_image_file}?band_combo=${imageVisualization}`));
                        const img = e.target as HTMLImageElement;
                        img.style.display = 'none';
                        const parent = img.parentElement;
                        if (parent && !parent.querySelector('.bg-red-50')) {
                          const errorDiv = document.createElement('div');
                          errorDiv.className = 'bg-red-50 rounded p-4 text-center text-sm text-red-600';
                          errorDiv.textContent = `Image failed: ${selectedCell.after_image_file}`;
                          parent.appendChild(errorDiv);
                        }
                      }}
                    />
                    
                    {/* Deforestation Detection Overlay for Grid Cell */}
                    {selectedCell?.forest_drop > 0.1 && (
                      <div className="absolute inset-0 pointer-events-none">
                        {/* Central detection marker */}
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="relative">
                            <div className="absolute inset-0 bg-red-500 rounded-full opacity-20 animate-ping" style={{ width: '60px', height: '60px', marginLeft: '-30px', marginTop: '-30px' }}></div>
                            <div className="relative bg-red-600 bg-opacity-30 border-3 border-red-600 rounded-full" style={{ width: '60px', height: '60px', marginLeft: '-30px', marginTop: '-30px' }}>
                              <div className="absolute inset-0 flex items-center justify-center">
                                <div className="bg-red-600 text-white rounded-full w-10 h-10 flex items-center justify-center text-sm font-bold shadow-lg">
                                  ⚠️
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        {/* Forest drop indicator */}
                        <div className="absolute top-2 right-2 bg-red-600 text-white text-xs px-2 py-1 rounded shadow-lg font-semibold">
                          Loss: {(selectedCell.forest_drop * 100).toFixed(0)}%
                        </div>
                      </div>
                    )}
                    
                    <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100 rounded pointer-events-none">
                      <span className="text-white text-sm bg-black bg-opacity-50 px-3 py-1 rounded">🔍 Click to zoom</span>
                    </div>
                  </div>
                ) : (
                  <div className="bg-gray-100 rounded p-8 text-center text-sm text-gray-500">
                    After image not available (filename: {selectedCell?.after_image_file || 'null'})
                  </div>
                )}
              </div>
            </div>

            <div className="mt-4 text-xs text-gray-500 italic">
              💡 RGB shows true color, NIR highlights vegetation in red, NDVI shows vegetation health in green
            </div>
          </div>
        </div>
      )}

      {gridScanError && (
        <div className="bg-red-50 rounded-lg p-4 border border-red-200">
          <p className="text-red-700 text-sm">{gridScanError}</p>
        </div>
      )}

      {/* ML Auto Change Detection */}
      <div className="bg-white rounded-lg shadow-sm p-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">ML Change Detection (Auto)</h2>
            <p className="text-sm text-gray-600">Uses GEE to fetch Sentinel-2 10-band imagery automatically.</p>
            <p className="text-xs text-amber-700 mt-1">⚠️ Compare same-season images (e.g., Jan→Jan) to avoid false positives from seasonal vegetation changes.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={runMlAutoChangeDetection}
              disabled={mlAutoRunning}
              className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                mlAutoRunning ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-indigo-600 text-white hover:bg-indigo-700'
              }`}
            >
              {mlAutoRunning && (
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
              <span>{mlAutoRunning ? 'Running… (may take a minute)' : 'Run ML Change Detection'}</span>
            </button>
            <button
              onClick={runTestMlDetection}
              disabled={testMlRunning}
              className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                testMlRunning ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-emerald-600 text-white hover:bg-emerald-700'
              }`}
              title="Test ML model with cached imagery (no Earth Engine needed)"
            >
              {testMlRunning && (
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
              <span>{testMlRunning ? 'Testing...' : '🧪 Test ML (Cached)'}</span>
            </button>
          </div>
        </div>

        {mlAutoRunning && (
          <div className="mt-3 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <div className="animate-pulse h-2 w-2 bg-indigo-500 rounded-full"></div>
              <span className="text-sm font-medium text-indigo-800">Processing detection...</span>
            </div>
            <div className="text-xs text-indigo-700 space-y-1">
              <div>🛰️ Downloading Sentinel-2 imagery from Google Earth Engine</div>
              <div>🤖 Running BigEarthNet ResNet-50 ML model</div>
              <div className="animate-pulse">⏳ Estimated time: 30-60 seconds</div>
            </div>
          </div>
        )}

        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label htmlFor="ml-before-date" className="block text-xs text-gray-600 mb-1">Before date</label>
            <input
              id="ml-before-date"
              type="date"
              value={beforeDate}
              onChange={(e) => setBeforeDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label htmlFor="ml-after-date" className="block text-xs text-gray-600 mb-1">After date</label>
            <input
              id="ml-after-date"
              type="date"
              value={afterDate}
              onChange={(e) => setAfterDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
        </div>
        
        <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800">
          <div className="font-medium mb-1">ℹ️ How date selection works:</div>
          <div>• System searches ±30 days around each date for cloud-free images</div>
          <div>• Choose dates from the same season (e.g., Jan→Jan) for best results</div>
          <div>• For Zimbabwe: avoid Oct-Apr (rainy season) for clearer images</div>
        </div>

        <div className="mt-3 text-sm">
          <div className="text-gray-700">
            <span className="font-medium">Target:</span>{' '}
            {selectedLocation?.name ? selectedLocation.name : 'No location selected'}
          </div>
          {mlAutoError && <div className="mt-2 text-red-700">{mlAutoError}</div>}
          
          {/* Test ML Result */}
          {testMlResult && (
            <div className="mt-3 p-3 rounded-lg border-2 border-emerald-200 bg-emerald-50">
              <div className="flex items-center justify-between mb-2">
                <div className="font-semibold text-emerald-900">✅ ML Model Test Result</div>
                <span className="text-xs px-2 py-1 bg-emerald-200 text-emerald-800 rounded-full">Test Mode</span>
              </div>
              <div className="text-xs text-emerald-800 space-y-1">
                <div className="font-medium">Status: {testMlResult.status}</div>
                <div>Deforestation Detected: <span className={testMlResult.deforestation_detected ? 'text-red-700 font-bold' : 'text-emerald-700 font-bold'}>
                  {testMlResult.deforestation_detected ? 'YES' : 'NO'}
                </span></div>
                <div>Forest Probability Drop: {(testMlResult.change?.forest_drop || 0).toFixed(4)}%</div>
                <div className="pt-2 border-t border-emerald-300 mt-2">
                  <div className="text-emerald-700">Files Used:</div>
                  <div>Before: {testMlResult.files_used?.before}</div>
                  <div>After: {testMlResult.files_used?.after}</div>
                </div>
                <div className="pt-2 mt-2 text-emerald-700 font-medium">
                  🎯 The ML model is working correctly!
                </div>
              </div>
            </div>
          )}
          {testMlError && <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-xs">{testMlError}</div>}
          
          {seasonalWarning && (
            <div className="mt-2 p-2 rounded bg-amber-50 border border-amber-300">
              <p className="text-xs text-amber-800">
                <strong>⚠️ Seasonal Warning:</strong> {seasonalWarning}
              </p>
            </div>
          )}
          {mlAutoResult && (
            <div className="mt-3 p-3 rounded-lg border bg-gray-50">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="font-medium text-gray-900">Result</div>
                <div className={`text-sm font-semibold ${mlAutoResult?.deforestation_detected ? 'text-red-700' : 'text-emerald-700'}`}>
                  {mlAutoResult?.deforestation_detected ? '⚠️ Deforestation detected' : '✅ No deforestation detected'}
                </div>
              </div>
              
              {/* Vegetation Trend Indicator */}
              {mlAutoResult?.change?.vegetation_trend && (
                <div className={`mt-2 p-2 rounded text-xs font-medium ${
                  mlAutoResult.change.vegetation_trend === 'growth' 
                    ? 'bg-green-100 text-green-800 border border-green-300' 
                    : mlAutoResult.change.vegetation_trend === 'decline'
                    ? 'bg-red-100 text-red-800 border border-red-300'
                    : 'bg-gray-100 text-gray-800 border border-gray-300'
                }`}>
                  🌿 Vegetation Trend: <strong>{mlAutoResult.change.vegetation_trend.toUpperCase()}</strong>
                  {mlAutoResult.change.interpretation && (
                    <div className="mt-1 text-xs opacity-90">{mlAutoResult.change.interpretation}</div>
                  )}
                </div>
              )}
              
              <div className="mt-2 text-xs text-gray-700 grid grid-cols-1 md:grid-cols-2 gap-2">
                <div className="font-medium text-gray-900">
                  Forest Cover Before: {mlAutoResult?.before?.forest_cover_percent?.toFixed?.(2) ?? (mlAutoResult?.before?.forest_probability * 100)?.toFixed?.(2) ?? 'N/A'}%
                </div>
                <div className="font-medium text-gray-900">
                  Forest Cover After: {mlAutoResult?.after?.forest_cover_percent?.toFixed?.(2) ?? (mlAutoResult?.after?.forest_probability * 100)?.toFixed?.(2) ?? 'N/A'}%
                </div>
                <div className={mlAutoResult?.change?.forest_drop_percent > 0 ? 'text-red-700 font-semibold' : 'text-emerald-700'}>
                  Forest Loss: {mlAutoResult?.change?.forest_drop_percent?.toFixed?.(2) ?? (mlAutoResult?.change?.forest_drop * 100)?.toFixed?.(4) ?? 'N/A'}%
                </div>
                <div className={mlAutoResult?.change?.forest_loss_percent > 5 ? 'text-red-700 font-semibold' : 'text-gray-700'}>
                  Relative Forest Loss: {mlAutoResult?.change?.forest_loss_percent?.toFixed?.(2) ?? 'N/A'}% of original
                </div>
                <div>NDVI change: {mlAutoResult?.change?.ndvi_drop !== undefined 
                  ? (mlAutoResult.change.ndvi_drop > 0 
                      ? `↓ ${mlAutoResult.change.ndvi_drop.toFixed(3)}` 
                      : `↑ ${Math.abs(mlAutoResult.change.ndvi_drop).toFixed(3)}`)
                  : 'N/A'}</div>
                <div>Greenness change: {mlAutoResult?.change?.greenness_increase !== undefined 
                  ? (mlAutoResult.change.greenness_increase > 0 
                      ? `↑ ${mlAutoResult.change.greenness_increase.toFixed(3)}` 
                      : `↓ ${Math.abs(mlAutoResult.change.greenness_increase).toFixed(3)}`)
                  : 'N/A'}</div>
              </div>

              {detectionMapUrl && (
                <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded flex items-center justify-between">
                  <span className="text-xs text-blue-800">
                    📍 Detection marked on map
                  </span>
                  <button
                    onClick={() => {
                      setDetectionMapUrl(null);
                      setMapKey(prev => prev + 1);
                    }}
                    className="text-xs px-2 py-1 bg-white border border-blue-300 rounded hover:bg-blue-50 transition-colors"
                  >
                    Clear marker
                  </button>
                </div>
              )}
              
              {mlAutoResult?.exports && (
                <div className="mt-3">
                  <button
                    onClick={() => setShowBeforeAfterImages(!showBeforeAfterImages)}
                    className="text-sm text-blue-600 hover:text-blue-800 underline"
                  >
                    {showBeforeAfterImages ? '▼ Hide' : '▶ View'} Before/After Satellite Images
                  </button>
                  
                  {showBeforeAfterImages && (
                    <div className="mt-3 space-y-3">
                      <div className="flex gap-2 items-center justify-between flex-wrap">
                        <div className="flex gap-2 items-center">
                          <label htmlFor="image-viz" className="text-xs font-medium text-gray-700">Visualization:</label>
                          <select
                            id="image-viz"
                            value={imageVisualization}
                            onChange={(e) => setImageVisualization(e.target.value as 'rgb' | 'nir' | 'ndvi')}
                            className="text-xs px-2 py-1 border border-gray-300 rounded"
                          >
                            <option value="rgb">True Color (RGB)</option>
                            <option value="nir">False Color (NIR)</option>
                            <option value="ndvi">NDVI (Vegetation)</option>
                          </select>
                        </div>
                        
                        {mlAutoResult?.deforestation_detected && (
                          <label className="flex items-center gap-2 text-xs cursor-pointer">
                            <input
                              type="checkbox"
                              checked={showDetectionOverlay}
                              onChange={(e) => setShowDetectionOverlay(e.target.checked)}
                              className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                            />
                            <span className="font-medium text-gray-700">Show deforestation markers</span>
                          </label>
                        )}
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                          <div className="text-xs font-semibold text-gray-700 mb-1">Before ({mlAutoResult.before.date})</div>
                          <div 
                            className="relative group cursor-zoom-in"
                            onClick={() => {
                              console.log('🔍 Before image clicked!');
                              setZoomedImage(apiUrl(`/api/ml/preview-geotiff/${mlAutoResult.exports.before.path.split(/[/\\]/).pop()}?band_combo=${imageVisualization}`));
                              setImageZoom(1);
                              setZoomedImageContext({ isAfterImage: false, hasDetection: false });
                            }}
                          >
                            <img
                              src={apiUrl(`/api/ml/preview-geotiff/${mlAutoResult.exports.before.path.split(/[/\\]/).pop()}?band_combo=${imageVisualization}`)}
                              alt="Before image"
                              className="w-full h-auto border border-gray-300 rounded pointer-events-none"
                              onLoad={() => console.log('✅ Main ML before image loaded')}
                              onError={(e) => {
                                console.error('❌ Main ML before image failed:', apiUrl(`/api/ml/preview-geotiff/${mlAutoResult.exports.before.path.split(/[/\\]/).pop()}?band_combo=${imageVisualization}`));
                                e.currentTarget.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23ddd" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" fill="%23666" font-size="14"%3EImage unavailable%3C/text%3E%3C/svg%3E';
                              }}
                            />
                            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100 rounded pointer-events-none">
                              <span className="text-white text-sm bg-black bg-opacity-50 px-3 py-1 rounded">🔍 Click to zoom</span>
                            </div>
                          </div>
                        </div>
                        <div>
                          <div className="text-xs font-semibold text-gray-700 mb-1">After ({mlAutoResult.after.date})</div>
                          <div 
                            className="relative group cursor-zoom-in"
                            onClick={() => {
                              console.log('🔍 After image clicked!');
                              setZoomedImage(apiUrl(`/api/ml/preview-geotiff/${mlAutoResult.exports.after.path.split(/[/\\]/).pop()}?band_combo=${imageVisualization}`));
                              setImageZoom(1);
                              setZoomedImageContext({
                                isAfterImage: true,
                                hasDetection: mlAutoResult?.deforestation_detected || false,
                                deforestationPercent: mlAutoResult?.after?.forest_probability ? (1 - mlAutoResult.after.forest_probability) * 100 : undefined,
                                forestLoss: mlAutoResult?.change?.forest_drop ? mlAutoResult.change.forest_drop * 100 : undefined
                              });
                            }}
                          >
                            <img
                              src={apiUrl(`/api/ml/preview-geotiff/${mlAutoResult.exports.after.path.split(/[/\\]/).pop()}?band_combo=${imageVisualization}`)}
                              alt="After image"
                              className="w-full h-auto border border-gray-300 rounded pointer-events-none"
                              onLoad={() => console.log('✅ Main ML after image loaded')}
                              onError={(e) => {
                                console.error('❌ Main ML after image failed:', apiUrl(`/api/ml/preview-geotiff/${mlAutoResult.exports.after.path.split(/[/\\]/).pop()}?band_combo=${imageVisualization}`));
                                e.currentTarget.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23ddd" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" fill="%23666" font-size="14"%3EImage unavailable%3C/text%3E%3C/svg%3E';
                              }}
                            />
                            
                            {/* Deforestation Detection Overlay */}
                            {showDetectionOverlay && mlAutoResult?.deforestation_detected && (
                              <div className="absolute inset-0 pointer-events-none">
                                {/* Central detection indicator */}
                                <div className="absolute inset-0 flex items-center justify-center">
                                  <div className="relative">
                                    {/* Pulsing circle animation */}
                                    <div className="absolute inset-0 bg-red-500 rounded-full opacity-20 animate-ping" style={{ width: '80px', height: '80px', marginLeft: '-40px', marginTop: '-40px' }}></div>
                                    {/* Static detection marker */}
                                    <div className="relative bg-red-600 bg-opacity-30 border-4 border-red-600 rounded-full" style={{ width: '80px', height: '80px', marginLeft: '-40px', marginTop: '-40px' }}>
                                      <div className="absolute inset-0 flex items-center justify-center">
                                        <div className="bg-red-600 text-white rounded-full w-12 h-12 flex items-center justify-center text-lg font-bold shadow-lg">
                                          ⚠️
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                                
                                {/* Corner labels with confidence */}
                                <div className="absolute top-2 right-2 bg-red-600 text-white text-xs px-2 py-1 rounded-md shadow-lg font-semibold">
                                  Deforestation: {((1 - mlAutoResult.after.forest_probability) * 100).toFixed(0)}%
                                </div>
                                
                                {/* Forest drop indicator */}
                                {mlAutoResult?.change?.forest_drop !== undefined && (
                                  <div className="absolute bottom-2 left-2 bg-orange-600 text-white text-xs px-2 py-1 rounded-md shadow-lg font-semibold">
                                    Forest Loss: {(mlAutoResult.change.forest_drop * 100).toFixed(1)}%
                                  </div>
                                )}
                              </div>
                            )}
                            
                            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100 rounded pointer-events-none">
                              <span className="text-white text-sm bg-black bg-opacity-50 px-3 py-1 rounded">🔍 Click to zoom</span>
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      <div className="text-xs text-gray-500 italic">
                        💡 RGB shows true color, NIR highlights vegetation in red, NDVI shows vegetation health in green
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
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
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            {useInteractiveMap ? 'Interactive Map - Draw Areas to Monitor' : 'Deforestation Map with NDVI Layers'}
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setUseInteractiveMap(!useInteractiveMap)}
              className={`px-4 py-2 text-sm rounded-lg transition-colors flex items-center gap-2 ${
                useInteractiveMap 
                  ? 'bg-indigo-600 text-white hover:bg-indigo-700' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Pencil className="h-4 w-4" />
              {useInteractiveMap ? 'Drawing Mode Active' : 'Enable Area Drawing'}
            </button>
            {!useInteractiveMap && mapError && (
              <button
                onClick={() => { setMapError(false); setMapKey(prev => prev + 1); }}
                className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Try API Map
              </button>
            )}
            {!useInteractiveMap && !mapError && (
              <button
                onClick={() => { setMapError(true); setMapKey(prev => prev + 1); }}
                className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Use Static Map
              </button>
            )}
          </div>
        </div>
        
        {useInteractiveMap ? (
          <div className="p-4">
            <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">📍 How to Mark Areas for Monitoring:</h3>
              <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                <li>Click the polygon/rectangle tool in the top-right corner of the map</li>
                <li>Click on the map to draw your monitoring area</li>
                <li>Complete the shape by clicking the first point again (for polygon)</li>
                <li>Give your area a name and save it</li>
                <li>Run ML detection on the saved area to monitor deforestation</li>
              </ol>
            </div>

            <InteractiveMap
              center={selectedLocation ? [selectedLocation.latitude, selectedLocation.longitude] : undefined}
              onAreaDrawn={handleAreaDrawn}
              existingAreas={monitoredAreas}
              onAreaClick={handleAreaClick}
              drawingEnabled={true}
            />

            {/* Deforestation Alerts */}
            {monitoredAreas.filter(a => a.detection_count > 0 && a.alert_enabled !== false).length > 0 && (
              <div className="mt-6 bg-red-50 border-2 border-red-300 rounded-lg p-4">
                <h3 className="font-semibold text-red-900 mb-3 flex items-center gap-2">
                  <span className="text-xl">🚨</span>
                  Deforestation Alerts ({monitoredAreas.filter(a => a.detection_count > 0).length})
                </h3>
                <div className="space-y-2">
                  {monitoredAreas
                    .filter(a => a.detection_count > 0 && a.alert_enabled !== false)
                    .map(area => (
                      <div
                        key={area.id}
                        className="bg-white border-l-4 border-red-600 p-3 rounded cursor-pointer hover:shadow-md transition-all"
                        onClick={() => handleAreaClick(area.id)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="font-semibold text-red-900">{area.name}</div>
                            <div className="text-sm text-red-700 mt-1">
                              ⚠️ {area.detection_count} deforestation event{area.detection_count > 1 ? 's' : ''} detected
                            </div>
                            {area.last_monitored && (
                              <div className="text-xs text-gray-600 mt-1">
                                Last detected: {new Date(area.last_monitored).toLocaleString()}
                              </div>
                            )}
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              // Dismiss alert by updating area
                              const updateAlert = async () => {
                                await apiFetch(`/api/monitored-areas/${area.id}`, {
                                  method: 'PATCH',
                                  headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({ alert_enabled: false })
                                });
                                fetchMonitoredAreas();
                              };
                              updateAlert();
                            }}
                            className="text-xs text-gray-500 hover:text-gray-700 px-2"
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    ))}
                </div>
                <div className="mt-3 text-xs text-red-700 italic">
                  💡 Click on an alert to view detailed detection results
                </div>
              </div>
            )}

            {/* Monitored Areas List */}
            {monitoredAreas.length > 0 && (
              <div className="mt-6 bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-3">📋 Your Monitored Areas ({monitoredAreas.length})</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {monitoredAreas.map(area => (
                    <div
                      key={area.id}
                      className={`bg-white border rounded-lg p-3 transition-all cursor-pointer ${
                        selectedMonitoredArea?.id === area.id 
                          ? 'ring-2 ring-indigo-500 shadow-md' 
                          : 'hover:shadow-md'
                      }`}
                      onClick={() => handleAreaClick(area.id)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <h4 className="font-semibold text-gray-900">{area.name}</h4>
                          {area.description && (
                            <p className="text-xs text-gray-600 mt-1">{area.description}</p>
                          )}
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteMonitoredArea(area.id);
                          }}
                          className="text-red-600 hover:text-red-800 p-1"
                          title="Delete area"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                      
                      <div className="text-xs text-gray-500 space-y-1">
                        <div>Created: {new Date(area.created_at).toLocaleDateString()}</div>
                        {area.last_monitored && (
                          <div>Last checked: {new Date(area.last_monitored).toLocaleString()}</div>
                        )}
                        {area.detection_count > 0 && (
                          <div className="text-red-600 font-semibold">
                            ⚠️ {area.detection_count} detections
                          </div>
                        )}
                        {area.continuous_monitoring && (
                          <div className="text-green-600 font-semibold flex items-center gap-1">
                            <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                            Continuous monitoring active
                          </div>
                        )}
                        {areaDates[area.id] && (
                          <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-xs">
                            <div className="font-semibold text-blue-900 mb-1">📅 Selected Dates:</div>
                            <div className="text-blue-800">
                              Before: <strong>{areaDates[area.id]?.before || 'Not set'}</strong>
                            </div>
                            <div className="text-blue-800">
                              After: <strong>{areaDates[area.id]?.after || 'Not set'}</strong>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Date Range Selection */}
                      {showDatePicker === area.id && (
                        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded space-y-2" onClick={(e) => e.stopPropagation()}>
                          <div className="text-xs font-semibold text-blue-900 mb-2">Select Date Range:</div>
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="text-xs text-gray-600">Before:</label>
                              <input
                                type="date"
                                value={areaDates[area.id]?.before || ''}
                                max="2025-12-31"
                                onChange={(e) => {
                                  const newValue = e.target.value;
                                  console.log('Before date changed:', newValue);
                                  setAreaDates(prev => ({
                                    ...prev,
                                    [area.id]: {
                                      before: newValue,
                                      after: prev[area.id]?.after || ''
                                    }
                                  }));
                                }}
                                placeholder="Select before date"
                                className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                              />
                            </div>
                            <div>
                              <label className="text-xs text-gray-600">After:</label>
                              <input
                                type="date"
                                value={areaDates[area.id]?.after || ''}
                                max="2025-12-31"
                                onChange={(e) => {
                                  const newValue = e.target.value;
                                  console.log('After date changed:', newValue);
                                  setAreaDates(prev => ({
                                    ...prev,
                                    [area.id]: {
                                      before: prev[area.id]?.before || '',
                                      after: newValue
                                    }
                                  }));
                                }}
                                placeholder="Select after date"
                                className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                              />
                            </div>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setShowDatePicker(null);
                            }}
                            className="text-xs text-blue-600 hover:text-blue-800 underline"
                          >
                            Close
                          </button>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="mt-2 space-y-2">
                        {/* Show selected dates prominently */}
                        {areaDates[area.id]?.before && areaDates[area.id]?.after && (
                          <div className="px-3 py-2 bg-green-50 border border-green-200 rounded text-xs">
                            <div className="font-semibold text-green-800 mb-1">✓ Dates Selected:</div>
                            <div className="text-green-700">
                              Before: <strong>{areaDates[area.id].before}</strong><br/>
                              After: <strong>{areaDates[area.id].after}</strong>
                            </div>
                          </div>
                        )}
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (showDatePicker === area.id) {
                              setShowDatePicker(null);
                            } else {
                              setShowDatePicker(area.id);
                              // NO default dates - user must select manually
                            }
                          }}
                          className="w-full px-3 py-1.5 text-xs bg-blue-50 text-blue-700 rounded hover:bg-blue-100 transition-colors flex items-center justify-center gap-2"
                        >
                          <Calendar className="h-3 w-3" />
                          {showDatePicker === area.id ? 'Hide Dates' : 'Select Date Range'}
                        </button>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            console.log('RUN DETECTION CLICKED - Area ID:', area.id);
                            console.log('Current dates for this area:', areaDates[area.id]);
                            runDetectionOnArea(area.id);
                          }}
                          disabled={areaDetectionRunning || !areaDates[area.id]?.before || !areaDates[area.id]?.after}
                          className={`w-full px-3 py-2 text-sm rounded transition-colors flex items-center justify-center gap-2 ${
                            areaDetectionRunning 
                              ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                              : (!areaDates[area.id]?.before || !areaDates[area.id]?.after)
                              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                              : 'bg-emerald-600 text-white hover:bg-emerald-700'
                          }`}
                          title={(!areaDates[area.id]?.before || !areaDates[area.id]?.after) ? 'Please select date range first' : `Run detection: ${areaDates[area.id]?.before} to ${areaDates[area.id]?.after}`}
                        >
                          {areaDetectionRunning ? (
                            <>
                              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Running...
                            </>
                          ) : (
                            <>
                              <Play className="h-4 w-4" />
                              {areaDates[area.id]?.before && areaDates[area.id]?.after 
                                ? 'Run Detection Now' 
                                : 'Select Dates First'}
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Error Display Section */}
            {areaError && (
              <div className="mt-6 bg-red-50 border-2 border-red-300 rounded-lg p-4 shadow-md">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-bold text-red-900 mb-2 flex items-center gap-2">
                      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
                      </svg>
                      Detection Error
                    </h3>
                    <p className="text-red-800 text-sm whitespace-pre-wrap">{areaError}</p>
                    <div className="mt-3 text-xs text-red-700 bg-red-100 p-2 rounded">
                      <strong>Troubleshooting Tips:</strong>
                      <ul className="list-disc ml-4 mt-1 space-y-1">
                        <li>Verify the date range - make sure "Before" date is earlier than "After" date</li>
                        <li>Check browser console (F12) for detailed error messages</li>
                        <li>Check if there's sufficient satellite imagery for the selected dates and area</li>
                        <li>Cloud cover may be too high for the selected period (try adjusting dates)</li>
                        <li>Try selecting a different date range with less cloud coverage</li>
                      </ul>
                    </div>
                  </div>
                  <button
                    onClick={() => setAreaError(null)}
                    className="ml-4 text-red-600 hover:text-red-800 font-bold text-xl"
                    title="Dismiss error"
                  >
                    ×
                  </button>
                </div>
              </div>
            )}
            
            {/* Loading Indicator - More Prominent */}
            {areaDetectionRunning && (
              <div className="mt-6 bg-blue-50 border-2 border-blue-300 rounded-lg p-6 shadow-md">
                <div className="flex items-center justify-center gap-4">
                  <svg className="animate-spin h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <div>
                    <div className="text-lg font-semibold text-blue-900">Running Detection...</div>
                    <div className="text-sm text-blue-700">This may take 30-60 seconds. Please wait.</div>
                  </div>
                </div>
              </div>
            )}

            {/* Selected Area Detection Results */}
            {selectedMonitoredArea && areaDetectionResult && (
              <div className="mt-6 bg-white border rounded-lg p-4 shadow-md">
                <h3 className="font-semibold text-gray-900 mb-3">
                  📊 Detection Results: {selectedMonitoredArea.name}
                </h3>
                <div className={`p-4 rounded-lg ${
                  areaDetectionResult.deforestation_detected 
                    ? 'bg-red-50 border border-red-200' 
                    : 'bg-green-50 border border-green-200'
                }`}>
                  <div className={`text-lg font-semibold mb-2 ${areaDetectionResult.deforestation_detected ? 'text-red-700' : 'text-green-700'}`}>
                    {areaDetectionResult.deforestation_detected ? '⚠️ Deforestation Detected' : '✅ No Deforestation Detected'}
                  </div>
                  
                  {areaDetectionResult.change?.vegetation_trend && (
                    <div className={`mb-3 p-2 rounded text-xs font-medium ${
                      areaDetectionResult.change.vegetation_trend === 'growth' 
                        ? 'bg-green-100 text-green-800' 
                        : areaDetectionResult.change.vegetation_trend === 'decline'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      🌿 Vegetation Trend: <strong>{areaDetectionResult.change.vegetation_trend.toUpperCase()}</strong>
                      {areaDetectionResult.change.interpretation && (
                        <div className="mt-1 opacity-90">{areaDetectionResult.change.interpretation}</div>
                      )}
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="font-medium text-gray-700">Forest Cover Before:</div>
                      <div className="text-lg">{(areaDetectionResult.before?.forest_cover_percent || 0).toFixed(2)}%</div>
                    </div>
                    <div>
                      <div className="font-medium text-gray-700">Forest Cover After:</div>
                      <div className="text-lg">{(areaDetectionResult.after?.forest_cover_percent || 0).toFixed(2)}%</div>
                    </div>
                    <div>
                      <div className="font-medium text-gray-700">Forest Loss:</div>
                      <div className="text-lg text-red-700 font-semibold">
                        {(areaDetectionResult.change?.forest_drop_percent || 0).toFixed(2)}%
                      </div>
                    </div>
                    <div>
                      <div className="font-medium text-gray-700">Relative Loss:</div>
                      <div className="text-lg text-red-700 font-semibold">
                        {(areaDetectionResult.change?.forest_loss_percent || 0).toFixed(2)}%
                      </div>
                    </div>
                  </div>
                </div>

                {/* Detection History */}
                {selectedMonitoredArea?.detection_history && selectedMonitoredArea.detection_history.length > 0 && (
                  <div className="mt-4 border-t pt-4">
                    <h4 className="font-semibold text-gray-900 mb-2">📜 Detection History</h4>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {selectedMonitoredArea.detection_history.slice().reverse().map((record: any, idx: number) => (
                        <div key={idx} className={`text-xs p-2 rounded ${
                          record.deforestation_detected ? 'bg-red-50 border border-red-200' : 'bg-gray-50'
                        }`}>
                          <div className="flex items-center justify-between">
                            <span className="font-medium">
                              {record.deforestation_detected ? '⚠️ Deforestation' : '✅ No Change'}
                            </span>
                            <span className="text-gray-600">
                              {new Date(record.timestamp).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="text-gray-600 mt-1">
                            {record.before_date} → {record.after_date}
                          </div>
                          {record.forest_loss_percent !== undefined && record.forest_loss_percent > 0 && (
                            <div className="text-red-700 font-semibold mt-1">
                              Loss: {record.forest_loss_percent.toFixed(2)}%
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <>
            {mapError && (
              <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mx-4 mt-4">
                <p className="text-sm text-yellow-700">
                  ℹ️ Showing static map. The API server may be offline. Start it with: <code>cd backend; python start_api.py</code>
                </p>
              </div>
            )}
            <iframe
          key={mapKey}
          src={backendMapUrl}
          title="Deforestation Map"
          className="w-full h-[600px] border-0"
          onError={() => setMapError(true)}
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
          </>
        )}
      </div>

      {/* Image Zoom Modal */}
      {zoomedImage && (
        <div 
          className="fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center"
          onClick={() => { setZoomedImage(null); setZoomedImageContext(null); }}
        >
          <div className="relative w-full h-full flex flex-col items-center justify-center p-8">
            {/* Close Button */}
            <button
              onClick={() => { setZoomedImage(null); setZoomedImageContext(null); }}
              className="absolute top-4 right-4 bg-white text-gray-800 rounded-full w-10 h-10 flex items-center justify-center hover:bg-gray-200 transition-colors z-10"
              title="Close (ESC)"
            >
              ✕
            </button>

            {/* Zoom Controls */}
            <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-white rounded-lg shadow-lg p-2 flex items-center space-x-2 z-10">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setImageZoom(Math.max(0.5, imageZoom - 0.25));
                }}
                className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                title="Zoom out"
              >
                −
              </button>
              <span className="text-sm font-medium px-2 min-w-[60px] text-center">
                {Math.round(imageZoom * 100)}%
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setImageZoom(Math.min(5, imageZoom + 0.25));
                }}
                className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                title="Zoom in"
              >
                +
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setImageZoom(1);
                }}
                className="px-3 py-1 bg-emerald-100 hover:bg-emerald-200 text-emerald-700 rounded transition-colors ml-2"
                title="Reset zoom"
              >
                Reset
              </button>
            </div>

            {/* Image Container with Pan Support */}
            <div 
              className="overflow-auto max-w-full max-h-full cursor-move relative"
              onClick={(e) => e.stopPropagation()}
              style={{
                maxWidth: '90vw',
                maxHeight: '80vh'
              }}
              onWheel={(e) => {
                e.stopPropagation();
                e.preventDefault();
                const delta = e.deltaY > 0 ? -0.1 : 0.1;
                setImageZoom(Math.max(0.5, Math.min(5, imageZoom + delta)));
              }}
            >
              <div className="relative inline-block">
                <img
                  src={zoomedImage}
                  alt="Zoomed satellite image"
                  className="transition-transform duration-100"
                  style={{
                    transform: `scale(${imageZoom})`,
                    transformOrigin: 'center center',
                    cursor: imageZoom > 1 ? 'grab' : 'zoom-in',
                    minWidth: '100%',
                    minHeight: '100%',
                    display: 'block',
                    imageRendering: '-webkit-optimize-contrast',
                    WebkitFontSmoothing: 'antialiased',
                    backfaceVisibility: 'hidden',
                    WebkitBackfaceVisibility: 'hidden',
                    MozBackfaceVisibility: 'hidden',
                    transformStyle: 'preserve-3d',
                    willChange: 'transform'
                  }}
                  draggable={false}
                  onDoubleClick={(e) => {
                    e.stopPropagation();
                    if (imageZoom === 1) {
                      setImageZoom(2);
                    } else {
                      setImageZoom(1);
                    }
                  }}
                />
                
                {/* Deforestation overlay on zoomed image */}
                {showDetectionOverlay && zoomedImageContext?.hasDetection && zoomedImageContext?.isAfterImage && (
                  <div 
                    className="absolute inset-0 pointer-events-none"
                    style={{
                      transform: `scale(${imageZoom})`,
                      transformOrigin: 'center center'
                    }}
                  >
                    {/* Central detection marker */}
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="relative">
                        <div className="absolute inset-0 bg-red-500 rounded-full opacity-20 animate-ping" style={{ width: '120px', height: '120px', marginLeft: '-60px', marginTop: '-60px' }}></div>
                        <div className="relative bg-red-600 bg-opacity-30 border-4 border-red-600 rounded-full" style={{ width: '120px', height: '120px', marginLeft: '-60px', marginTop: '-60px' }}>
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="bg-red-600 text-white rounded-full w-16 h-16 flex items-center justify-center text-2xl font-bold shadow-lg">
                              ⚠️
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Detection badges */}
                    {zoomedImageContext.deforestationPercent !== undefined && (
                      <div className="absolute top-4 right-4 bg-red-600 text-white text-sm px-3 py-2 rounded-md shadow-xl font-semibold">
                        Deforestation: {zoomedImageContext.deforestationPercent.toFixed(0)}%
                      </div>
                    )}
                    
                    {zoomedImageContext.forestLoss !== undefined && (
                      <div className="absolute bottom-4 left-4 bg-orange-600 text-white text-sm px-3 py-2 rounded-md shadow-xl font-semibold">
                        Forest Loss: {zoomedImageContext.forestLoss.toFixed(1)}%
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Instructions */}
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black bg-opacity-75 text-white text-xs px-4 py-2 rounded-lg max-w-xl text-center">
              🖱️ Scroll wheel or +/− buttons to zoom • ⌨️ Keyboard: +/− keys, 0 to reset • 🖱️ Double-click to toggle zoom • ✕ Click outside or ESC to close
            </div>
          </div>
        </div>
      )}

      {/* Save Monitored Area Dialog */}
      {showSaveAreaDialog && (
        <div 
          className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4"
          onClick={() => setShowSaveAreaDialog(false)}
        >
          <div 
            className="bg-white rounded-lg shadow-xl max-w-md w-full p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              💾 Save Monitored Area
            </h3>
            
            <div className="space-y-4">
              <div>
                <label htmlFor="area-name" className="block text-sm font-medium text-gray-700 mb-1">
                  Area Name *
                </label>
                <input
                  id="area-name"
                  type="text"
                  value={newAreaName}
                  onChange={(e) => setNewAreaName(e.target.value)}
                  placeholder="e.g., Chirinda Forest East"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label htmlFor="area-description" className="block text-sm font-medium text-gray-700 mb-1">
                  Description (optional)
                </label>
                <textarea
                  id="area-description"
                  value={newAreaDescription}
                  onChange={(e) => setNewAreaDescription(e.target.value)}
                  placeholder="Add notes about this area..."
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="text-xs text-gray-500">
                <strong>Coordinates:</strong> {drawnCoordinates?.length || 0} points drawn
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => {
                  setShowSaveAreaDialog(false);
                  setNewAreaName('');
                  setNewAreaDescription('');
                  setDrawnCoordinates(null);
                }}
                className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveMonitoredArea}
                disabled={!newAreaName.trim()}
                className={`px-4 py-2 text-sm rounded-md transition-colors ${
                  newAreaName.trim()
                    ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                Save Area
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MapViewPage;