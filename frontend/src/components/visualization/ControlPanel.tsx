/**
 * ControlPanel Component
 * System status, emergency controls, and communication interface
 */

import React, { useState } from 'react';
import { usePerformanceMonitor } from '../../hooks/useAnimation';
import {
  ControlPanelProps,
  SystemStatus,
  Scenario,
  CommunicationMessage,
} from '../../types/visualization';

export const ControlPanel: React.FC<ControlPanelProps> = ({
  systemStatus,
  onEmergencyStop,
  onTestScenario,
  onCommunication,
}) => {
  const [activeSection, setActiveSection] = useState<'STATUS' | 'EMERGENCY' | 'COMMUNICATION' | 'SCENARIOS'>('STATUS');
  const [messageContent, setMessageContent] = useState('');
  const [messagePriority, setMessagePriority] = useState<'NORMAL' | 'HIGH' | 'URGENT'>('NORMAL');
  const [selectedScenario, setSelectedScenario] = useState<string>('');
  
  const { fps, frameTime, isPerformant } = usePerformanceMonitor();

  const emergencyConfirm = () => {
    if (window.confirm('⚠️ Are you sure you want to initiate EMERGENCY STOP for ALL trains? This action cannot be undone immediately.')) {
      onEmergencyStop();
    }
  };

  const handleSendMessage = () => {
    if (!messageContent.trim()) return;

    const message: CommunicationMessage = {
      id: Date.now().toString(),
      from: 'CONTROLLER',
      to: 'ALL_STATIONS',
      channel: 'TEXT',
      content: messageContent,
      timestamp: new Date(),
      priority: messagePriority,
    };

    onCommunication(message);
    setMessageContent('');
  };

  const predefinedScenarios: Scenario[] = [
    {
      id: 'conflict_test_1',
      name: 'Head-On Collision Test',
      description: 'Simulate two trains approaching on same track',
      type: 'CONFLICT',
      parameters: { trains: 2, section: 'TEST_SECTION_1' },
    },
    {
      id: 'capacity_test_1',
      name: 'Station Capacity Test',
      description: 'Test maximum station throughput',
      type: 'CAPACITY_TEST',
      parameters: { station: 'CENTRAL_STATION', trainCount: 10 },
    },
    {
      id: 'emergency_test_1',
      name: 'Emergency Protocol Test',
      description: 'Test emergency stop and evacuation procedures',
      type: 'EMERGENCY',
      parameters: { affectedSections: ['SECTION_A', 'SECTION_B'] },
    },
  ];

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg border border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-gray-800 to-gray-900">
        <h2 className="text-xl font-bold text-white">Control Center</h2>
        <p className="text-sm text-gray-300 mt-1">System Management & Emergency Controls</p>
      </div>

      {/* Section Tabs */}
      <div className="flex border-b border-gray-200 bg-gray-50">
        {['STATUS', 'EMERGENCY', 'COMMUNICATION', 'SCENARIOS'].map(section => (
          <button
            key={section}
            onClick={() => setActiveSection(section as any)}
            className={`flex-1 py-3 px-4 font-medium text-sm transition-colors ${
              activeSection === section
                ? 'text-blue-600 border-b-2 border-blue-600 bg-white'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            {section}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* STATUS Section */}
        {activeSection === 'STATUS' && systemStatus && (
          <div className="space-y-4">
            {/* System Health */}
            <div className={`p-4 rounded-lg border-2 ${
              systemStatus.operational ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-semibold">
                  {systemStatus.operational ? '✓ System Operational' : '✗ System Issues Detected'}
                </h3>
                <div className={`w-4 h-4 rounded-full ${
                  systemStatus.operational ? 'bg-green-500 animate-pulse' : 'bg-red-500 animate-pulse'
                }`} />
              </div>
              <p className="text-sm text-gray-700">
                Last updated: {new Date(systemStatus.timestamp).toLocaleString()}
              </p>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                <div className="text-xs text-blue-600 font-semibold mb-1">ACTIVE TRAINS</div>
                <div className="text-3xl font-bold text-blue-900">{systemStatus.trainCount}</div>
              </div>
              
              <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                <div className="text-xs text-red-600 font-semibold mb-1">CONFLICTS</div>
                <div className="text-3xl font-bold text-red-900">{systemStatus.activeConflicts}</div>
              </div>
              
              <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                <div className="text-xs text-yellow-600 font-semibold mb-1">AVG DELAY</div>
                <div className="text-3xl font-bold text-yellow-900">{systemStatus.averageDelay.toFixed(1)}</div>
                <div className="text-xs text-yellow-700">minutes</div>
              </div>
              
              <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                <div className="text-xs text-purple-600 font-semibold mb-1">SYSTEM LOAD</div>
                <div className="text-3xl font-bold text-purple-900">{systemStatus.systemLoad}</div>
                <div className="text-xs text-purple-700">%</div>
              </div>
            </div>

            {/* System Load Bar */}
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-gray-700">System Load</span>
                <span className="text-sm text-gray-600">{systemStatus.systemLoad}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    systemStatus.systemLoad > 80 ? 'bg-red-500' :
                    systemStatus.systemLoad > 60 ? 'bg-yellow-500' :
                    'bg-green-500'
                  }`}
                  style={{ width: `${systemStatus.systemLoad}%` }}
                />
              </div>
            </div>

            {/* Section Status */}
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Section Status Distribution</h3>
              <div className="space-y-2">
                {Object.entries(systemStatus.sectionsStatus).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between">
                    <span className="text-sm text-gray-700">{status}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-900">{count}</span>
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-full rounded-full ${
                            status === 'CLEAR' ? 'bg-green-500' :
                            status === 'OCCUPIED' ? 'bg-yellow-500' :
                            status === 'CONFLICT' ? 'bg-red-500' :
                            'bg-gray-500'
                          }`}
                          style={{ width: `${(count / Object.values(systemStatus.sectionsStatus).reduce((a, b) => a + b, 0)) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Performance Metrics</h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs text-gray-600">FPS</div>
                  <div className={`text-lg font-bold ${isPerformant ? 'text-green-600' : 'text-red-600'}`}>
                    {fps}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-600">Frame Time</div>
                  <div className="text-lg font-bold text-gray-900">{frameTime.toFixed(1)}ms</div>
                </div>
                <div>
                  <div className="text-xs text-gray-600">Latency</div>
                  <div className="text-lg font-bold text-gray-900">{systemStatus.performance.latency}ms</div>
                </div>
                <div>
                  <div className="text-xs text-gray-600">Memory</div>
                  <div className="text-lg font-bold text-gray-900">{systemStatus.performance.memoryUsage}MB</div>
                </div>
              </div>
            </div>

            {/* Alerts */}
            {systemStatus.alerts.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-gray-700">System Alerts</h3>
                {systemStatus.alerts.map(alert => (
                  <div
                    key={alert.id}
                    className={`p-3 rounded-lg border ${
                      alert.type === 'CRITICAL' ? 'bg-red-50 border-red-300' :
                      alert.type === 'ERROR' ? 'bg-orange-50 border-orange-300' :
                      alert.type === 'WARNING' ? 'bg-yellow-50 border-yellow-300' :
                      'bg-blue-50 border-blue-300'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-gray-900">{alert.type}</span>
                      <span className="text-xs text-gray-500">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700">{alert.message}</p>
                    <p className="text-xs text-gray-500 mt-1">Source: {alert.source}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* EMERGENCY Section */}
        {activeSection === 'EMERGENCY' && (
          <div className="space-y-4">
            <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4">
              <h3 className="text-lg font-bold text-red-900 mb-2">⚠️ Emergency Controls</h3>
              <p className="text-sm text-red-800">
                These controls should only be used in genuine emergency situations. All actions are logged and monitored.
              </p>
            </div>

            <button
              onClick={emergencyConfirm}
              className="w-full py-4 bg-red-600 text-white rounded-lg font-bold text-lg hover:bg-red-700 transition-colors shadow-lg hover:shadow-xl border-4 border-red-800"
            >
              🚨 EMERGENCY STOP ALL TRAINS
            </button>

            <div className="grid grid-cols-2 gap-3">
              <button className="py-3 px-4 bg-orange-600 text-white rounded-lg font-semibold hover:bg-orange-700 transition-colors">
                🔒 Lock All Sections
              </button>
              <button className="py-3 px-4 bg-yellow-600 text-white rounded-lg font-semibold hover:bg-yellow-700 transition-colors">
                ⚠️ System-Wide Alert
              </button>
              <button className="py-3 px-4 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition-colors">
                📞 Emergency Call
              </button>
              <button className="py-3 px-4 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors">
                🔄 System Reset
              </button>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Emergency Protocols</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>All emergency exits are operational</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Emergency communication systems active</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Backup power systems ready</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Emergency services on standby</span>
                </li>
              </ul>
            </div>
          </div>
        )}

        {/* COMMUNICATION Section */}
        {activeSection === 'COMMUNICATION' && (
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-300 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-blue-900 mb-1">Broadcast Message</h3>
              <p className="text-sm text-blue-700">Send messages to all stations and trains</p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Priority Level</label>
              <div className="flex gap-2">
                {(['NORMAL', 'HIGH', 'URGENT'] as const).map(priority => (
                  <button
                    key={priority}
                    onClick={() => setMessagePriority(priority)}
                    className={`flex-1 py-2 px-4 rounded-lg font-medium text-sm transition-colors ${
                      messagePriority === priority
                        ? priority === 'URGENT' ? 'bg-red-600 text-white' :
                          priority === 'HIGH' ? 'bg-orange-600 text-white' :
                          'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    {priority}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Message</label>
              <textarea
                value={messageContent}
                onChange={(e) => setMessageContent(e.target.value)}
                placeholder="Enter your message..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={5}
              />
            </div>

            <button
              onClick={handleSendMessage}
              disabled={!messageContent.trim()}
              className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              📢 Send Broadcast
            </button>

            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Quick Messages</h4>
              <div className="space-y-2">
                {[
                  'All systems operating normally',
                  'Minor delays expected, please stand by',
                  'Scheduled maintenance in progress',
                  'Weather advisory in effect',
                ].map((msg, idx) => (
                  <button
                    key={idx}
                    onClick={() => setMessageContent(msg)}
                    className="w-full text-left px-3 py-2 bg-white border border-gray-200 rounded hover:bg-gray-50 text-sm"
                  >
                    {msg}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* SCENARIOS Section */}
        {activeSection === 'SCENARIOS' && (
          <div className="space-y-4">
            <div className="bg-purple-50 border border-purple-300 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-purple-900 mb-1">What-If Scenario Testing</h3>
              <p className="text-sm text-purple-700">Test system behavior under various conditions</p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Select Scenario</label>
              <select
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="">Choose a scenario...</option>
                {predefinedScenarios.map(scenario => (
                  <option key={scenario.id} value={scenario.id}>
                    {scenario.name}
                  </option>
                ))}
              </select>
            </div>

            {selectedScenario && (
              <>
                {predefinedScenarios
                  .filter(s => s.id === selectedScenario)
                  .map(scenario => (
                    <div key={scenario.id} className="bg-white p-4 rounded-lg border-2 border-purple-300">
                      <h4 className="font-semibold text-gray-900 mb-2">{scenario.name}</h4>
                      <p className="text-sm text-gray-700 mb-3">{scenario.description}</p>
                      <div className="bg-gray-50 p-3 rounded text-xs font-mono text-gray-600">
                        {JSON.stringify(scenario.parameters, null, 2)}
                      </div>
                    </div>
                  ))}

                <button
                  onClick={() => {
                    const scenario = predefinedScenarios.find(s => s.id === selectedScenario);
                    if (scenario) onTestScenario(scenario);
                  }}
                  className="w-full py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition-colors"
                >
                  🧪 Run Scenario Test
                </button>
              </>
            )}

            <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-yellow-900 mb-2">⚠️ Testing Mode Notice</h4>
              <p className="text-sm text-yellow-800">
                Scenarios run in simulation mode and do not affect actual train operations. Results are logged for analysis.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ControlPanel;
