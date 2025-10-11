import React, { useState } from 'react';
import { Download, FileText, Calendar, Filter, BarChart3, TrendingUp } from 'lucide-react';
import { useData } from '../context/DataContext';

const ReportsPage: React.FC = () => {
  const { alerts, detectionData } = useData();
  const [reportType, setReportType] = useState<'summary' | 'detailed' | 'trends'>('summary');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [selectedRegions, setSelectedRegions] = useState<string[]>(['all']);
  const [format, setFormat] = useState<'pdf' | 'excel'>('pdf');

  const generateReport = () => {
    const reportData = {
      type: reportType,
      dateRange,
      regions: selectedRegions,
      format,
      alerts: alerts.length,
      timestamp: new Date().toISOString()
    };
    
    console.log('Generating report...', reportData);
    alert(`${format.toUpperCase()} report generation started. Check downloads folder.`);
  };

  const recentReports = [
    {
      id: 'report-1',
      name: 'Weekly Summary - Bulawayo Region',
      type: 'Summary Report',
      generatedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
      format: 'PDF',
      size: '2.4 MB'
    },
    {
      id: 'report-2',
      name: 'Detailed Analysis - All Regions',
      type: 'Detailed Report',
      generatedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
      format: 'Excel',
      size: '5.1 MB'
    },
    {
      id: 'report-3',
      name: 'Monthly Trends - Q4 2024',
      type: 'Trends Report',
      generatedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      format: 'PDF',
      size: '3.8 MB'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
        <p className="text-gray-600">Generate comprehensive reports for stakeholders and authorities</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report Generator */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">Generate New Report</h2>
            
            <div className="space-y-6">
              {/* Report Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">Report Type</label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {[
                    { value: 'summary', label: 'Summary Report', desc: 'High-level overview with key metrics', icon: BarChart3 },
                    { value: 'detailed', label: 'Detailed Analysis', desc: 'Complete case-by-case breakdown', icon: FileText },
                    { value: 'trends', label: 'Trends Analysis', desc: 'Historical patterns and predictions', icon: TrendingUp }
                  ].map((type) => (
                    <button
                      key={type.value}
                      onClick={() => setReportType(type.value as any)}
                      className={`p-4 border-2 rounded-lg text-left transition-colors ${
                        reportType === type.value
                          ? 'border-emerald-500 bg-emerald-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center space-x-2 mb-2">
                        <type.icon className={`h-5 w-5 ${
                          reportType === type.value ? 'text-emerald-600' : 'text-gray-400'
                        }`} />
                        <span className={`font-medium ${
                          reportType === type.value ? 'text-emerald-900' : 'text-gray-900'
                        }`}>
                          {type.label}
                        </span>
                      </div>
                      <p className="text-xs text-gray-600">{type.desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Date Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">Date Range</label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Start Date</label>
                    <input
                      type="date"
                      value={dateRange.start}
                      onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">End Date</label>
                    <input
                      type="date"
                      value={dateRange.end}
                      onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                </div>
              </div>

              {/* Regions */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">Regions</label>
                <div className="space-y-2">
                  {[
                    { value: 'all', label: 'All Regions' },
                    { value: 'bulawayo', label: 'Bulawayo, Zimbabwe' },
                    { value: 'amazon', label: 'Amazon Rainforest, Brazil' },
                    { value: 'congo', label: 'Congo Basin, DRC' },
                    { value: 'borneo', label: 'Borneo, Malaysia' }
                  ].map((region) => (
                    <label key={region.value} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={selectedRegions.includes(region.value)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedRegions(prev => [...prev, region.value]);
                          } else {
                            setSelectedRegions(prev => prev.filter(r => r !== region.value));
                          }
                        }}
                        className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                      />
                      <span className="text-sm text-gray-700">{region.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Format */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">Export Format</label>
                <div className="flex space-x-3">
                  <button
                    onClick={() => setFormat('pdf')}
                    className={`flex-1 p-3 border-2 rounded-lg transition-colors ${
                      format === 'pdf'
                        ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <FileText className="h-5 w-5 mx-auto mb-1" />
                    <div className="text-sm font-medium">PDF</div>
                  </button>
                  <button
                    onClick={() => setFormat('excel')}
                    className={`flex-1 p-3 border-2 rounded-lg transition-colors ${
                      format === 'excel'
                        ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <BarChart3 className="h-5 w-5 mx-auto mb-1" />
                    <div className="text-sm font-medium">Excel</div>
                  </button>
                </div>
              </div>

              {/* Generate Button */}
              <button
                onClick={generateReport}
                className="w-full flex items-center justify-center space-x-2 px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
              >
                <Download className="h-5 w-5" />
                <span>Generate Report</span>
              </button>
            </div>
          </div>
        </div>

        {/* Recent Reports */}
        <div className="space-y-6">
          <div className="bg-theme-card rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-theme-text-primary mb-4">Recent Reports</h2>
            <div className="space-y-3">
              {recentReports.map((report) => (
                <div key={report.id} className="border border-theme-border rounded-lg p-4 hover:bg-theme-hover transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-medium text-theme-text-primary text-sm">{report.name}</h3>
                      <p className="text-xs text-theme-text-secondary mt-1">{report.type}</p>
                      <div className="flex items-center space-x-4 mt-2 text-xs text-theme-text-secondary">
                        <span>{report.generatedAt.toLocaleDateString()}</span>
                        <span>{report.format}</span>
                        <span>{report.size}</span>
                      </div>
                    </div>
                    <button className="text-emerald-600 hover:text-emerald-700 p-1">
                      <Download className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Stats */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Statistics</h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Total Cases</span>
                <span className="font-bold text-gray-900">{alerts.length}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Active Alerts</span>
                <span className="font-bold text-red-600">
                  {alerts.filter(a => a.status === 'active').length}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Resolved Cases</span>
                <span className="font-bold text-green-600">
                  {alerts.filter(a => a.status === 'resolved').length}
                </span>
              </div>
              {detectionData && (
                <>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Forest Loss</span>
                    <span className="font-bold text-emerald-600">
                      {detectionData.deforestedArea.toLocaleString()} ha
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Mining Activity</span>
                    <span className="font-bold text-blue-600">
                      {detectionData.miningArea.toLocaleString()} ha
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportsPage;