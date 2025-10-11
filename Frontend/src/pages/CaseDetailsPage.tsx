import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  MapPin, 
  Calendar, 
  Activity, 
  Download, 
  ExternalLink, 
  CheckCircle,
  AlertTriangle,
  ZoomIn,
  Send,
  FileText
} from 'lucide-react';
import { useData } from '../context/DataContext';

const CaseDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { alerts, setAlerts } = useData();
  const [imageComparison, setImageComparison] = useState(50); // Slider position
  const [showLargeImage, setShowLargeImage] = useState(false);

  const alert = alerts.find(a => a.id === id);

  if (!alert) {
    return (
      <div className="text-center py-12">
        <div className="h-12 w-12 text-theme-text-secondary mx-auto mb-4 flex items-center justify-center">
          <span className="text-2xl">⚠️</span>
        </div>
        <h2 className="text-xl font-semibold text-theme-text-primary mb-2">Case Not Found</h2>
        <p className="text-theme-text-secondary mb-4">The requested case could not be found.</p>
        <Link
          to="/flagged-areas"
          className="inline-flex items-center space-x-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Flagged Areas</span>
        </Link>
      </div>
    );
  }

  const handleMarkResolved = () => {
    setAlerts(prev => prev.map(a => 
      a.id === alert.id ? { ...a, status: 'resolved' } : a
    ));
    navigate('/flagged-areas');
  };

  const handleDownloadReport = () => {
    // Simulate PDF generation
    const reportData = {
      caseId: alert.id,
      type: alert.type,
      location: alert.location,
      area: alert.area,
      confidence: alert.confidence,
      detectedAt: alert.detectedAt,
      description: alert.description
    };
    
    console.log('Generating PDF report...', reportData);
    alert('PDF report generation started. Check downloads folder.');
  };

  const handleNotifyAuthorities = () => {
    // Simulate notification
    const message = `URGENT: ${alert.type} activity detected at ${alert.location.address}. Area affected: ${alert.area} hectares. Confidence: ${alert.confidence}%. GPS: ${alert.location.lat}, ${alert.location.lng}`;
    console.log('Sending notification...', message);
    alert('Authorities have been notified via SMS and email.');
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-100 border-red-200';
      case 'high': return 'text-orange-600 bg-orange-100 border-orange-200';
      case 'medium': return 'text-yellow-600 bg-yellow-100 border-yellow-200';
      default: return 'text-blue-600 bg-blue-100 border-blue-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            to="/flagged-areas"
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Flagged Areas</span>
          </Link>
          <div className="h-6 border-l border-gray-300"></div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Case Details</h1>
            <p className="text-gray-600">ID: {alert.id}</p>
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-medium border ${getSeverityColor(alert.severity)}`}>
          {alert.severity.toUpperCase()} PRIORITY
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Before/After Comparison */}
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            <div className="bg-gray-50 border-b border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">Satellite Evidence</h2>
                <button
                  onClick={() => setShowLargeImage(true)}
                  className="flex items-center space-x-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors text-sm"
                >
                  <ZoomIn className="h-4 w-4" />
                  <span>View Larger</span>
                </button>
              </div>
            </div>
            
            <div className="p-6">
              {/* Image Comparison Container */}
              <div className="relative bg-gray-100 rounded-lg overflow-hidden h-80 mb-4">
                {/* Before Image */}
                <div 
                  className="absolute inset-0 bg-gradient-to-br from-green-600 to-green-800"
                  style={{
                    clipPath: `polygon(0 0, ${imageComparison}% 0, ${imageComparison}% 100%, 0 100%)`,
                    backgroundImage: `url("data:image/svg+xml,%3Csvg width='20' height='20' viewBox='0 0 20 20' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='0.1'%3E%3Ccircle cx='3' cy='3' r='3'/%3E%3C/g%3E%3C/svg%3E")`
                  }}
                >
                  <div className="absolute top-4 left-4 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded">
                    BEFORE
                  </div>
                </div>

                {/* After Image */}
                <div 
                  className="absolute inset-0 bg-gradient-to-br from-brown-600 to-red-700"
                  style={{
                    clipPath: `polygon(${imageComparison}% 0, 100% 0, 100% 100%, ${imageComparison}% 100%)`,
                    backgroundImage: `url("data:image/svg+xml,%3Csvg width='20' height='20' viewBox='0 0 20 20' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23000000' fill-opacity='0.2'%3E%3Crect x='0' y='0' width='10' height='10'/%3E%3C/g%3E%3C/svg%3E")`
                  }}
                >
                  <div className="absolute top-4 right-4 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded">
                    AFTER
                  </div>
                </div>

                {/* Slider */}
                <div 
                  className="absolute top-0 bottom-0 w-1 bg-white shadow-lg cursor-ew-resize z-10"
                  style={{ left: `${imageComparison}%` }}
                >
                  <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-6 h-6 bg-white rounded-full shadow-lg border-2 border-gray-300 flex items-center justify-center">
                    <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                  </div>
                </div>

                {/* Slider Input */}
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={imageComparison}
                  onChange={(e) => setImageComparison(Number(e.target.value))}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-20"
                />
              </div>

              {/* Image Metadata */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="bg-green-50 p-3 rounded-lg">
                  <h4 className="font-medium text-green-800 mb-1">Before Image</h4>
                  <p className="text-green-700">Sentinel-2 • {new Date(alert.detectedAt.getTime() - 30 * 24 * 60 * 60 * 1000).toLocaleDateString()}</p>
                  <p className="text-green-600 text-xs">10m resolution • Cloud cover: 2%</p>
                </div>
                <div className="bg-red-50 p-3 rounded-lg">
                  <h4 className="font-medium text-red-800 mb-1">After Image</h4>
                  <p className="text-red-700">Sentinel-2 • {new Date(alert.detectedAt).toLocaleDateString()}</p>
                  <p className="text-red-600 text-xs">10m resolution • Cloud cover: 5%</p>
                </div>
              </div>
            </div>
          </div>

          {/* Analysis Details */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Detection Analysis</h2>
            <div className="space-y-4">
              <div>
                <h3 className="font-medium text-gray-900 mb-2">Change Detection Results</h3>
                <p className="text-gray-700 text-sm leading-relaxed">{alert.description}</p>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-lg font-bold text-gray-900">{alert.confidence}%</div>
                  <div className="text-xs text-gray-600">AI Confidence</div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-lg font-bold text-gray-900">-{Math.floor(Math.random() * 30 + 40)}%</div>
                  <div className="text-xs text-gray-600">NDVI Change</div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-lg font-bold text-gray-900">{Math.floor(Math.random() * 20 + 80)}%</div>
                  <div className="text-xs text-gray-600">Bare Soil Index</div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-lg font-bold text-gray-900">{Math.floor(Math.random() * 15 + 5)}</div>
                  <div className="text-xs text-gray-600">Days Since Detection</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Case Information */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Case Information</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-600">Activity Type</label>
                <p className="text-gray-900 capitalize">{alert.type}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium text-gray-600">Location</label>
                <div className="flex items-start space-x-2 mt-1">
                  <MapPin className="h-4 w-4 text-gray-400 mt-0.5" />
                  <div>
                    <p className="text-gray-900">{alert.location.address}</p>
                    <p className="text-sm text-gray-500">
                      {alert.location.lat.toFixed(6)}, {alert.location.lng.toFixed(6)}
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-600">Detection Date</label>
                <div className="flex items-center space-x-2 mt-1">
                  <Calendar className="h-4 w-4 text-gray-400" />
                  <p className="text-gray-900">{new Date(alert.detectedAt).toLocaleString()}</p>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-600">Area Affected</label>
                <p className="text-gray-900">{alert.area} hectares</p>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-600">Confidence Level</label>
                <div className="flex items-center space-x-2 mt-1">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-emerald-500 h-2 rounded-full transition-all"
                      style={{ width: `${alert.confidence}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-medium text-gray-900">{alert.confidence}%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Actions</h2>
            <div className="space-y-3">
              <button
                onClick={() => setShowLargeImage(true)}
                className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
              >
                <ZoomIn className="h-4 w-4" />
                <span>View Larger Image</span>
              </button>

              <button
                onClick={handleDownloadReport}
                className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-emerald-50 text-emerald-700 rounded-lg hover:bg-emerald-100 transition-colors"
              >
                <Download className="h-4 w-4" />
                <span>Download Report (PDF)</span>
              </button>

              <button
                onClick={handleNotifyAuthorities}
                className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors"
              >
                <Send className="h-4 w-4" />
                <span>Notify Authorities</span>
              </button>

              <Link
                to="/map"
                className="w-full flex items-center justify-center space-x-2 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <ExternalLink className="h-4 w-4" />
                <span>View on Map</span>
              </Link>

              {alert.status === 'active' && (
                <button
                  onClick={handleMarkResolved}
                  className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors"
                >
                  <CheckCircle className="h-4 w-4" />
                  <span>Mark as Resolved</span>
                </button>
              )}
            </div>
          </div>

          {/* Case Timeline */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Case Timeline</h2>
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <div className="w-2 h-2 bg-emerald-500 rounded-full mt-2"></div>
                <div>
                  <p className="text-sm font-medium text-gray-900">Case Created</p>
                  <p className="text-xs text-gray-500">{new Date(alert.detectedAt).toLocaleString()}</p>
                </div>
              </div>
              
              {alert.status === 'investigating' && (
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-yellow-500 rounded-full mt-2"></div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">Investigation Started</p>
                    <p className="text-xs text-gray-500">
                      {new Date(alert.detectedAt.getTime() + 2 * 60 * 60 * 1000).toLocaleString()}
                    </p>
                  </div>
                </div>
              )}

              {alert.status === 'resolved' && (
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">Case Resolved</p>
                    <p className="text-xs text-gray-500">
                      {new Date(alert.detectedAt.getTime() + 24 * 60 * 60 * 1000).toLocaleString()}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Technical Details */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Technical Details</h2>
          <div className="space-y-4 text-sm">
            <div>
              <label className="font-medium text-gray-600">Satellite Data</label>
              <p className="text-gray-900">Sentinel-2 MSI</p>
              <p className="text-xs text-gray-500">10m spatial resolution</p>
            </div>

            <div>
              <label className="font-medium text-gray-600">Processing Date</label>
              <p className="text-gray-900">{new Date(alert.detectedAt).toLocaleDateString()}</p>
            </div>

            <div>
              <label className="font-medium text-gray-600">Algorithm</label>
              <p className="text-gray-900">CNN + NDVI Analysis</p>
              <p className="text-xs text-gray-500">ResNet-50 backbone</p>
            </div>

            <div>
              <label className="font-medium text-gray-600">Validation</label>
              <p className="text-gray-900">Automated + Manual Review</p>
            </div>

            <div>
              <label className="font-medium text-gray-600">Data Sources</label>
              <div className="space-y-1">
                <p className="text-gray-900">• ESA Copernicus Hub</p>
                <p className="text-gray-900">• Global Forest Watch</p>
                <p className="text-gray-900">• OpenStreetMap</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Large Image Modal */}
      {showLargeImage && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
            <div className="bg-gray-50 border-b border-gray-200 p-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Satellite Evidence - Large View</h3>
              <button
                onClick={() => setShowLargeImage(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            <div className="p-6">
              <div className="relative bg-gray-100 rounded-lg overflow-hidden h-96">
                {/* Same comparison slider but larger */}
                <div 
                  className="absolute inset-0 bg-gradient-to-br from-green-600 to-green-800"
                  style={{
                    clipPath: `polygon(0 0, ${imageComparison}% 0, ${imageComparison}% 100%, 0 100%)`,
                    backgroundImage: `url("data:image/svg+xml,%3Csvg width='20' height='20' viewBox='0 0 20 20' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='0.1'%3E%3Ccircle cx='3' cy='3' r='3'/%3E%3C/g%3E%3C/svg%3E")`
                  }}
                >
                  <div className="absolute top-4 left-4 bg-black bg-opacity-75 text-white text-sm px-3 py-2 rounded">
                    BEFORE - {new Date(alert.detectedAt.getTime() - 30 * 24 * 60 * 60 * 1000).toLocaleDateString()}
                  </div>
                </div>

                <div 
                  className="absolute inset-0 bg-gradient-to-br from-brown-600 to-red-700"
                  style={{
                    clipPath: `polygon(${imageComparison}% 0, 100% 0, 100% 100%, ${imageComparison}% 100%)`,
                    backgroundImage: `url("data:image/svg+xml,%3Csvg width='20' height='20' viewBox='0 0 20 20' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23000000' fill-opacity='0.2'%3E%3Crect x='0' y='0' width='10' height='10'/%3E%3C/g%3E%3C/svg%3E")`
                  }}
                >
                  <div className="absolute top-4 right-4 bg-black bg-opacity-75 text-white text-sm px-3 py-2 rounded">
                    AFTER - {new Date(alert.detectedAt).toLocaleDateString()}
                  </div>
                </div>

                <div 
                  className="absolute top-0 bottom-0 w-1 bg-white shadow-lg cursor-ew-resize z-10"
                  style={{ left: `${imageComparison}%` }}
                >
                  <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-white rounded-full shadow-lg border-2 border-gray-300 flex items-center justify-center">
                    <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
                  </div>
                </div>

                <input
                  type="range"
                  min="0"
                  max="100"
                  value={imageComparison}
                  onChange={(e) => setImageComparison(Number(e.target.value))}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-20"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CaseDetailsPage;