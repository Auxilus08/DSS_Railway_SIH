/**
 * Custom Hook for D3.js Integration
 * Provides lifecycle management for D3 visualizations in React
 */

import { useEffect, useRef, DependencyList } from 'react';
import * as d3 from 'd3';

export type D3Selection = d3.Selection<SVGElement, unknown, null, undefined>;

/**
 * Hook for integrating D3 with React components
 * Handles the rendering lifecycle and provides a stable D3 selection
 */
export function useD3<T extends SVGElement>(
  renderFn: (selection: d3.Selection<T, unknown, null, undefined>) => void,
  dependencies: DependencyList = []
) {
  const ref = useRef<T>(null);

  useEffect(() => {
    if (ref.current) {
      const selection = d3.select(ref.current);
      renderFn(selection);
    }
  }, dependencies);

  return ref;
}

/**
 * Hook for creating zoom behavior on SVG elements
 */
export function useD3Zoom<T extends SVGElement>(
  onZoom: (transform: d3.ZoomTransform) => void,
  config: {
    minZoom?: number;
    maxZoom?: number;
    initialZoom?: number;
  } = {}
) {
  const ref = useRef<T>(null);
  const zoomBehavior = useRef<d3.ZoomBehavior<T, unknown>>();

  useEffect(() => {
    if (!ref.current) return;

    const { minZoom = 0.5, maxZoom = 10, initialZoom = 1 } = config;

    const zoom = d3.zoom<T, unknown>()
      .scaleExtent([minZoom, maxZoom])
      .on('zoom', (event: d3.D3ZoomEvent<T, unknown>) => {
        onZoom(event.transform);
      });

    zoomBehavior.current = zoom;

    const selection = d3.select(ref.current);
    selection.call(zoom);

    // Set initial zoom
    if (initialZoom !== 1) {
      selection.call(
        zoom.transform,
        d3.zoomIdentity.scale(initialZoom)
      );
    }

    return () => {
      selection.on('.zoom', null);
    };
  }, [onZoom, config.minZoom, config.maxZoom, config.initialZoom]);

  const resetZoom = () => {
    if (ref.current && zoomBehavior.current) {
      d3.select(ref.current)
        .transition()
        .duration(750)
        .call(zoomBehavior.current.transform, d3.zoomIdentity);
    }
  };

  const zoomTo = (scale: number, center?: [number, number]) => {
    if (ref.current && zoomBehavior.current) {
      const selection = d3.select(ref.current);
      if (center) {
        const transform = d3.zoomIdentity
          .translate(center[0], center[1])
          .scale(scale)
          .translate(-center[0], -center[1]);
        selection.transition().duration(750).call(zoomBehavior.current.transform, transform);
      } else {
        selection.transition().duration(750).call(zoomBehavior.current.scaleTo, scale);
      }
    }
  };

  return { ref, resetZoom, zoomTo };
}

/**
 * Hook for managing D3 scales
 */
export function useD3Scale(
  type: 'linear' | 'time',
  domain: number[] | Date[],
  range: number[]
) {
  return useRef(() => {
    switch (type) {
      case 'linear':
        return d3.scaleLinear().domain(domain as number[]).range(range);
      case 'time':
        return d3.scaleTime().domain(domain as Date[]).range(range);
      default:
        return d3.scaleLinear().domain(domain as number[]).range(range);
    }
  }).current();
}

/**
 * Hook for creating geographic projections
 */
export function useD3Projection(
  type: 'mercator' | 'albers' | 'equirectangular' = 'mercator',
  config?: {
    center?: [number, number];
    scale?: number;
    translate?: [number, number];
  }
) {
  return useRef(() => {
    let projection: d3.GeoProjection;

    switch (type) {
      case 'mercator':
        projection = d3.geoMercator();
        break;
      case 'albers':
        projection = d3.geoAlbers();
        break;
      case 'equirectangular':
        projection = d3.geoEquirectangular();
        break;
      default:
        projection = d3.geoMercator();
    }

    if (config?.center) projection.center(config.center);
    if (config?.scale) projection.scale(config.scale);
    if (config?.translate) projection.translate(config.translate);

    return projection;
  }).current();
}

/**
 * Hook for D3 line generators
 */
export function useD3Line<T>(
  xAccessor: (d: T) => number,
  yAccessor: (d: T) => number,
  curve: d3.CurveFactory = d3.curveLinear
) {
  return useRef(
    d3.line<T>()
      .x(xAccessor)
      .y(yAccessor)
      .curve(curve)
  ).current;
}

/**
 * Hook for managing D3 transitions
 */
export function useD3Transition(duration: number = 300) {
  return useRef(() => d3.transition().duration(duration)).current;
}

/**
 * Hook for D3 color scales
 */
export function useD3ColorScale(
  scheme: 'category10' | 'tableau10' | 'set3' | 'interpolateRdYlGn' = 'category10'
) {
  return useRef(() => {
    switch (scheme) {
      case 'category10':
        return d3.scaleOrdinal(d3.schemeCategory10);
      case 'tableau10':
        return d3.scaleOrdinal(d3.schemeTableau10);
      case 'set3':
        return d3.scaleOrdinal(d3.schemeSet3);
      case 'interpolateRdYlGn':
        return d3.scaleSequential(d3.interpolateRdYlGn);
      default:
        return d3.scaleOrdinal(d3.schemeCategory10);
    }
  }).current();
}

/**
 * Hook for force simulation
 */
export function useD3ForceSimulation<NodeType extends d3.SimulationNodeDatum>(
  nodes: NodeType[],
  config?: {
    charge?: number;
    linkDistance?: number;
    centerStrength?: number;
  }
) {
  const simulationRef = useRef<d3.Simulation<NodeType, undefined>>();

  useEffect(() => {
    const { charge = -30, linkDistance = 30, centerStrength = 1 } = config || {};

    const simulation = d3.forceSimulation<NodeType>(nodes)
      .force('charge', d3.forceManyBody().strength(charge))
      .force('center', d3.forceCenter(0, 0).strength(centerStrength))
      .force('collision', d3.forceCollide().radius(10));

    simulationRef.current = simulation;

    return () => {
      simulation.stop();
    };
  }, [nodes, config?.charge, config?.linkDistance, config?.centerStrength]);

  return simulationRef.current;
}

export default useD3;
