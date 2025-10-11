import React, { useState } from 'react';
import { Users, Settings, Bell, Shield, Database, Activity } from 'lucide-react';

const AdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'users' | 'settings' | 'alerts' | 'system'>('users');

  const tabs = [
    { id: 'users', label: 'User Management', icon: Users },
    { id: 'settings', label: 'System Settings', icon: Settings },
    { id: 'alerts', label: 'Alert Configuration', icon: Bell },
    { id: 'system', label: 'System Status', icon: Database }
  ];

  const mockUsers = [
    { id: 1, name: 'Dr. Sarah Johnson', email: 'sarah.johnson@ecoguard.org', role: 'Administrator', status: 'Active', lastLogin: '2 hours ago' },
    { id: 2, name: 'Mark Thompson', email: 'mark.thompson@forestry.gov', role: 'Analyst', status: 'Active', lastLogin: '1 day ago' },
    { id: 3, name: 'Lisa Chen', email: 'lisa.chen@conservation.org', role: 'Viewer', status: 'Active', lastLogin: '3 days ago' },
    { id: 4, name: 'James Wilson', email: 'james.wilson@mining.dept', role: 'Investigator', status: 'Inactive', lastLogin: '1 week ago' }
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Administration Panel</h1>
        <p className="text-gray-600">Manage users, system settings, and monitoring configuration</p>
      </div>

      {/* Tab Navigation */}
      <div className="bg-theme-card rounded-lg shadow-sm">
        <div className="border-b border-theme-border">
          <nav className="flex space-x-8 px-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'border-emerald-500 text-emerald-600'
                    : 'border-transparent text-theme-text-secondary hover:text-theme-text-primary hover:border-theme-border'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* Users Tab */}
          {activeTab === 'users' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">User Management</h3>
                <button className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">
                  Add New User
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Login</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {mockUsers.map((user) => (
                      <tr key={user.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <div className="text-sm font-medium text-gray-900">{user.name}</div>
                            <div className="text-sm text-gray-500">{user.email}</div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="inline-flex px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                            {user.role}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                            user.status === 'Active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {user.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {user.lastLogin}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <button className="text-emerald-600 hover:text-emerald-700 mr-3">Edit</button>
                          <button className="text-red-600 hover:text-red-700">Disable</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">System Settings</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Detection Sensitivity</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>High (90% confidence threshold)</option>
                      <option>Medium (80% confidence threshold)</option>
                      <option>Low (70% confidence threshold)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Minimum Area Threshold</label>
                    <input
                      type="number"
                      defaultValue="5"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      placeholder="Hectares"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Scan Frequency</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Every 5 days (Sentinel-2 revisit)</option>
                      <option>Daily (when available)</option>
                      <option>Weekly</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Auto-Alert Threshold</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Critical alerts only</option>
                      <option>High priority and above</option>
                      <option>All alerts</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Data Retention</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>1 year</option>
                      <option>2 years</option>
                      <option>5 years</option>
                      <option>Indefinite</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">API Rate Limit</label>
                    <input
                      type="number"
                      defaultValue="1000"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      placeholder="Requests per hour"
                    />
                  </div>
                </div>
              </div>

              <button className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">
                Save Settings
              </button>
            </div>
          )}

          {/* Alerts Tab */}
          {activeTab === 'alerts' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">Alert Configuration</h3>
              
              <div className="space-y-4">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-3">Notification Channels</h4>
                  <div className="space-y-3">
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" defaultChecked className="rounded border-gray-300 text-emerald-600" />
                      <span className="text-sm">Email notifications</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" defaultChecked className="rounded border-gray-300 text-emerald-600" />
                      <span className="text-sm">SMS alerts for critical cases</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" className="rounded border-gray-300 text-emerald-600" />
                      <span className="text-sm">Webhook notifications</span>
                    </label>
                  </div>
                </div>

                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-3">Alert Recipients</h4>
                  <div className="space-y-2">
                    <input
                      type="email"
                      placeholder="Add email address..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    />
                    <div className="flex flex-wrap gap-2">
                      {['forestry@gov.zw', 'alerts@conservation.org', 'emergency@mining.dept'].map((email) => (
                        <span key={email} className="inline-flex items-center px-2 py-1 bg-emerald-100 text-emerald-700 text-xs rounded-full">
                          {email}
                          <button className="ml-1 text-emerald-500 hover:text-emerald-700">×</button>
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* System Tab */}
          {activeTab === 'system' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">System Status</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      <span className="font-medium text-green-800">Satellite Data Feed</span>
                    </div>
                    <p className="text-sm text-green-700">Connected • Last update: 2 hours ago</p>
                  </div>

                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      <span className="font-medium text-green-800">AI Processing Engine</span>
                    </div>
                    <p className="text-sm text-green-700">Operational • 99.8% uptime</p>
                  </div>

                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                      <span className="font-medium text-yellow-800">Database Storage</span>
                    </div>
                    <p className="text-sm text-yellow-700">78% capacity • Consider cleanup</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-medium text-gray-900 mb-3">Processing Statistics</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Images Processed Today:</span>
                        <span className="font-medium">1,247</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Alerts Generated:</span>
                        <span className="font-medium">23</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Average Processing Time:</span>
                        <span className="font-medium">2.3 seconds</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Queue Size:</span>
                        <span className="font-medium">12 images</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-medium text-gray-900 mb-3">System Resources</h4>
                    <div className="space-y-3">
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600">CPU Usage</span>
                          <span className="font-medium">34%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div className="bg-blue-500 h-2 rounded-full" style={{ width: '34%' }}></div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600">Memory Usage</span>
                          <span className="font-medium">67%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div className="bg-yellow-500 h-2 rounded-full" style={{ width: '67%' }}></div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600">Storage Usage</span>
                          <span className="font-medium">78%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div className="bg-orange-500 h-2 rounded-full" style={{ width: '78%' }}></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">System Configuration</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Detection Model</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>ResNet-50 (Current)</option>
                      <option>U-Net Segmentation</option>
                      <option>EfficientNet-B7</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Processing Priority</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Real-time (High CPU)</option>
                      <option>Balanced</option>
                      <option>Batch Processing (Low CPU)</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Backup Frequency</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Daily</option>
                      <option>Weekly</option>
                      <option>Monthly</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Log Level</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Error</option>
                      <option>Warning</option>
                      <option>Info</option>
                      <option>Debug</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Alerts Tab */}
          {activeTab === 'alerts' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">Alert Configuration</h3>
              
              <div className="space-y-4">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-3">Severity Thresholds</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">Critical (hectares)</label>
                      <input type="number" defaultValue="50" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">High (hectares)</label>
                      <input type="number" defaultValue="20" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">Medium (hectares)</label>
                      <input type="number" defaultValue="10" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">Low (hectares)</label>
                      <input type="number" defaultValue="5" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-3">Notification Settings</h4>
                  <div className="space-y-3">
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" defaultChecked className="rounded border-gray-300 text-emerald-600" />
                      <span className="text-sm">Send immediate alerts for critical cases</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" defaultChecked className="rounded border-gray-300 text-emerald-600" />
                      <span className="text-sm">Daily summary reports</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" className="rounded border-gray-300 text-emerald-600" />
                      <span className="text-sm">Weekly trend analysis</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* System Tab */}
          {activeTab === 'system' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">System Monitoring</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                  <Activity className="h-8 w-8 text-green-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-green-600">99.8%</div>
                  <div className="text-sm text-green-700">System Uptime</div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                  <Shield className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-blue-600">1,247</div>
                  <div className="text-sm text-blue-700">Images Processed Today</div>
                </div>

                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 text-center">
                  <Database className="h-8 w-8 text-purple-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-purple-600">2.3TB</div>
                  <div className="text-sm text-purple-700">Data Stored</div>
                </div>
              </div>

              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-3">Recent System Events</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-gray-700">Model retrained with new data</span>
                    <span className="text-gray-500">2 hours ago</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-gray-700">Database backup completed</span>
                    <span className="text-gray-500">6 hours ago</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-gray-700">New satellite data ingested</span>
                    <span className="text-gray-500">8 hours ago</span>
                  </div>
                  <div className="flex justify-between items-center py-2">
                    <span className="text-gray-700">System maintenance completed</span>
                    <span className="text-gray-500">1 day ago</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminPage;