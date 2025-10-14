/**
 * ConflictPanel Component
 * Displays active conflicts with AI recommendations and resolution actions
 */

import React, { useMemo, useState } from 'react';
import { useCountdown } from '../../hooks/useAnimation';
import {
  Conflict,
  AIRecommendation,
  ConflictPanelProps,
} from '../../types/visualization';

const SEVERITY_COLORS = {
  LOW: 'bg-blue-100 text-blue-800 border-blue-300',
  MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  HIGH: 'bg-orange-100 text-orange-800 border-orange-300',
  CRITICAL: 'bg-red-100 text-red-800 border-red-300',
};

const SEVERITY_ICONS = {
  LOW: '⚠️',
  MEDIUM: '⚠️',
  HIGH: '🚨',
  CRITICAL: '🚨',
};

interface ConflictCardProps {
  conflict: Conflict;
  isSelected: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onToggleExpand: () => void;
  onAcceptRecommendation?: (recommendationId: string) => void;
  onRejectRecommendation?: (recommendationId: string) => void;
}

const ConflictCard: React.FC<ConflictCardProps> = ({
  conflict,
  isSelected,
  isExpanded,
  onSelect,
  onToggleExpand,
  onAcceptRecommendation,
  onRejectRecommendation,
}) => {
  const { formatted: timeToImpact } = useCountdown(conflict.timeToImpact);
  const severityClass = SEVERITY_COLORS[conflict.severity];

  return (
    <div
      className={`border-2 rounded-lg p-4 mb-3 cursor-pointer transition-all ${
        isSelected ? 'border-blue-500 shadow-lg' : 'border-gray-200'
      } ${isExpanded ? 'bg-white' : 'bg-gray-50'} hover:shadow-md`}
      onClick={onSelect}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{SEVERITY_ICONS[conflict.severity]}</span>
          <div>
            <h3 className="font-semibold text-gray-900">{conflict.type.replace(/_/g, ' ')}</h3>
            <p className="text-xs text-gray-500">ID: {conflict.id.substring(0, 8)}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${severityClass}`}>
            {conflict.severity}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand();
            }}
            className="p-1 hover:bg-gray-200 rounded"
          >
            {isExpanded ? '▼' : '▶'}
          </button>
        </div>
      </div>

      {/* Time to Impact */}
      <div className="flex items-center gap-2 mb-2">
        <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className={`text-sm font-mono ${
          conflict.timeToImpact < 60 ? 'text-red-600 font-bold' : 'text-gray-700'
        }`}>
          Impact in: {timeToImpact}
        </span>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-700 mb-2">{conflict.description}</p>

      {/* Trains Involved */}
      <div className="flex flex-wrap gap-2 mb-2">
        {conflict.trains.map(trainId => (
          <span key={trainId} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
            🚂 {trainId}
          </span>
        ))}
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          {/* Affected Sections */}
          <div className="mb-3">
            <h4 className="text-xs font-semibold text-gray-600 mb-1">Affected Sections:</h4>
            <div className="flex flex-wrap gap-1">
              {conflict.sections.map(sectionId => (
                <span key={sectionId} className="px-2 py-1 bg-gray-200 text-gray-700 text-xs rounded">
                  {sectionId}
                </span>
              ))}
            </div>
          </div>

          {/* Status */}
          <div className="mb-3">
            <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
              conflict.status === 'DETECTED' ? 'bg-yellow-100 text-yellow-800' :
              conflict.status === 'RESOLVING' ? 'bg-blue-100 text-blue-800' :
              conflict.status === 'RESOLVED' ? 'bg-green-100 text-green-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              Status: {conflict.status}
            </span>
          </div>

          {/* AI Recommendation */}
          {conflict.aiRecommendation && (
            <AIRecommendationCard
              recommendation={conflict.aiRecommendation}
              onAccept={() => onAcceptRecommendation?.(conflict.aiRecommendation!.id)}
              onReject={() => onRejectRecommendation?.(conflict.aiRecommendation!.id)}
            />
          )}

          {/* Resolution Info */}
          {conflict.resolution && (
            <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded">
              <h4 className="text-xs font-semibold text-green-800 mb-1">✓ Resolution</h4>
              <p className="text-xs text-green-700">
                Method: {conflict.resolution.method}
              </p>
              <p className="text-xs text-green-700">
                Effectiveness: {(conflict.resolution.effectiveness * 100).toFixed(0)}%
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

interface AIRecommendationCardProps {
  recommendation: AIRecommendation;
  onAccept: () => void;
  onReject: () => void;
}

const AIRecommendationCard: React.FC<AIRecommendationCardProps> = ({
  recommendation,
  onAccept,
  onReject,
}) => {
  const isPending = recommendation.status === 'PENDING';

  return (
    <div className="mt-3 p-4 bg-blue-50 border-2 border-blue-300 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        <h4 className="font-semibold text-blue-900">AI Recommendation</h4>
        <span className="ml-auto text-xs font-medium text-blue-700">
          Confidence: {(recommendation.confidence * 100).toFixed(0)}%
        </span>
      </div>

      <p className="text-sm text-blue-800 mb-3">{recommendation.explanation}</p>

      <div className="mb-3">
        <h5 className="text-xs font-semibold text-blue-700 mb-1">Recommended Actions:</h5>
        <ul className="space-y-1">
          {recommendation.actions.map((action, idx) => (
            <li key={action.id} className="text-xs text-blue-700 flex items-start gap-2">
              <span className="font-mono text-blue-500">{idx + 1}.</span>
              <span>
                {action.action} for Train {action.trainId}
                {action.mandatory && <span className="ml-1 text-red-600 font-bold">*Required</span>}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* Impact Analysis */}
      <div className="mb-3 grid grid-cols-2 gap-2 text-xs">
        <div className="p-2 bg-white rounded">
          <span className="text-gray-600">Est. Resolution:</span>
          <span className="ml-1 font-semibold">{Math.round(recommendation.estimatedResolutionTime / 60)}m</span>
        </div>
        <div className="p-2 bg-white rounded">
          <span className="text-gray-600">Safety Score:</span>
          <span className="ml-1 font-semibold text-green-600">{recommendation.impactAnalysis.safetyScore}/100</span>
        </div>
        <div className="p-2 bg-white rounded">
          <span className="text-gray-600">Affected Trains:</span>
          <span className="ml-1 font-semibold">{recommendation.impactAnalysis.affectedTrains.length}</span>
        </div>
        <div className="p-2 bg-white rounded">
          <span className="text-gray-600">Efficiency:</span>
          <span className="ml-1 font-semibold text-blue-600">{recommendation.impactAnalysis.efficiencyScore}/100</span>
        </div>
      </div>

      {/* Alternative Routes */}
      {recommendation.alternativeRoutes && recommendation.alternativeRoutes.length > 0 && (
        <div className="mb-3">
          <h5 className="text-xs font-semibold text-blue-700 mb-1">Alternative Routes:</h5>
          {recommendation.alternativeRoutes.map((route, idx) => (
            <div key={route.id} className="text-xs p-2 bg-white rounded mb-1">
              <span className="font-semibold">Route {idx + 1}:</span>
              <span className="ml-2">+{route.delay}min</span>
              <span className="ml-2">{route.distance.toFixed(1)}km</span>
              {route.conflictFree && <span className="ml-2 text-green-600">✓ Conflict-free</span>}
            </div>
          ))}
        </div>
      )}

      {/* Action Buttons */}
      {isPending && (
        <div className="flex gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAccept();
            }}
            className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium text-sm"
          >
            ✓ Accept
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onReject();
            }}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium text-sm"
          >
            ✗ Reject
          </button>
        </div>
      )}

      {!isPending && (
        <div className={`text-center py-2 rounded font-medium text-sm ${
          recommendation.status === 'ACCEPTED' ? 'bg-green-200 text-green-800' :
          recommendation.status === 'REJECTED' ? 'bg-red-200 text-red-800' :
          'bg-yellow-200 text-yellow-800'
        }`}>
          {recommendation.status}
        </div>
      )}
    </div>
  );
};

export const ConflictPanel: React.FC<ConflictPanelProps> = ({
  conflicts,
  onConflictSelect,
  onAcceptRecommendation,
  onRejectRecommendation,
  selectedConflict,
}) => {
  const [expandedConflicts, setExpandedConflicts] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<'ALL' | Conflict['severity']>('ALL');
  const [sortBy, setSortBy] = useState<'SEVERITY' | 'TIME' | 'STATUS'>('SEVERITY');

  // Sort and filter conflicts
  const processedConflicts = useMemo(() => {
    let filtered = filter === 'ALL' 
      ? conflicts 
      : conflicts.filter(c => c.severity === filter);

    // Sort
    return filtered.sort((a, b) => {
      switch (sortBy) {
        case 'SEVERITY':
          const severityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
          return severityOrder[a.severity] - severityOrder[b.severity];
        case 'TIME':
          return a.timeToImpact - b.timeToImpact;
        case 'STATUS':
          const statusOrder = { DETECTED: 0, ACKNOWLEDGED: 1, RESOLVING: 2, RESOLVED: 3, ESCALATED: 4 };
          return statusOrder[a.status] - statusOrder[b.status];
        default:
          return 0;
      }
    });
  }, [conflicts, filter, sortBy]);

  const toggleExpand = (conflictId: string) => {
    setExpandedConflicts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(conflictId)) {
        newSet.delete(conflictId);
      } else {
        newSet.add(conflictId);
      }
      return newSet;
    });
  };

  const conflictCounts = useMemo(() => {
    return {
      total: conflicts.length,
      critical: conflicts.filter(c => c.severity === 'CRITICAL').length,
      high: conflicts.filter(c => c.severity === 'HIGH').length,
      medium: conflicts.filter(c => c.severity === 'MEDIUM').length,
      low: conflicts.filter(c => c.severity === 'LOW').length,
    };
  }, [conflicts]);

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg border border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-xl font-bold text-gray-900 mb-3">Active Conflicts</h2>
        
        {/* Statistics */}
        <div className="grid grid-cols-5 gap-2 mb-3">
          <div className="text-center p-2 bg-gray-100 rounded">
            <div className="text-lg font-bold text-gray-900">{conflictCounts.total}</div>
            <div className="text-xs text-gray-600">Total</div>
          </div>
          <div className="text-center p-2 bg-red-100 rounded">
            <div className="text-lg font-bold text-red-800">{conflictCounts.critical}</div>
            <div className="text-xs text-red-600">Critical</div>
          </div>
          <div className="text-center p-2 bg-orange-100 rounded">
            <div className="text-lg font-bold text-orange-800">{conflictCounts.high}</div>
            <div className="text-xs text-orange-600">High</div>
          </div>
          <div className="text-center p-2 bg-yellow-100 rounded">
            <div className="text-lg font-bold text-yellow-800">{conflictCounts.medium}</div>
            <div className="text-xs text-yellow-600">Medium</div>
          </div>
          <div className="text-center p-2 bg-blue-100 rounded">
            <div className="text-lg font-bold text-blue-800">{conflictCounts.low}</div>
            <div className="text-xs text-blue-600">Low</div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-2 mb-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="SEVERITY">Sort by Severity</option>
            <option value="TIME">Sort by Time</option>
            <option value="STATUS">Sort by Status</option>
          </select>
        </div>
      </div>

      {/* Conflict List */}
      <div className="flex-1 overflow-y-auto p-4">
        {processedConflicts.length === 0 ? (
          <div className="text-center py-12">
            <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-gray-500 font-medium">No conflicts detected</p>
            <p className="text-gray-400 text-sm mt-1">All systems operating normally</p>
          </div>
        ) : (
          processedConflicts.map(conflict => (
            <ConflictCard
              key={conflict.id}
              conflict={conflict}
              isSelected={selectedConflict === conflict.id}
              isExpanded={expandedConflicts.has(conflict.id)}
              onSelect={() => onConflictSelect?.(conflict)}
              onToggleExpand={() => toggleExpand(conflict.id)}
              onAcceptRecommendation={onAcceptRecommendation}
              onRejectRecommendation={onRejectRecommendation}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default ConflictPanel;
