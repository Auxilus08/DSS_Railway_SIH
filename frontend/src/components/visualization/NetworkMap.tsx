/**
 * NetworkMap Component
 * SVG-based railway network visualization with D3.js
 * Features: zoom, pan, real-time train positions, section status
 */

import React, { useEffect, useRef, useMemo, useCallback } from 'react';
import * as d3 from 'd3';
import { useD3Zoom } from '../../hooks/useD3';
import { useTrainAnimation } from '../../hooks/useAnimation';
import {
  NetworkMapProps,
  Train,
  Section,
  Station,
  Position,
  SectionStatus,
  TrainStatus,
} from '../../types/visualization';

const COLORS = {
  sections: {
    CLEAR: '#10b981', // green
    OCCUPIED: '#f59e0b', // yellow/orange
    CONFLICT: '#ef4444', // red
    MAINTENANCE: '#6b7280', // gray
    BLOCKED: '#991b1b', // dark red
  },
  trains: {
    RUNNING: '#3b82f6', // blue
    STOPPED: '#ef4444', // red
    DELAYED: '#f59e0b', // orange
    EMERGENCY: '#dc2626', // red
    MAINTENANCE: '#6b7280', // gray
  },
  ai: '#60a5fa', // blue for AI recommendations
  controller: {
    accepted: '#10b981', // green
    modified: '#f59e0b', // yellow
  },
  station: '#8b5cf6', // purple
  junction: '#ec4899', // pink
};

