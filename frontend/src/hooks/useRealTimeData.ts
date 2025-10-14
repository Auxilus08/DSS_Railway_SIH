/**
 * Custom Hook for Real-Time Data Management
 * Integrates with WebSocket for live railway network updates
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import {
  Train,
  Section,
  Conflict,
  AIRecommendation,
  SystemStatus,
  NetworkGraph,
  WSMessage,
  TrainUpdateMessage,
  ConflictMessage,
  SectionStatusMessage,
  AIRecommendationMessage,
} from '../types/visualization';

interface RealTimeDataState {
  trains: Map<string, Train>;
  sections: Map<string, Section>;
  conflicts: Map<string, Conflict>;
  recommendations: Map<string, AIRecommendation>;
  systemStatus: SystemStatus | null;
  lastUpdate: Date;
  isConnected: boolean;
  error: string | null;
}

interface UseRealTimeDataOptions {
  autoConnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  updateThrottle?: number;
}

/**
 * Hook for managing real-time railway network data
 */
export function useRealTimeData(
  wsUrl?: string,
  options: UseRealTimeDataOptions = {}
) {
  const {
    autoConnect = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5,
    updateThrottle = 50,
  } = options;

  const [state, setState] = useState<RealTimeDataState>({
    trains: new Map(),
    sections: new Map(),
    conflicts: new Map(),
    recommendations: new Map(),
    systemStatus: null,
    lastUpdate: new Date(),
    isConnected: false,
    error: null,
  });

  const updateQueue = useRef<WSMessage[]>([]);
  const processingRef = useRef(false);
  const throttleTimerRef = useRef<NodeJS.Timeout>();

  // WebSocket message handler
  const handleMessage = useCallback((message: WSMessage) => {
    updateQueue.current.push(message);
    
    if (!processingRef.current) {
      processingRef.current = true;
      
      if (throttleTimerRef.current) {
        clearTimeout(throttleTimerRef.current);
      }
      
      throttleTimerRef.current = setTimeout(() => {
        processUpdateQueue();
        processingRef.current = false;
      }, updateThrottle);
    }
  }, [updateThrottle]);

  // Process queued updates in batch
  const processUpdateQueue = () => {
    const updates = [...updateQueue.current];
    updateQueue.current = [];

    setState(prevState => {
      const newTrains = new Map(prevState.trains);
      const newSections = new Map(prevState.sections);
      const newConflicts = new Map(prevState.conflicts);
      const newRecommendations = new Map(prevState.recommendations);
      let newSystemStatus = prevState.systemStatus;

      updates.forEach(message => {
        switch (message.type) {
          case 'TRAIN_UPDATE': {
            const { train } = (message as TrainUpdateMessage).payload;
            newTrains.set(train.id, train);
            break;
          }

          case 'SECTION_STATUS': {
            const { section } = (message as SectionStatusMessage).payload;
            newSections.set(section.id, section);
            break;
          }

          case 'CONFLICT_DETECTED': {
            const { conflict } = (message as ConflictMessage).payload;
            newConflicts.set(conflict.id, conflict);
            break;
          }

          case 'CONFLICT_RESOLVED': {
            const { conflict } = (message as ConflictMessage).payload;
            if (conflict.status === 'RESOLVED') {
              newConflicts.delete(conflict.id);
            } else {
              newConflicts.set(conflict.id, conflict);
            }
            break;
          }

          case 'AI_RECOMMENDATION': {
            const { recommendation } = (message as AIRecommendationMessage).payload;
            newRecommendations.set(recommendation.id, recommendation);
            break;
          }

          case 'SYSTEM_STATUS': {
            newSystemStatus = message.payload as SystemStatus;
            break;
          }

          case 'EMERGENCY': {
            // Handle emergency broadcasts
            console.error('EMERGENCY:', message.payload);
            break;
          }
        }
      });

      return {
        ...prevState,
        trains: newTrains,
        sections: newSections,
        conflicts: newConflicts,
        recommendations: newRecommendations,
        systemStatus: newSystemStatus,
        lastUpdate: new Date(),
      };
    });
  };

  const handleError = useCallback((error: Error) => {
    setState(prev => ({
      ...prev,
      error: error.message,
      isConnected: false,
    }));
  }, []);

  const handleConnect = useCallback(() => {
    setState(prev => ({
      ...prev,
      isConnected: true,
      error: null,
    }));
  }, []);

  const handleDisconnect = useCallback(() => {
    setState(prev => ({
      ...prev,
      isConnected: false,
    }));
  }, []);

  // Use WebSocket hook
  const { sendMessage, disconnect } = useWebSocket({
    autoConnect,
    onMessage: handleMessage as any,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
  });

  // Convert Maps to arrays for easier consumption
  const trains = Array.from(state.trains.values());
  const sections = Array.from(state.sections.values());
  const conflicts = Array.from(state.conflicts.values());
  const recommendations = Array.from(state.recommendations.values());

  // Helper functions
  const getTrainById = useCallback((id: string): Train | undefined => {
    return state.trains.get(id);
  }, [state.trains]);

  const getSectionById = useCallback((id: string): Section | undefined => {
    return state.sections.get(id);
  }, [state.sections]);

  const getConflictById = useCallback((id: string): Conflict | undefined => {
    return state.conflicts.get(id);
  }, [state.conflicts]);

  const getTrainsBySection = useCallback((sectionId: string): Train[] => {
    return trains.filter(train => train.currentSection === sectionId);
  }, [trains]);

  const getActiveConflicts = useCallback((): Conflict[] => {
    return conflicts.filter(c => 
      c.status === 'DETECTED' || c.status === 'ACKNOWLEDGED' || c.status === 'RESOLVING'
    );
  }, [conflicts]);

  const getConflictsBySeverity = useCallback((severity: Conflict['severity']): Conflict[] => {
    return conflicts.filter(c => c.severity === severity);
  }, [conflicts]);

  const getPendingRecommendations = useCallback((): AIRecommendation[] => {
    return recommendations.filter(r => r.status === 'PENDING');
  }, [recommendations]);

  // Network graph data
  const networkGraph: NetworkGraph = {
    stations: [], // Would need to fetch or maintain stations separately
    sections,
    junctions: [], // Would need to fetch or maintain junctions separately
    trains,
    bounds: {
      north: 0,
      south: 0,
      east: 0,
      west: 0,
    },
  };

  // Cleanup
  useEffect(() => {
    return () => {
      if (throttleTimerRef.current) {
        clearTimeout(throttleTimerRef.current);
      }
      disconnect();
    };
  }, [disconnect]);

  return {
    // State
    trains,
    sections,
    conflicts,
    recommendations,
    systemStatus: state.systemStatus,
    networkGraph,
    lastUpdate: state.lastUpdate,
    isConnected: state.isConnected,
    error: state.error,

    // Query functions
    getTrainById,
    getSectionById,
    getConflictById,
    getTrainsBySection,
    getActiveConflicts,
    getConflictsBySeverity,
    getPendingRecommendations,

    // Actions
    sendMessage,
    disconnect,
  };
}

