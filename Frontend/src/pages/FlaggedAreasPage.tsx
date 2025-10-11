import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, Download, Eye, MapPin, Calendar, CheckCircle } from 'lucide-react';
import { useData } from '../context/DataContext';
import { Alert } from '../types';

const FlaggedAreasPage: React.FC = () => {
  const { alerts, setAlerts } = useData();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'date' | 'severity' | 'area'>('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const filteredAndSortedAlerts = alerts
    .filter(alert => {
      const matchesSearch = alert.location.address.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           alert.description.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'all' || alert.status === statusFilter;
      const matchesSeverity = severityFilter === 'all' || alert.severity === severityFilter;
      return matchesSearch && matchesStatus && matchesSeverity;
    })
    .sort((a, b) => {
      let comparison = 0;
      if (sortBy === 'date') {
        comparison = new Date(a.detectedAt).getTime() - new Date(b.detectedAt).getTime();
      } else if (sortBy === 'severity') {
        const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
        comparison = severityOrder[a.severity] - severityOrder[b.severity];
      } else if (sortBy === 'area') {
        comparison = a.area - b.area;
      }
      return sortOrder === 'desc' ? -comparison : comparison;
    });

  const handleMarkResolved = (alertId: string) => {
    setAlerts(prev => prev.map(alert => 
      alert.id === alertId ? { ...alert, status: 'resolved' } : alert
    ));
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-100';
      case 'high': return 'text-orange-600 bg-orange-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      default: return 'text-blue-600 bg-blue-100';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-red-600 bg-red-100';
      case 'investigating': return 'text-yellow-600 bg-yellow-100';
      case 'resolved': return 'text-green-600 bg-green-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Flagged Areas</h1>
          <p className="text-gray-600">
            {filteredAndSortedAlerts.length} of {alerts.length} cases shown
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">
            <Download className="h-4 w-4" />
            <span>Export All</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg p-6 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search locations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-emerald-500"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
          </select>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-emerald-500"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          {/* Sort By */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-emerald-500"
          >
            <option value="date">Sort by Date</option>
            <option value="severity">Sort by Severity</option>
            <option value="area">Sort by Area</option>
          </select>

          {/* Sort Order */}
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as any)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-emerald-500"
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>
      </div>

      {/* Cases Table */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Case Details
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Location
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Impact
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredAndSortedAlerts.map((alert) => (
                <tr key={alert.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-3">
                      <div className={`w-3 h-3 rounded-full ${
                        alert.severity === 'critical' ? 'bg-red-500' :
                        alert.severity === 'high' ? 'bg-orange-500' :
                        alert.severity === 'medium' ? 'bg-yellow-500' :
                        'bg-blue-500'
                      }`}></div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {alert.type.charAt(0).toUpperCase() + alert.type.slice(1)}
                        </div>
                        <div className="text-sm text-gray-500">ID: {alert.id}</div>
                        <div className="flex items-center space-x-1 mt-1">
                          <Calendar className="h-3 w-3 text-gray-400" />
                          <span className="text-xs text-gray-500">
                            {new Date(alert.detectedAt).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-start space-x-2">
                      <MapPin className="h-4 w-4 text-gray-400 mt-0.5" />
                      <div>
                        <div className="text-sm text-gray-900">{alert.location.address}</div>
                        <div className="text-xs text-gray-500">
                          {alert.location.lat.toFixed(4)}, {alert.location.lng.toFixed(4)}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{alert.area} hectares</div>
                    <div className="text-xs text-gray-500">{alert.confidence}% confidence</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="space-y-1">
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getSeverityColor(alert.severity)}`}>
                        {alert.severity.toUpperCase()}
                      </span>
                      <div>
                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(alert.status)}`}>
                          {alert.status.charAt(0).toUpperCase() + alert.status.slice(1)}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                    <Link
                      to={`/case/${alert.id}`}
                      className="inline-flex items-center space-x-1 text-emerald-600 hover:text-emerald-700"
                    >
                      <Eye className="h-4 w-4" />
                      <span>View</span>
                    </Link>
                    {alert.status === 'active' && (
                      <button
                        onClick={() => handleMarkResolved(alert.id)}
                        className="inline-flex items-center space-x-1 text-green-600 hover:text-green-700 ml-3"
                      >
                        <CheckCircle className="h-4 w-4" />
                        <span>Resolve</span>
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredAndSortedAlerts.length === 0 && (
          <div className="text-center py-12">
            <div className="h-12 w-12 text-theme-text-secondary mx-auto mb-4 flex items-center justify-center">
              <span className="text-2xl">🔍</span>
            </div>
            <p className="text-theme-text-secondary">No flagged areas match your current filters</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default FlaggedAreasPage;