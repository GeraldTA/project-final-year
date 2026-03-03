import React from 'react';
import { Clock, TrendingDown, TrendingUp, Minus, AlertCircle } from 'lucide-react';

interface DetectionRecord {
  timestamp: string;
  before_date: string;
  after_date: string;
  deforestation_detected: boolean;
  forest_loss_percent: number;
  vegetation_trend: string;
}

interface MonitoringTimelineProps {
  detectionHistory: DetectionRecord[];
  monitoringStartDate?: string;
  nextScheduledDetection?: string;
  activeMonitoring: boolean;
}

export const MonitoringTimeline: React.FC<MonitoringTimelineProps> = ({
  detectionHistory,
  monitoringStartDate,
  nextScheduledDetection,
  activeMonitoring
}) => {
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'growth':
        return <TrendingUp className="h-4 w-4 text-green-600" />;
      case 'decline':
        return <TrendingDown className="h-4 w-4 text-red-600" />;
      default:
        return <Minus className="h-4 w-4 text-gray-600" />;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDateShort = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="bg-white rounded-lg border shadow-sm p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <Clock className="h-5 w-5 text-blue-600" />
          Detection Timeline
        </h3>
        {activeMonitoring && (
          <div className="flex items-center gap-2 text-xs">
            <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
            <span className="text-green-700 font-medium">Active Monitoring</span>
          </div>
        )}
      </div>

      {/* Monitoring Info */}
      {monitoringStartDate && (
        <div className="bg-blue-50 rounded p-3 mb-4 text-sm">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-blue-600 mt-0.5" />
            <div className="flex-1">
              <div className="font-medium text-blue-900">
                Monitoring started: {formatDate(monitoringStartDate)}
              </div>
              {nextScheduledDetection && activeMonitoring && (
                <div className="text-blue-700 mt-1">
                  Next detection: {formatDate(nextScheduledDetection)}
                </div>
              )}
              <div className="text-blue-600 mt-1 text-xs">
                Automatic detection runs every 5 days (Sentinel-2 revisit time)
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {detectionHistory.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Clock className="h-12 w-12 mx-auto mb-2 opacity-20" />
            <div className="text-sm">No detection history yet</div>
            <div className="text-xs mt-1">Run a detection or start active monitoring</div>
          </div>
        ) : (
          detectionHistory.map((record, index) => (
            <div
              key={index}
              className={`relative pl-8 pb-4 ${
                index !== detectionHistory.length - 1 ? 'border-l-2 border-gray-200' : ''
              }`}
            >
              {/* Timeline dot */}
              <div className={`absolute left-0 top-0 w-4 h-4 rounded-full -ml-2 ${
                record.deforestation_detected
                  ? 'bg-red-500'
                  : record.vegetation_trend === 'growth'
                  ? 'bg-green-500'
                  : 'bg-gray-400'
              }`} />

              {/* Detection card */}
              <div className={`rounded-lg border p-3 ${
                record.deforestation_detected
                  ? 'bg-red-50 border-red-200'
                  : record.vegetation_trend === 'growth'
                  ? 'bg-green-50 border-green-200'
                  : 'bg-gray-50 border-gray-200'
              }`}>
                <div className="flex items-start justify-between mb-2">
                  <div className="text-xs font-medium text-gray-600">
                    {formatDate(record.timestamp)}
                  </div>
                  <div className="flex items-center gap-1">
                    {getTrendIcon(record.vegetation_trend)}
                    <span className={`text-xs font-semibold ${
                      record.deforestation_detected
                        ? 'text-red-700'
                        : record.vegetation_trend === 'growth'
                        ? 'text-green-700'
                        : 'text-gray-700'
                    }`}>
                      {record.vegetation_trend.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-600">Before:</span>
                    <span className="ml-1 font-medium">{formatDateShort(record.before_date)}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">After:</span>
                    <span className="ml-1 font-medium">{formatDateShort(record.after_date)}</span>
                  </div>
                </div>

                {record.deforestation_detected && (
                  <div className="mt-2 pt-2 border-t border-red-200">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-red-600" />
                      <span className="text-xs font-semibold text-red-900">
                        Deforestation Detected
                      </span>
                    </div>
                    <div className="text-xs text-red-700 mt-1">
                      Forest loss: {Math.abs(record.forest_loss_percent).toFixed(2)}%
                    </div>
                  </div>
                )}

                {!record.deforestation_detected && record.forest_loss_percent !== 0 && (
                  <div className="mt-2 text-xs text-gray-600">
                    Change: {record.forest_loss_percent > 0 ? '+' : ''}{record.forest_loss_percent.toFixed(2)}%
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