/**
 * Hook for managing data refresh and polling
 */
export function useDataRefresh(
  refreshFn: () => Promise<void>,
  interval: number = 5000
) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout>();

  const refresh = useCallback(async () => {
    try {
      setIsRefreshing(true);
      setError(null);
      await refreshFn();
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Refresh failed');
    } finally {
      setIsRefreshing(false);
    }
  }, [refreshFn]);

  useEffect(() => {
    // Initial refresh
    refresh();

    // Set up interval
    intervalRef.current = setInterval(refresh, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [refresh, interval]);

  return {
    isRefreshing,
    lastRefresh,
    error,
    refresh,
  };
}

/**
 * Hook for managing historical data
 */
export function useHistoricalData<T>(
  maxSize: number = 100
) {
  const [history, setHistory] = useState<T[]>([]);

  const addEntry = useCallback((entry: T) => {
    setHistory(prev => {
      const newHistory = [...prev, entry];
      if (newHistory.length > maxSize) {
        return newHistory.slice(-maxSize);
      }
      return newHistory;
    });
  }, [maxSize]);

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  const getRecent = useCallback((count: number): T[] => {
    return history.slice(-count);
  }, [history]);

  return {
    history,
    addEntry,
    clearHistory,
    getRecent,
  };
}

export default useRealTimeData;
