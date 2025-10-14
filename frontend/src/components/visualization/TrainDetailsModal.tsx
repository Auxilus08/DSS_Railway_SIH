/**
 * TrainDetailsModal Component
 * Displays detailed train information with manual control options
 */

import React, { useState } from 'react';
import {
  TrainDetailsModalProps,
  Train,
  TrainHistory,
  ControllerAction,
  ActionType,
} from '../../types/visualization';

const STATUS_COLORS = {
  RUNNING: 'bg-green-100 text-green-800 border-green-300',
  STOPPED: 'bg-red-100 text-red-800 border-red-300',
  DELAYED: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  EMERGENCY: 'bg-red-200 text-red-900 border-red-400',
  MAINTENANCE: 'bg-gray-100 text-gray-800 border-gray-300',
};

const TRAIN_TYPE_ICONS = {
  EXPRESS: '🚄',
  PASSENGER: '🚂',
  FREIGHT: '🚆',
  SUBURBAN: '🚊',
};

export const TrainDetailsModal: React.FC<TrainDetailsModalProps> = ({
  train,
  history,
  onClose,
  onControlAction,
}) => {
  const [activeTab, setActiveTab] = useState<'INFO' | 'ROUTE' | 'HISTORY' | 'CONTROL'>('INFO');
  const [controlAction, setControlAction] = useState<ActionType>('SPEED_CHANGE');
  const [speedValue, setSpeedValue] = useState(train?.currentSpeed || 0);
  const [routeChange, setRouteChange] = useState('');

  if (!train) return null;

  const handleControlSubmit = () => {
    const action: ControllerAction = {
      id: Date.now().toString(),
      controllerId: 'current_user', // Would come from auth context
      timestamp: new Date(),
      type: controlAction,
      target: train.id,
      parameters: {
        speed: controlAction === 'SPEED_CHANGE' ? speedValue : undefined,
        route: controlAction === 'ROUTE_CHANGE' ? routeChange : undefined,
      },
      status: 'INITIATED',
    };

    onControlAction?.(action);
  };

  const speedPercentage = (train.currentSpeed / train.maxSpeed) * 100;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-blue-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-5xl">{TRAIN_TYPE_ICONS[train.type]}</span>
              <div>
                <h2 className="text-2xl font-bold text-white">{train.name}</h2>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-white text-sm opacity-90">#{train.trainNumber}</span>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${STATUS_COLORS[train.status]}`}>
                    {train.status}
                  </span>
                </div>
              </div>
            </div>
            
            <button
              onClick={onClose}
              className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition-colors"
            >
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 bg-gray-50">
          {['INFO', 'ROUTE', 'HISTORY', 'CONTROL'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`flex-1 py-3 px-4 font-medium text-sm transition-colors ${
                activeTab === tab
                  ? 'text-blue-600 border-b-2 border-blue-600 bg-white'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* INFO Tab */}
          {activeTab === 'INFO' && (
            <div className="space-y-6">
              {/* Real-time Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-200">
                  <div className="text-xs text-blue-600 font-semibold mb-1">CURRENT SPEED</div>
                  <div className="text-2xl font-bold text-blue-900">{train.currentSpeed}</div>
                  <div className="text-xs text-blue-700">km/h</div>
                </div>
                
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg border border-purple-200">
                  <div className="text-xs text-purple-600 font-semibold mb-1">MAX SPEED</div>
                  <div className="text-2xl font-bold text-purple-900">{train.maxSpeed}</div>
                  <div className="text-xs text-purple-700">km/h</div>
                </div>
                
                <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg border border-green-200">
                  <div className="text-xs text-green-600 font-semibold mb-1">PASSENGERS</div>
                  <div className="text-2xl font-bold text-green-900">{train.passengerCount || 'N/A'}</div>
                  <div className="text-xs text-green-700">onboard</div>
                </div>
                
                <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-4 rounded-lg border border-orange-200">
                  <div className="text-xs text-orange-600 font-semibold mb-1">DELAY</div>
                  <div className="text-2xl font-bold text-orange-900">{train.delays}</div>
                  <div className="text-xs text-orange-700">minutes</div>
                </div>
              </div>

              {/* Speed Gauge */}
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-gray-700">Speed Performance</span>
                  <span className="text-sm text-gray-600">{speedPercentage.toFixed(0)}% of max</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      speedPercentage > 80 ? 'bg-green-500' :
                      speedPercentage > 50 ? 'bg-yellow-500' :
                      'bg-red-500'
                    }`}
                    style={{ width: `${speedPercentage}%` }}
                  />
                </div>
              </div>

              {/* Journey Info */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-3">
                  <div>
                    <div className="text-xs text-gray-500 font-semibold mb-1">ORIGIN</div>
                    <div className="text-lg font-semibold text-gray-900">{train.origin}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 font-semibold mb-1">DESTINATION</div>
                    <div className="text-lg font-semibold text-gray-900">{train.destination}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 font-semibold mb-1">PRIORITY</div>
                    <div className="flex items-center gap-1">
                      {Array.from({ length: 10 }).map((_, i) => (
                        <div
                          key={i}
                          className={`w-2 h-4 rounded ${
                            i < train.priority ? 'bg-blue-500' : 'bg-gray-200'
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="text-xs text-gray-500 font-semibold mb-1">NEXT STATION</div>
                    <div className="text-lg font-semibold text-gray-900">{train.nextStation}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 font-semibold mb-1">ETA</div>
                    <div className="text-lg font-semibold text-gray-900">
                      {new Date(train.eta).toLocaleTimeString()}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 font-semibold mb-1">DISTANCE TO NEXT</div>
                    <div className="text-lg font-semibold text-gray-900">{train.distanceToNext.toFixed(1)} km</div>
                  </div>
                </div>
              </div>

              {/* Current Section */}
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                <div className="text-xs text-blue-600 font-semibold mb-1">CURRENT SECTION</div>
                <div className="text-lg font-semibold text-blue-900">{train.currentSection}</div>
                <div className="text-sm text-blue-700 mt-1">Heading: {train.heading}°</div>
              </div>

              {/* Last Update */}
              <div className="text-xs text-gray-500 text-center">
                Last updated: {new Date(train.lastUpdate).toLocaleString()}
              </div>
            </div>
          )}

          {/* ROUTE Tab */}
          {activeTab === 'ROUTE' && (
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Scheduled Route</h3>
                <div className="space-y-2">
                  {train.scheduledRoute.map((sectionId, idx) => (
                    <div
                      key={idx}
                      className={`flex items-center gap-3 p-3 rounded-lg border ${
                        sectionId === train.currentSection
                          ? 'bg-blue-50 border-blue-300'
                          : 'bg-gray-50 border-gray-200'
                      }`}
                    >
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                        sectionId === train.currentSection
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-300 text-gray-700'
                      }`}>
                        {idx + 1}
                      </div>
                      <div className="flex-1">
                        <div className="font-semibold text-gray-900">{sectionId}</div>
                        {sectionId === train.currentSection && (
                          <div className="text-xs text-blue-600 font-medium">← Current Location</div>
                        )}
                      </div>
                      {train.actualRoute.includes(sectionId) && (
                        <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {train.actualRoute.length !== train.scheduledRoute.length && (
                <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-300">
                  <h3 className="text-sm font-semibold text-yellow-800 mb-2">⚠️ Route Deviation Detected</h3>
                  <p className="text-sm text-yellow-700">
                    The actual route differs from the scheduled route. This may indicate a rerouting or unexpected path change.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* HISTORY Tab */}
          {activeTab === 'HISTORY' && (
            <div className="space-y-4">
              {history ? (
                <>
                  {/* Speed Profile Chart */}
                  <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">Speed Profile</h3>
                    <div className="h-40 flex items-end gap-1">
                      {history.speedProfile.slice(-20).map((reading, idx) => {
                        const height = (reading.speed / train.maxSpeed) * 100;
                        return (
                          <div
                            key={idx}
                            className="flex-1 bg-blue-500 rounded-t"
                            style={{ height: `${height}%`, minHeight: '2px' }}
                            title={`${reading.speed} km/h`}
                          />
                        );
                      })}
                    </div>
                  </div>

                  {/* Events */}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">Recent Events</h3>
                    <div className="space-y-2">
                      {history.events.slice(-10).reverse().map(event => (
                        <div
                          key={event.id}
                          className={`p-3 rounded-lg border ${
                            event.severity === 'CRITICAL' ? 'bg-red-50 border-red-300' :
                            event.severity === 'WARNING' ? 'bg-yellow-50 border-yellow-300' :
                            'bg-gray-50 border-gray-200'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-semibold text-gray-900">{event.type.replace(/_/g, ' ')}</span>
                            <span className="text-xs text-gray-500">
                              {new Date(event.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <p className="text-sm text-gray-700">{event.description}</p>
                          <p className="text-xs text-gray-500 mt-1">Location: {event.location}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Delays */}
                  {history.delays.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-3">Delay History</h3>
                      <div className="space-y-2">
                        {history.delays.map((delay, idx) => (
                          <div key={idx} className="p-3 bg-orange-50 rounded-lg border border-orange-200">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-semibold text-orange-900">{delay.duration} minutes</span>
                              <span className="text-xs text-orange-700">{delay.location}</span>
                            </div>
                            <p className="text-sm text-orange-800">{delay.reason}</p>
                            <div className="text-xs text-orange-600 mt-1">
                              {new Date(delay.startTime).toLocaleString()}
                              {delay.endTime && ` - ${new Date(delay.endTime).toLocaleString()}`}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p>No historical data available</p>
                </div>
              )}
            </div>
          )}

          {/* CONTROL Tab */}
          {activeTab === 'CONTROL' && (
            <div className="space-y-6">
              <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4">
                <h3 className="font-semibold text-yellow-900 mb-2">⚠️ Manual Control Mode</h3>
                <p className="text-sm text-yellow-800">
                  Use these controls only when necessary. All actions are logged and require authorization.
                </p>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Control Action</label>
                <select
                  value={controlAction}
                  onChange={(e) => setControlAction(e.target.value as ActionType)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="SPEED_CHANGE">Change Speed</option>
                  <option value="ROUTE_CHANGE">Change Route</option>
                  <option value="STOP_TRAIN">Stop Train</option>
                  <option value="EMERGENCY_STOP">Emergency Stop</option>
                  <option value="PRIORITY_OVERRIDE">Override Priority</option>
                  <option value="MANUAL_CONTROL">Full Manual Control</option>
                </select>
              </div>

              {controlAction === 'SPEED_CHANGE' && (
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    New Speed: {speedValue} km/h
                  </label>
                  <input
                    type="range"
                    min="0"
                    max={train.maxSpeed}
                    value={speedValue}
                    onChange={(e) => setSpeedValue(Number(e.target.value))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-600 mt-1">
                    <span>0 km/h</span>
                    <span>{train.maxSpeed} km/h</span>
                  </div>
                </div>
              )}

              {controlAction === 'ROUTE_CHANGE' && (
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">New Route</label>
                  <textarea
                    value={routeChange}
                    onChange={(e) => setRouteChange(e.target.value)}
                    placeholder="Enter section IDs separated by commas"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={3}
                  />
                </div>
              )}

              <button
                onClick={handleControlSubmit}
                className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors shadow-lg hover:shadow-xl"
              >
                Execute Control Action
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TrainDetailsModal;