export const NetworkMap: React.FC<NetworkMapProps> = ({
  network,
  config,
  onTrainClick,
  onSectionClick,
  onStationClick,
  selectedTrain,
  selectedSection,
}) => {
  const gRef = useRef<SVGGElement>(null);
  const animatedPositions = useTrainAnimation(network.trains, config.animation.fps);

  // Calculate bounds from network data
  const bounds = useMemo(() => {
    let minLat = Infinity, maxLat = -Infinity;
    let minLon = Infinity, maxLon = -Infinity;

    network.sections.forEach(section => {
      section.coordinates.forEach(coord => {
        minLat = Math.min(minLat, coord.latitude);
        maxLat = Math.max(maxLat, coord.latitude);
        minLon = Math.min(minLon, coord.longitude);
        maxLon = Math.max(maxLon, coord.longitude);
      });
    });

    network.trains.forEach(train => {
      minLat = Math.min(minLat, train.position.latitude);
      maxLat = Math.max(maxLat, train.position.latitude);
      minLon = Math.min(minLon, train.position.longitude);
      maxLon = Math.max(maxLon, train.position.longitude);
    });

    return { minLat, maxLat, minLon, maxLon };
  }, [network]);

  // Create projection for converting lat/lon to SVG coordinates
  const projection = useMemo(() => {
    return d3.geoMercator()
      .center([(bounds.minLon + bounds.maxLon) / 2, (bounds.minLat + bounds.maxLat) / 2])
      .scale(100000)
      .translate([config.width / 2, config.height / 2]);
  }, [bounds, config.width, config.height]);

  // Line generator for sections
  const lineGenerator = useMemo(() => {
    return d3.line<Position>()
      .x(d => projection([d.longitude, d.latitude])![0])
      .y(d => projection([d.longitude, d.latitude])![1])
      .curve(d3.curveCatmullRom.alpha(0.5));
  }, [projection]);

  // Zoom handler
  const handleZoom = useCallback((transform: d3.ZoomTransform) => {
    if (gRef.current) {
      d3.select(gRef.current)
        .attr('transform', transform.toString());
    }
  }, []);

  const { ref: zoomRef, resetZoom, zoomTo } = useD3Zoom<SVGSVGElement>(
    handleZoom,
    {
      minZoom: config.zoom.min,
      maxZoom: config.zoom.max,
      initialZoom: config.zoom.initial,
    }
  );

  // Render network
  useEffect(() => {
    if (!gRef.current) return;

    const g = d3.select(gRef.current);

    // Clear existing content
    g.selectAll('*').remove();

    // Create layers
    const sectionsLayer = g.append('g').attr('class', 'sections-layer');
    const stationsLayer = g.append('g').attr('class', 'stations-layer');
    const trainsLayer = g.append('g').attr('class', 'trains-layer');
    const labelsLayer = g.append('g').attr('class', 'labels-layer');

    // Render sections
    if (config.layers.network) {
      const sections = sectionsLayer
        .selectAll<SVGPathElement, Section>('path.section')
        .data(network.sections, d => d.id)
        .join('path')
        .attr('class', 'section')
        .attr('d', d => lineGenerator(d.coordinates) || '')
        .attr('stroke', d => COLORS.sections[d.status])
        .attr('stroke-width', d => selectedSection === d.id ? 6 : 4)
        .attr('fill', 'none')
        .attr('stroke-linecap', 'round')
        .attr('opacity', 0.8)
        .style('cursor', 'pointer')
        .on('click', (event, d) => {
          event.stopPropagation();
          onSectionClick?.(d);
        })
        .on('mouseenter', function() {
          d3.select(this)
            .attr('stroke-width', 6)
            .attr('opacity', 1);
        })
        .on('mouseleave', function(event, d) {
          if (selectedSection !== d.id) {
            d3.select(this)
              .attr('stroke-width', 4)
              .attr('opacity', 0.8);
          }
        });

      // Add section status indicators (pulsing for conflicts)
      sections
        .filter(d => d.status === 'CONFLICT')
        .each(function() {
          d3.select(this)
            .transition()
            .duration(500)
            .attr('opacity', 0.4)
            .transition()
            .duration(500)
            .attr('opacity', 1)
            .on('end', function repeat() {
              d3.select(this)
                .transition()
                .duration(500)
                .attr('opacity', 0.4)
                .transition()
                .duration(500)
                .attr('opacity', 1)
                .on('end', repeat);
            });
        });
    }

    // Render stations
    if (config.layers.network) {
      const stations = stationsLayer
        .selectAll<SVGCircleElement, Station>('circle.station')
        .data(network.stations, d => d.id)
        .join('circle')
        .attr('class', 'station')
        .attr('cx', d => projection([d.position.longitude, d.position.latitude])![0])
        .attr('cy', d => projection([d.position.longitude, d.position.latitude])![1])
        .attr('r', d => d.type === 'JUNCTION' ? 8 : 6)
        .attr('fill', d => d.type === 'JUNCTION' ? COLORS.junction : COLORS.station)
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .style('cursor', 'pointer')
        .on('click', (event, d) => {
          event.stopPropagation();
          onStationClick?.(d);
        })
        .on('mouseenter', function() {
          d3.select(this).attr('r', 10);
        })
        .on('mouseleave', function(event, d) {
          d3.select(this).attr('r', d.type === 'JUNCTION' ? 8 : 6);
        });

      // Station labels
      if (config.layers.labels) {
        labelsLayer
          .selectAll<SVGTextElement, Station>('text.station-label')
          .data(network.stations, d => d.id)
          .join('text')
          .attr('class', 'station-label')
          .attr('x', d => projection([d.position.longitude, d.position.latitude])![0] + 10)
          .attr('y', d => projection([d.position.longitude, d.position.latitude])![1] - 10)
          .attr('font-size', '12px')
          .attr('font-weight', '500')
          .attr('fill', '#1f2937')
          .attr('text-anchor', 'start')
          .style('pointer-events', 'none')
          .text(d => d.name);
      }
    }

    // Render trains
    if (config.layers.trains) {
      renderTrains(trainsLayer, labelsLayer);
    }

  }, [network, config, projection, lineGenerator, selectedSection, onSectionClick, onStationClick]);

  // Update train positions separately for smooth animation
  const renderTrains = useCallback((trainsLayer: d3.Selection<SVGGElement, unknown, null, undefined>, labelsLayer: d3.Selection<SVGGElement, unknown, null, undefined>) => {
    // Render trains with animated positions
    const trainGroup = trainsLayer
      .selectAll<SVGGElement, Train>('g.train')
      .data(network.trains, d => d.id)
      .join(
        enter => {
          const g = enter.append('g')
            .attr('class', 'train')
            .style('cursor', 'pointer');

          // Train icon (triangle pointing in heading direction)
          g.append('path')
            .attr('class', 'train-icon')
            .attr('d', 'M 0,-10 L 5,10 L -5,10 Z') // Triangle
            .attr('fill', d => COLORS.trains[d.status])
            .attr('stroke', '#fff')
            .attr('stroke-width', 1.5);

          // Speed indicator (circle)
          g.append('circle')
            .attr('class', 'speed-indicator')
            .attr('r', 3)
            .attr('cx', 0)
            .attr('cy', -15)
            .attr('fill', '#10b981')
            .attr('opacity', 0);

          return g;
        },
        update => update,
        exit => exit
          .transition()
          .duration(300)
          .attr('opacity', 0)
          .remove()
      );

    // Update positions with animation
    trainGroup
      .transition()
      .duration(1000 / config.animation.fps)
      .ease(d3.easeLinear)
      .attr('transform', d => {
        const pos = animatedPositions.get(d.id) || d.position;
        const coords = projection([pos.longitude, pos.latitude]);
        return coords ? `translate(${coords[0]},${coords[1]}) rotate(${d.heading})` : '';
      })
      .attr('opacity', 1);

    // Update train colors based on status
    trainGroup
      .select<SVGPathElement>('.train-icon')
      .attr('fill', d => COLORS.trains[d.status])
      .attr('stroke-width', d => selectedTrain === d.id ? 3 : 1.5);

    // Show speed indicator for moving trains
    trainGroup
      .select<SVGCircleElement>('.speed-indicator')
      .transition()
      .duration(300)
      .attr('opacity', d => d.currentSpeed > 0 ? 0.8 : 0)
      .attr('fill', d => {
        const speedRatio = d.currentSpeed / d.maxSpeed;
        if (speedRatio > 0.8) return '#10b981'; // green
        if (speedRatio > 0.5) return '#f59e0b'; // yellow
        return '#ef4444'; // red
      });

    // Click handler for trains
    trainGroup.on('click', (event, d) => {
      event.stopPropagation();
      onTrainClick?.(d);
    });

    // Hover effects
    trainGroup
      .on('mouseenter', function() {
        d3.select(this)
          .select('.train-icon')
          .attr('stroke-width', 3)
          .transition()
          .duration(200)
          .attr('transform', 'scale(1.3)');
      })
      .on('mouseleave', function(event, d) {
        if (selectedTrain !== d.id) {
          d3.select(this)
            .select('.train-icon')
            .attr('stroke-width', 1.5)
            .transition()
            .duration(200)
            .attr('transform', 'scale(1)');
        }
      });

    // Train labels
    if (config.layers.labels) {
      labelsLayer
        .selectAll<SVGTextElement, Train>('text.train-label')
        .data(network.trains.filter(t => selectedTrain === t.id || t.status === 'EMERGENCY'), d => d.id)
        .join('text')
        .attr('class', 'train-label')
        .attr('x', d => {
          const pos = animatedPositions.get(d.id) || d.position;
          const coords = projection([pos.longitude, pos.latitude]);
          return coords ? coords[0] + 15 : 0;
        })
        .attr('y', d => {
          const pos = animatedPositions.get(d.id) || d.position;
          const coords = projection([pos.longitude, pos.latitude]);
          return coords ? coords[1] - 15 : 0;
        })
        .attr('font-size', '11px')
        .attr('font-weight', '600')
        .attr('fill', '#1f2937')
        .attr('text-anchor', 'start')
        .style('pointer-events', 'none')
        .text(d => `${d.trainNumber} (${d.currentSpeed} km/h)`);
    }

  }, [network.trains, animatedPositions, projection, config, selectedTrain, onTrainClick]);

  // Update trains on position change
  useEffect(() => {
    if (!gRef.current) return;
    const g = d3.select(gRef.current);
    const trainsLayer = g.select<SVGGElement>('.trains-layer');
    const labelsLayer = g.select<SVGGElement>('.labels-layer');
    
    if (trainsLayer.empty() || labelsLayer.empty()) return;
    renderTrains(trainsLayer, labelsLayer);
  }, [animatedPositions, renderTrains]);

  return (
    <div 
      className="relative w-full h-full bg-gray-50 rounded-lg overflow-hidden shadow-lg border border-gray-200"
    >
      {/* Controls */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
        <button
          onClick={resetZoom}
          className="px-3 py-2 bg-white rounded-lg shadow-md hover:bg-gray-50 transition-colors border border-gray-200"
          title="Reset Zoom"
        >
          <svg className="w-5 h-5 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
        
        <button
          onClick={() => zoomTo(config.zoom.initial)}
          className="px-3 py-2 bg-white rounded-lg shadow-md hover:bg-gray-50 transition-colors border border-gray-200 text-sm font-medium text-gray-700"
          title="Reset View"
        >
          Reset
        </button>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 z-10 bg-white rounded-lg shadow-md p-3 border border-gray-200">
        <h3 className="text-xs font-semibold text-gray-700 mb-2">Legend</h3>
        <div className="space-y-1">
          {Object.entries(COLORS.sections).map(([status, color]) => (
            <div key={status} className="flex items-center gap-2 text-xs">
              <div className="w-4 h-1 rounded" style={{ backgroundColor: color }} />
              <span className="text-gray-600">{status}</span>
            </div>
          ))}
        </div>
      </div>

      {/* SVG Canvas */}
      <svg
        ref={zoomRef}
        width={config.width}
        height={config.height}
        className="w-full h-full"
      >
        <defs>
          {/* Gradient for sections */}
          <linearGradient id="sectionGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={COLORS.sections.CLEAR} />
            <stop offset="100%" stopColor={COLORS.sections.OCCUPIED} />
          </linearGradient>
          
          {/* Filter for glow effect */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        <g ref={gRef} />
      </svg>
    </div>
  );
};

export default NetworkMap;
