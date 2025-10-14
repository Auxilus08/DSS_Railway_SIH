import React, { useEffect, useState } from 'react';
import { useSectionStatuses } from '../hooks/useApi';
import { SectionStatus } from '../types';

const Sections: React.FC = () => {
  const { data: sectionStatuses, loading, execute: fetchSections } = useSectionStatuses();
  const [filter, setFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchSections();
    const interval = setInterval(fetchSections, 30000);
    return () => clearInterval(interval);
  }, []);

  const filteredSections = sectionStatuses?.filter((sectionStatus: SectionStatus) => {
    const matchesFilter =
      filter === 'ALL' ||
      sectionStatus.status === filter ||
      sectionStatus.section.section_type === filter;
    const matchesSearch =
      !searchTerm ||
      sectionStatus.section.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      sectionStatus.section.section_code.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'AVAILABLE':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'BUSY':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'FULL':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      case 'MAINTENANCE':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'TRACK':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'JUNCTION':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'STATION':
        return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200';
      case 'YARD':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    }
  };

  const availableSections =
    sectionStatuses?.filter((s: SectionStatus) => s.status === 'AVAILABLE').length || 0;
  const busySections =
    sectionStatuses?.filter((s: SectionStatus) => s.status === 'BUSY').length || 0;
  const fullSections =
    sectionStatuses?.filter((s: SectionStatus) => s.status === 'FULL').length || 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Section Monitoring</h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Track and monitor all railway sections
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-gray-400"
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
                    Total Sections
                  </dt>
                  <dd className="text-lg font-semibold text-gray-900 dark:text-white">
                    {sectionStatuses?.length || 0}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg border border-green-200 dark:border-green-800">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Available
                  </dt>
                  <dd className="text-lg font-semibold text-green-600 dark:text-green-400">
                    {availableSections}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg border border-yellow-200 dark:border-yellow-800">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-yellow-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Busy
                  </dt>
                  <dd className="text-lg font-semibold text-yellow-600 dark:text-yellow-400">
                    {busySections}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg border border-red-200 dark:border-red-800">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">Full</dt>
                  <dd className="text-lg font-semibold text-red-600 dark:text-red-400">
                    {fullSections}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Search */}
          <div className="lg:col-span-2">
            <label htmlFor="search" className="sr-only">
              Search sections
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg
                  className="h-5 w-5 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
              <input
                id="search"
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Search by name or code..."
              />
            </div>
          </div>

          {/* Filter */}
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="block w-full py-2 px-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-gray-900 dark:text-white"
          >
            <option value="ALL">All Sections</option>
            <option value="TRACK">Track</option>
            <option value="JUNCTION">Junction</option>
            <option value="STATION">Station</option>
            <option value="YARD">Yard</option>
            <option value="AVAILABLE">Available Only</option>
            <option value="BUSY">Busy Only</option>
            <option value="FULL">Full Only</option>
          </select>

          {/* Refresh Button */}
          <button
            onClick={() => fetchSections()}
            disabled={loading}
            className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Refreshing...
              </>
            ) : (
              <>
                <svg className="-ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Refresh
              </>
            )}
          </button>
        </div>
      </div>

      {/* Sections Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full text-center text-gray-500 dark:text-gray-400">
            Loading sections...
          </div>
        ) : filteredSections && filteredSections.length > 0 ? (
          filteredSections.map((sectionStatus: SectionStatus) => (
            <div
              key={sectionStatus.section.id}
              className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow"
            >
              <div className="p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                      {sectionStatus.section.name}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {sectionStatus.section.section_code}
                    </p>
                  </div>
                  <div className="flex flex-col space-y-1 items-end">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(
                        sectionStatus.status
                      )}`}
                    >
                      {sectionStatus.status}
                    </span>
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${getTypeColor(
                        sectionStatus.section.section_type
                      )}`}
                    >
                      {sectionStatus.section.section_type}
                    </span>
                  </div>
                </div>

                {/* Section Details */}
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Length</span>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {sectionStatus.section.length_meters}m
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Max Speed</span>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {sectionStatus.section.max_speed_kmh} km/h
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Capacity</span>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {sectionStatus.section.capacity}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Electrified</span>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {sectionStatus.section.electrified ? 'Yes' : 'No'}
                      </p>
                    </div>
                  </div>

                  {/* Occupancy */}
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-500 dark:text-gray-400">Occupancy</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {sectionStatus.current_occupancy} / {sectionStatus.section.capacity} (
                        {sectionStatus.utilization_percentage.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          sectionStatus.utilization_percentage >= 100
                            ? 'bg-red-600'
                            : sectionStatus.utilization_percentage >= 75
                            ? 'bg-yellow-600'
                            : 'bg-green-600'
                        }`}
                        style={{
                          width: `${Math.min(sectionStatus.utilization_percentage, 100)}%`,
                        }}
                      ></div>
                    </div>
                  </div>

                  {/* Trains Present */}
                  {sectionStatus.trains_present.length > 0 && (
                    <div>
                      <span className="text-sm text-gray-500 dark:text-gray-400">Trains Present:</span>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {sectionStatus.trains_present.map((train) => (
                          <span
                            key={train.id}
                            className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded"
                          >
                            {train.train_number}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-full text-center text-gray-500 dark:text-gray-400">
            No sections found
          </div>
        )}
      </div>
    </div>
  );
};

export default Sections;
