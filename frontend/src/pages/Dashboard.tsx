import React, { useEffect, useState } from 'react';
import { useTrains, useSections, useConflicts, usePerformanceMetrics } from '../hooks/useApi';
import { Train, Section, Conflict, PerformanceMetrics } from '../types';

const Dashboard: React.FC = () => {
  const { data: trains, loading: trainsLoading, error: trainsError, execute: fetchTrains } = useTrains();
  const { data: sections, loading: sectionsLoading, error: sectionsError, execute: fetchSections } = useSections();
  const { data: conflicts, loading: conflictsLoading, error: conflictsError, execute: fetchConflicts } = useConflicts(24);
  const { data: metrics, loading: metricsLoading, error: metricsError, execute: fetchMetrics } = usePerformanceMetrics();
  
  const [initialLoad, setInitialLoad] = useState(true);

  useEffect(() => {
    // Fetch initial data with error handling
    const loadData = async () => {
      try {
        await Promise.allSettled([
          fetchTrains(),
          fetchSections(),
          fetchConflicts(),
          fetchMetrics()
        ]);
      } catch (error) {
        console.error('Error loading dashboard data:', error);
      } finally {
        setInitialLoad(false);
      }
    };

    loadData();

    // Set up periodic refresh
    const interval = setInterval(() => {
      fetchTrains().catch(err => console.error('Error fetching trains:', err));
      fetchSections().catch(err => console.error('Error fetching sections:', err));
      fetchConflicts().catch(err => console.error('Error fetching conflicts:', err));
      fetchMetrics().catch(err => console.error('Error fetching metrics:', err));
    }, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, []);

  // Show loading state on initial load
  if (initialLoad && (trainsLoading || sectionsLoading || conflictsLoading || metricsLoading)) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading dashboard data...</p>
        </div>
      </div>
    );
  }

  const getTrainTypeCount = (type: string) => {
    return trains?.filter((t: Train) => t.type === type).length || 0;
  };

  const getActiveTrainsCount = () => {
    return trains?.filter((t: Train) => t.operational_status === 'ACTIVE').length || 0;
  };

  const getCriticalConflictsCount = () => {
    return conflicts?.filter((c: Conflict) => (c.severity === 'CRITICAL' || c.severity === 'HIGH') && !c.resolution_time).length || 0;
  };

  const getOccupiedSectionsCount = () => {
    return sections?.filter((s: Section) => s.active).length || 0;
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Traffic Control Dashboard
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Real-time railway traffic monitoring and management
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {/* Active Trains */}
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-green-600 dark:text-green-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Active Trains
                  </dt>
                  <dd className="flex items-baseline">
                    <div className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {trainsLoading ? '...' : getActiveTrainsCount()}
                    </div>
                    <div className="ml-2 text-sm text-gray-500 dark:text-gray-400">
                      / {trains?.length || 0}
                    </div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* Conflicts */}
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-red-600 dark:text-red-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Critical Conflicts
                  </dt>
                  <dd className="flex items-baseline">
                    <div className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {conflictsLoading ? '...' : getCriticalConflictsCount()}
                    </div>
                    <div className="ml-2 text-sm text-gray-500 dark:text-gray-400">
                      active
                    </div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* Sections */}
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-blue-600 dark:text-blue-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                  />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Active Sections
                  </dt>
                  <dd className="flex items-baseline">
                    <div className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {sectionsLoading ? '...' : getOccupiedSectionsCount()}
                    </div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* Performance */}
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-purple-600 dark:text-purple-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    System Response
                  </dt>
                  <dd className="flex items-baseline">
                    <div className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {metricsLoading ? '...' : `${metrics?.average_response_time_ms?.toFixed(0) || 0}ms`}
                    </div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Conflicts */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Recent Conflicts
            </h3>
            <div className="space-y-3">
              {conflictsLoading ? (
                <p className="text-gray-500 dark:text-gray-400">Loading...</p>
              ) : conflicts && conflicts.length > 0 ? (
                conflicts.slice(0, 5).map((conflict: Conflict) => (
                  <div
                    key={conflict.id}
                    className="flex items-start p-3 bg-gray-50 dark:bg-gray-700 rounded-md"
                  >
                    <div className="flex-shrink-0">
                      <span
                        className={`inline-block h-2 w-2 rounded-full ${
                          conflict.severity === 'CRITICAL'
                            ? 'bg-red-600'
                            : conflict.severity === 'HIGH'
                            ? 'bg-orange-500'
                            : conflict.severity === 'MEDIUM'
                            ? 'bg-yellow-500'
                            : 'bg-blue-500'
                        }`}
                      ></span>
                    </div>
                    <div className="ml-3 flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {conflict.conflict_type.replace('_', ' ')}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {conflict.description}
                      </p>
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                        {new Date(conflict.detection_time).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                  No recent conflicts
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Train Types Distribution */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Train Types Distribution
            </h3>
            <div className="space-y-4">
              {['EXPRESS', 'LOCAL', 'FREIGHT', 'MAINTENANCE'].map((type) => {
                const count = getTrainTypeCount(type);
                const percentage = trains ? (count / trains.length) * 100 : 0;
                return (
                  <div key={type}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {type}
                      </span>
                      <span className="text-sm text-gray-500 dark:text-gray-400">{count}</span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          type === 'EXPRESS'
                            ? 'bg-blue-600'
                            : type === 'LOCAL'
                            ? 'bg-green-600'
                            : type === 'FREIGHT'
                            ? 'bg-yellow-600'
                            : 'bg-gray-600'
                        }`}
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* System Performance Metrics */}
      {metrics && (
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              System Performance
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Position Updates/min</p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {metrics.position_updates_per_minute || 0}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Cache Hit Rate</p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {(metrics.cache_hit_rate * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Active WS Connections</p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {metrics.active_websocket_connections || 0}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">DB Connections</p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {metrics.database_connections || 0}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
