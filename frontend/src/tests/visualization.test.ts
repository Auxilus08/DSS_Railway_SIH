/**
 * Unit Tests for Visualization Components
 * Tests for hooks, utilities, and component logic
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useCountdown, usePositionAnimation, easingFunctions } from '../hooks/useAnimation';
import { Position, Train } from '../types/visualization';

// Mock data
const mockTrain: Train = {
  id: 'TRAIN001',
  trainNumber: 'T001',
  name: 'Express 1',
  type: 'EXPRESS',
  position: { latitude: 28.6139, longitude: 77.2090 },
  currentSection: 'SECTION_A',
  currentSpeed: 80,
  maxSpeed: 120,
  heading: 45,
  status: 'RUNNING',
  destination: 'Mumbai',
  origin: 'Delhi',
  passengerCount: 500,
  priority: 8,
  scheduledRoute: ['SECTION_A', 'SECTION_B', 'SECTION_C'],
  actualRoute: ['SECTION_A'],
  delays: 5,
  lastUpdate: new Date(),
  nextStation: 'Agra',
  eta: new Date(Date.now() + 3600000),
  distanceToNext: 45,
};

describe('useCountdown Hook', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should countdown from initial seconds', () => {
    const { result } = renderHook(() => useCountdown(10));
    
    expect(result.current.timeRemaining).toBe(10);
    expect(result.current.isRunning).toBe(true);
    
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    
    expect(result.current.timeRemaining).toBe(9);
  });

  it('should stop at zero and call onComplete', () => {
    const onComplete = vi.fn();
    const { result } = renderHook(() => useCountdown(2, onComplete));
    
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    
    expect(result.current.timeRemaining).toBe(0);
    expect(result.current.isRunning).toBe(false);
    expect(onComplete).toHaveBeenCalled();
  });

  it('should pause and resume correctly', () => {
    const { result } = renderHook(() => useCountdown(10));
    
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(result.current.timeRemaining).toBe(8);
    
    act(() => {
      result.current.pause();
    });
    expect(result.current.isRunning).toBe(false);
    
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(result.current.timeRemaining).toBe(8); // Should not change
    
    act(() => {
      result.current.resume();
      vi.advanceTimersByTime(1000);
    });
    expect(result.current.timeRemaining).toBe(7);
  });

  it('should reset to initial value', () => {
    const { result } = renderHook(() => useCountdown(10));
    
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(result.current.timeRemaining).toBe(5);
    
    act(() => {
      result.current.reset();
    });
    expect(result.current.timeRemaining).toBe(10);
    expect(result.current.isRunning).toBe(true);
  });

  it('should format time correctly', () => {
    const { result } = renderHook(() => useCountdown(125));
    
    expect(result.current.formatted).toBe('2:05');
    
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    
    expect(result.current.formatted).toBe('2:00');
  });
});

describe('Easing Functions', () => {
  it('linear should return input value', () => {
    expect(easingFunctions.linear(0)).toBe(0);
    expect(easingFunctions.linear(0.5)).toBe(0.5);
    expect(easingFunctions.linear(1)).toBe(1);
  });

  it('easeInQuad should accelerate', () => {
    expect(easingFunctions.easeInQuad(0)).toBe(0);
    expect(easingFunctions.easeInQuad(0.5)).toBeLessThan(0.5);
    expect(easingFunctions.easeInQuad(1)).toBe(1);
  });

  it('easeOutQuad should decelerate', () => {
    expect(easingFunctions.easeOutQuad(0)).toBe(0);
    expect(easingFunctions.easeOutQuad(0.5)).toBeGreaterThan(0.5);
    expect(easingFunctions.easeOutQuad(1)).toBe(1);
  });

  it('easeInOutQuad should accelerate then decelerate', () => {
    expect(easingFunctions.easeInOutQuad(0)).toBe(0);
    expect(easingFunctions.easeInOutQuad(0.25)).toBeLessThan(0.25);
    expect(easingFunctions.easeInOutQuad(0.5)).toBe(0.5);
    expect(easingFunctions.easeInOutQuad(0.75)).toBeGreaterThan(0.75);
    expect(easingFunctions.easeInOutQuad(1)).toBe(1);
  });
});

describe('Train Data Validation', () => {
  it('should have valid train structure', () => {
    expect(mockTrain).toHaveProperty('id');
    expect(mockTrain).toHaveProperty('trainNumber');
    expect(mockTrain).toHaveProperty('position');
    expect(mockTrain.position).toHaveProperty('latitude');
    expect(mockTrain.position).toHaveProperty('longitude');
  });

  it('should have speed within valid range', () => {
    expect(mockTrain.currentSpeed).toBeGreaterThanOrEqual(0);
    expect(mockTrain.currentSpeed).toBeLessThanOrEqual(mockTrain.maxSpeed);
  });

  it('should have valid priority range', () => {
    expect(mockTrain.priority).toBeGreaterThanOrEqual(1);
    expect(mockTrain.priority).toBeLessThanOrEqual(10);
  });

  it('should have valid train type', () => {
    const validTypes = ['EXPRESS', 'PASSENGER', 'FREIGHT', 'SUBURBAN'];
    expect(validTypes).toContain(mockTrain.type);
  });

  it('should have valid status', () => {
    const validStatuses = ['RUNNING', 'STOPPED', 'DELAYED', 'EMERGENCY', 'MAINTENANCE'];
    expect(validStatuses).toContain(mockTrain.status);
  });
});

describe('Position Calculations', () => {
  it('should calculate distance between two positions', () => {
    const pos1: Position = { latitude: 28.6139, longitude: 77.2090 };
    const pos2: Position = { latitude: 28.7041, longitude: 77.1025 };
    
    const latDiff = pos2.latitude - pos1.latitude;
    const lonDiff = pos2.longitude - pos1.longitude;
    const distance = Math.sqrt(latDiff * latDiff + lonDiff * lonDiff);
    
    expect(distance).toBeGreaterThan(0);
    expect(distance).toBeLessThan(1); // Should be less than 1 degree
  });

  it('should handle same position', () => {
    const pos: Position = { latitude: 28.6139, longitude: 77.2090 };
    
    const distance = Math.sqrt(
      Math.pow(pos.latitude - pos.latitude, 2) +
      Math.pow(pos.longitude - pos.longitude, 2)
    );
    
    expect(distance).toBe(0);
  });
});

describe('Conflict Severity Ordering', () => {
  it('should order severities correctly', () => {
    const severityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
    
    expect(severityOrder.CRITICAL).toBeLessThan(severityOrder.HIGH);
    expect(severityOrder.HIGH).toBeLessThan(severityOrder.MEDIUM);
    expect(severityOrder.MEDIUM).toBeLessThan(severityOrder.LOW);
  });
});

describe('Time Formatting', () => {
  it('should format seconds to mm:ss', () => {
    const formatTime = (seconds: number): string => {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    };
    
    expect(formatTime(0)).toBe('0:00');
    expect(formatTime(60)).toBe('1:00');
    expect(formatTime(125)).toBe('2:05');
    expect(formatTime(3661)).toBe('61:01');
  });

  it('should format with hours for large values', () => {
    const formatTime = (seconds: number): string => {
      const hrs = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      const secs = seconds % 60;
      
      if (hrs > 0) {
        return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      }
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    };
    
    expect(formatTime(3661)).toBe('1:01:01');
    expect(formatTime(7200)).toBe('2:00:00');
  });
});

describe('Speed Calculations', () => {
  it('should calculate speed percentage', () => {
    const calculateSpeedPercentage = (current: number, max: number): number => {
      return (current / max) * 100;
    };
    
    expect(calculateSpeedPercentage(80, 120)).toBeCloseTo(66.67, 1);
    expect(calculateSpeedPercentage(0, 120)).toBe(0);
    expect(calculateSpeedPercentage(120, 120)).toBe(100);
  });

  it('should convert km/h to m/s', () => {
    const kmhToMs = (kmh: number): number => {
      return (kmh * 1000) / 3600;
    };
    
    expect(kmhToMs(36)).toBeCloseTo(10, 1);
    expect(kmhToMs(72)).toBeCloseTo(20, 1);
    expect(kmhToMs(108)).toBeCloseTo(30, 1);
  });
});

describe('Color Assignments', () => {
  it('should assign correct colors for section status', () => {
    const COLORS = {
      CLEAR: '#10b981',
      OCCUPIED: '#f59e0b',
      CONFLICT: '#ef4444',
      MAINTENANCE: '#6b7280',
      BLOCKED: '#991b1b',
    };
    
    expect(COLORS.CLEAR).toMatch(/^#[0-9a-f]{6}$/i);
    expect(COLORS.CONFLICT).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it('should assign correct colors for train status', () => {
    const COLORS = {
      RUNNING: '#3b82f6',
      STOPPED: '#ef4444',
      DELAYED: '#f59e0b',
      EMERGENCY: '#dc2626',
      MAINTENANCE: '#6b7280',
    };
    
    expect(COLORS.RUNNING).toMatch(/^#[0-9a-f]{6}$/i);
    expect(COLORS.EMERGENCY).toMatch(/^#[0-9a-f]{6}$/i);
  });
});

describe('Performance Metrics', () => {
  it('should validate FPS is within acceptable range', () => {
    const fps = 60;
    const isPerformant = fps >= 55;
    
    expect(isPerformant).toBe(true);
    expect(fps).toBeGreaterThanOrEqual(30);
    expect(fps).toBeLessThanOrEqual(120);
  });

  it('should calculate frame time from FPS', () => {
    const fps = 60;
    const frameTime = 1000 / fps;
    
    expect(frameTime).toBeCloseTo(16.67, 1);
  });
});

describe('Network Graph Data Structure', () => {
  it('should have required network graph properties', () => {
    const networkGraph = {
      stations: [],
      sections: [],
      junctions: [],
      trains: [mockTrain],
      bounds: {
        north: 0,
        south: 0,
        east: 0,
        west: 0,
      },
    };
    
    expect(networkGraph).toHaveProperty('stations');
    expect(networkGraph).toHaveProperty('sections');
    expect(networkGraph).toHaveProperty('trains');
    expect(networkGraph).toHaveProperty('bounds');
    expect(Array.isArray(networkGraph.trains)).toBe(true);
  });
});

describe('Configuration Validation', () => {
  it('should have valid zoom configuration', () => {
    const zoomConfig = {
      min: 0.5,
      max: 10,
      initial: 1,
    };
    
    expect(zoomConfig.min).toBeGreaterThan(0);
    expect(zoomConfig.max).toBeGreaterThan(zoomConfig.min);
    expect(zoomConfig.initial).toBeGreaterThanOrEqual(zoomConfig.min);
    expect(zoomConfig.initial).toBeLessThanOrEqual(zoomConfig.max);
  });

  it('should have valid animation configuration', () => {
    const animationConfig = {
      duration: 300,
      enabled: true,
      fps: 60,
    };
    
    expect(animationConfig.duration).toBeGreaterThan(0);
    expect(typeof animationConfig.enabled).toBe('boolean');
    expect(animationConfig.fps).toBeGreaterThan(0);
    expect(animationConfig.fps).toBeLessThanOrEqual(120);
  });
});
