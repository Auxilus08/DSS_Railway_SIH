/**
 * Railway Network Visualization Dashboard
 * Main control room interface integrating all visualization components
 */

import React, { useState, useEffect, useMemo } from 'react';
import NetworkMap from '../components/visualization/NetworkMap';
import ConflictPanel from '../components/visualization/ConflictPanel';
import TrainDetailsModal from '../components/visualization/TrainDetailsModal';
import ControlPanel from '../components/visualization/ControlPanel';
import { useRealTimeData } from '../hooks/useRealTimeData';
import {
  Train,
  Section,
  Conflict,
  VisualizationConfig,
  Scenario,
  CommunicationMessage,
  ControllerAction,
  TrainHistory,
  NetworkGraph,
  SystemStatus,
} from '../types/visualization';

// Default configuration
const DEFAULT_CONFIG: VisualizationConfig = {
  width: 1200,
  height: 800,
  zoom: {
    min: 0.5,
    max: 10,
    initial: 1,
  },
  animation: {
    duration: 300,
    enabled: true,
    fps: 60,
  },
  colors: {
    sections: {
      CLEAR: '#10b981',
      OCCUPIED: '#f59e0b',
      CONFLICT: '#ef4444',
      MAINTENANCE: '#6b7280',
      BLOCKED: '#991b1b',
    },
    trains: {
      RUNNING: '#3b82f6',
      STOPPED: '#ef4444',
      DELAYED: '#f59e0b',
      EMERGENCY: '#dc2626',
      MAINTENANCE: '#6b7280',
    },
    conflicts: {
      LOW: '#3b82f6',
      MEDIUM: '#f59e0b',
      HIGH: '#fb923c',
      CRITICAL: '#ef4444',
    },
    recommendations: '#60a5fa',
  },
  layers: {
    network: true,
    trains: true,
    conflicts: true,
    recommendations: true,
    labels: true,
  },
};

export const Visualization: React.FC = () => {
  const [selectedTrain, setSelectedTrain] = useState<string | undefined>();
  const [selectedSection, setSelectedSection] = useState<string | undefined>();
  const [selectedConflict, setSelectedConflict] = useState<string | undefined>();
  const [trainModalOpen, setTrainModalOpen] = useState(false);
  const [config, setConfig] = useState<VisualizationConfig>(DEFAULT_CONFIG);
  const [leftPanelWidth, setLeftPanelWidth] = useState(30); // percentage
  const [rightPanelWidth, setRightPanelWidth] = useState(25); // percentage

  // Get real-time data
  const {
    trains,
    sections,
    conflicts,
    recommendations,
    systemStatus,
    isConnected,
    error,
    getTrainById,
    sendMessage,
  } = useRealTimeData();

  // Create network graph
  const networkGraph: NetworkGraph = useMemo(() => ({
    stations: [], // Would be populated from API
    sections,
    junctions: [], // Would be populated from API
    trains,
    bounds: {
      north: 0,
      south: 0,
      east: 0,
      west: 0,
    },
  }), [trains, sections]);

  // Mock system status if not available
  const displaySystemStatus: SystemStatus = systemStatus || {
    timestamp: new Date(),
    operational: true,
    trainCount: trains.length,
    activeConflicts: conflicts.length,
    sectionsStatus: {
      CLEAR: sections.filter(s => s.status === 'CLEAR').length,
      OCCUPIED: sections.filter(s => s.status === 'OCCUPIED').length,
      CONFLICT: sections.filter(s => s.status === 'CONFLICT').length,
      MAINTENANCE: sections.filter(s => s.status === 'MAINTENANCE').length,
      BLOCKED: sections.filter(s => s.status === 'BLOCKED').length,
    },
    averageDelay: trains.reduce((sum, t) => sum + t.delays, 0) / (trains.length || 1),
    systemLoad: Math.min(100, (trains.length / 10) * 100),
    performance: {
      fps: 60,
      latency: 50,
      updateFrequency: 10,
      dataPoints: trains.length + sections.length,
      memoryUsage: 128,
    },
    alerts: [],
  };

  // Handlers
  const handleTrainClick = (train: Train) => {
    setSelectedTrain(train.id);
    setTrainModalOpen(true);
  };

  const handleSectionClick = (section: Section) => {
    setSelectedSection(section.id);
  };

  const handleConflictSelect = (conflict: Conflict) => {
    setSelectedConflict(conflict.id);
  };

  const handleAcceptRecommendation = (recommendationId: string) => {
    console.log('Accepting recommendation:', recommendationId);
    // Would send to backend via custom API call
    // sendMessage is for existing WebSocket types
  };

  const handleRejectRecommendation = (recommendationId: string) => {
    console.log('Rejecting recommendation:', recommendationId);
    // Would send to backend via custom API call
  };

  const handleControlAction = (action: ControllerAction) => {
    console.log('Executing control action:', action);
    // Would send to backend via custom API call
  };

  const handleEmergencyStop = () => {
    console.log('EMERGENCY STOP INITIATED');
    // Would send to backend via custom API call
    sendMessage({
      type: 'NOTIFICATION',
      data: {
        type: 'CRITICAL',
        title: 'Emergency Stop',
        message: 'Emergency stop initiated by controller',
      },
    });
  };

  const handleTestScenario = (scenario: Scenario) => {
    console.log('Running scenario:', scenario);
    // Would send to backend
  };

  const handleCommunication = (message: CommunicationMessage) => {
    console.log('Broadcasting message:', message);
    // Would send to backend
  };

  const handleToggleLayer = (layer: keyof VisualizationConfig['layers']) => {
    setConfig(prev => ({
      ...prev,
      layers: {
        ...prev.layers,
        [layer]: !prev.layers[layer],
      },
    }));
  };

  // Get selected train details
  const selectedTrainData = selectedTrain ? getTrainById(selectedTrain) : null;

  // Mock train history (would come from API)
  const trainHistory: TrainHistory | undefined = selectedTrainData ? {
    trainId: selectedTrainData.id,
    positions: [],
    speedProfile: [],
    events: [],
    delays: [],
  } : undefined;

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Top Bar */}
      <div className="bg-gradient-to-r from-blue-900 to-blue-800 text-white px-6 py-4 shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Railway Network Control Center</h1>
            <p className="text-sm text-blue-200 mt-1">Real-Time Visualization & Management System</p>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Connection Status */}
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`}>
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-white animate-pulse' : 'bg-white'}`} />
              <span className="text-sm font-medium">{isConnected ? 'Connected' : 'Disconnected'}</span>
            </div>

            {/* Statistics */}
            <div className="flex items-center gap-4 px-4 py-2 bg-white bg-opacity-10 rounded-lg">
              <div className="text-center">
                <div className="text-xs text-blue-200">Trains</div>
                <div className="text-lg font-bold">{trains.length}</div>
              </div>
              <div className="h-8 w-px bg-white bg-opacity-20" />
              <div className="text-center">
                <div className="text-xs text-blue-200">Conflicts</div>
                <div className="text-lg font-bold text-red-300">{conflicts.length}</div>
              </div>
              <div className="h-8 w-px bg-white bg-opacity-20" />
              <div className="text-center">
                <div className="text-xs text-blue-200">Sections</div>
                <div className="text-lg font-bold">{sections.length}</div>
              </div>
            </div>

            {/* Layer Controls */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleToggleLayer('trains')}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  config.layers.trains
                    ? 'bg-white text-blue-900'
                    : 'bg-white bg-opacity-20 text-white'
                }`}
                title="Toggle Trains Layer"
              >
                🚂
              </button>
              <button
                onClick={() => handleToggleLayer('conflicts')}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  config.layers.conflicts
                    ? 'bg-white text-blue-900'
                    : 'bg-white bg-opacity-20 text-white'
                }`}
                title="Toggle Conflicts Layer"
              >
                ⚠️
              </button>
              <button
                onClick={() => handleToggleLayer('labels')}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  config.layers.labels
                    ? 'bg-white text-blue-900'
                    : 'bg-white bg-opacity-20 text-white'
                }`}
                title="Toggle Labels"
              >
                🏷️
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden p-4 gap-4">
        {/* Left Panel - Conflicts */}
        <div 
          className="h-full overflow-hidden"
          style={{ width: `${leftPanelWidth}%` }}
        >
          <ConflictPanel
            conflicts={conflicts}
            onConflictSelect={handleConflictSelect}
            onAcceptRecommendation={handleAcceptRecommendation}
            onRejectRecommendation={handleRejectRecommendation}
            selectedConflict={selectedConflict}
          />
        </div>

        {/* Center Panel - Network Map */}
        <div className="flex-1 h-full overflow-hidden">
          <NetworkMap
            network={networkGraph}
            config={config}
            onTrainClick={handleTrainClick}
            onSectionClick={handleSectionClick}
            selectedTrain={selectedTrain}
            selectedSection={selectedSection}
          />

          {/* Error Display */}
          {error && (
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-red-600 text-white px-6 py-3 rounded-lg shadow-lg">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="font-medium">{error}</span>
              </div>
            </div>
          )}
        </div>

        {/* Right Panel - Control Panel */}
        <div 
          className="h-full overflow-hidden"
          style={{ width: `${rightPanelWidth}%` }}
        >
          <ControlPanel
            systemStatus={displaySystemStatus}
            onEmergencyStop={handleEmergencyStop}
            onTestScenario={handleTestScenario}
            onCommunication={handleCommunication}
          />
        </div>
      </div>

      {/* Train Details Modal */}
      {trainModalOpen && selectedTrainData && (
        <TrainDetailsModal
          train={selectedTrainData}
          history={trainHistory}
          onClose={() => {
            setTrainModalOpen(false);
            setSelectedTrain(undefined);
          }}
          onControlAction={handleControlAction}
        />
      )}

      {/* Bottom Status Bar */}
      <div className="bg-gray-800 text-white px-6 py-2 flex items-center justify-between text-xs">
        <div className="flex items-center gap-4">
          <span>System Load: {displaySystemStatus.systemLoad}%</span>
          <span>Avg Delay: {displaySystemStatus.averageDelay.toFixed(1)} min</span>
          <span>FPS: {displaySystemStatus.performance.fps}</span>
        </div>
        <div className="flex items-center gap-4">
          <span>Last Update: {new Date(displaySystemStatus.timestamp).toLocaleTimeString()}</span>
          <span className={displaySystemStatus.operational ? 'text-green-400' : 'text-red-400'}>
            {displaySystemStatus.operational ? '● Operational' : '● System Issues'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default Visualization;
