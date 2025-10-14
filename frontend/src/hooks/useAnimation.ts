/**
 * Custom Hook for Animation Management
 * Provides smooth 60fps animations for train movement and transitions
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Position, Train, TransitionState, AnimationFrame } from '../types/visualization';

interface AnimationOptions {
  duration?: number;
  fps?: number;
  easing?: EasingFunction;
}

type EasingFunction = (t: number) => number;

// Common easing functions
export const easingFunctions = {
  linear: (t: number) => t,
  easeInQuad: (t: number) => t * t,
  easeOutQuad: (t: number) => t * (2 - t),
  easeInOutQuad: (t: number) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t),
  easeInCubic: (t: number) => t * t * t,
  easeOutCubic: (t: number) => --t * t * t + 1,
  easeInOutCubic: (t: number) =>
    t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1,
  easeInOutSine: (t: number) => -(Math.cos(Math.PI * t) - 1) / 2,
};

/**
 * Hook for smooth position interpolation
 */
export function usePositionAnimation(
  targetPosition: Position,
  options: AnimationOptions = {}
) {
  const {
    duration = 1000,
    easing = easingFunctions.easeInOutQuad,
  } = options;

  const [currentPosition, setCurrentPosition] = useState(targetPosition);
  const animationRef = useRef<number>();
  const startPositionRef = useRef(targetPosition);
  const startTimeRef = useRef<number>();

  useEffect(() => {
    startPositionRef.current = currentPosition;
    startTimeRef.current = undefined;

    const animate = (timestamp: number) => {
      if (!startTimeRef.current) {
        startTimeRef.current = timestamp;
      }

      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);
      const easedProgress = easing(progress);

      const newPosition: Position = {
        latitude:
          startPositionRef.current.latitude +
          (targetPosition.latitude - startPositionRef.current.latitude) * easedProgress,
        longitude:
          startPositionRef.current.longitude +
          (targetPosition.longitude - startPositionRef.current.longitude) * easedProgress,
        x:
          startPositionRef.current.x !== undefined && targetPosition.x !== undefined
            ? startPositionRef.current.x +
              (targetPosition.x - startPositionRef.current.x) * easedProgress
            : undefined,
        y:
          startPositionRef.current.y !== undefined && targetPosition.y !== undefined
            ? startPositionRef.current.y +
              (targetPosition.y - startPositionRef.current.y) * easedProgress
            : undefined,
      };

      setCurrentPosition(newPosition);

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [targetPosition, duration, easing]);

  return currentPosition;
}

/**
 * Hook for managing train animations with velocity-based interpolation
 */
export function useTrainAnimation(trains: Train[], fps: number = 60) {
  const [animatedTrains, setAnimatedTrains] = useState<Map<string, Position>>(new Map());
  const previousTrainsRef = useRef<Map<string, Train>>(new Map());
  const frameRef = useRef<number>();
  const lastFrameTimeRef = useRef<number>();

  useEffect(() => {
    const frameDuration = 1000 / fps;
    let running = true;

    const animate = (timestamp: number) => {
      if (!running) return;

      if (!lastFrameTimeRef.current) {
        lastFrameTimeRef.current = timestamp;
      }

      const deltaTime = timestamp - lastFrameTimeRef.current;

      if (deltaTime >= frameDuration) {
        const newPositions = new Map<string, Position>();

        trains.forEach(train => {
          const previousTrain = previousTrainsRef.current.get(train.id);
          
          if (previousTrain) {
            // Calculate interpolated position based on speed and time
            const speedKmh = train.currentSpeed;
            const speedMs = (speedKmh * 1000) / 3600; // Convert km/h to m/s
            const distanceM = speedMs * (deltaTime / 1000);
            
            // Simple linear interpolation (in production, would use proper geo calculations)
            const latDiff = train.position.latitude - previousTrain.position.latitude;
            const lonDiff = train.position.longitude - previousTrain.position.longitude;
            const totalDist = Math.sqrt(latDiff * latDiff + lonDiff * lonDiff);
            
            if (totalDist > 0) {
              const progress = Math.min(distanceM / (totalDist * 111000), 1); // 111km per degree
              
              newPositions.set(train.id, {
                latitude: previousTrain.position.latitude + latDiff * progress,
                longitude: previousTrain.position.longitude + lonDiff * progress,
                x: previousTrain.position.x !== undefined && train.position.x !== undefined
                  ? previousTrain.position.x + (train.position.x - previousTrain.position.x) * progress
                  : undefined,
                y: previousTrain.position.y !== undefined && train.position.y !== undefined
                  ? previousTrain.position.y + (train.position.y - previousTrain.position.y) * progress
                  : undefined,
              });
            } else {
              newPositions.set(train.id, train.position);
            }
          } else {
            newPositions.set(train.id, train.position);
          }
        });

        setAnimatedTrains(newPositions);
        lastFrameTimeRef.current = timestamp;
      }

      frameRef.current = requestAnimationFrame(animate);
    };

    // Update previous trains reference
    trains.forEach(train => {
      previousTrainsRef.current.set(train.id, train);
    });

    frameRef.current = requestAnimationFrame(animate);

    return () => {
      running = false;
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [trains, fps]);

  return animatedTrains;
}

/**
 * Hook for transition states (e.g., color transitions, opacity)
 */
export function useTransition<T>(
  targetValue: T,
  duration: number = 300,
  interpolate: (from: T, to: T, progress: number) => T
) {
  const [currentValue, setCurrentValue] = useState(targetValue);
  const transitionRef = useRef<TransitionState<T> | null>(null);
  const animationRef = useRef<number>();

  useEffect(() => {
    if (!transitionRef.current) {
      transitionRef.current = {
        from: currentValue,
        to: targetValue,
        progress: 0,
        duration,
        startTime: performance.now(),
      };
    } else {
      transitionRef.current = {
        from: currentValue,
        to: targetValue,
        progress: 0,
        duration,
        startTime: performance.now(),
      };
    }

    const animate = (timestamp: number) => {
      if (!transitionRef.current) return;

      const elapsed = timestamp - transitionRef.current.startTime;
      const progress = Math.min(elapsed / duration, 1);

      const interpolated = interpolate(
        transitionRef.current.from,
        transitionRef.current.to,
        easingFunctions.easeInOutQuad(progress)
      );

      setCurrentValue(interpolated);

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        transitionRef.current = null;
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [targetValue, duration, interpolate]);

  return currentValue;
}

/**
 * Hook for frame-based animation loop
 */
export function useAnimationFrame(
  callback: (deltaTime: number, timestamp: number) => void,
  enabled: boolean = true
) {
  const requestRef = useRef<number>();
  const previousTimeRef = useRef<number>();
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;

    const animate = (timestamp: number) => {
      if (previousTimeRef.current !== undefined) {
        const deltaTime = timestamp - previousTimeRef.current;
        callbackRef.current(deltaTime, timestamp);
      }
      previousTimeRef.current = timestamp;
      requestRef.current = requestAnimationFrame(animate);
    };

    requestRef.current = requestAnimationFrame(animate);

    return () => {
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
      previousTimeRef.current = undefined;
    };
  }, [enabled]);
}

/**
 * Hook for performance monitoring
 */
export function usePerformanceMonitor() {
  const [fps, setFps] = useState(60);
  const [frameTime, setFrameTime] = useState(0);
  const frameCountRef = useRef(0);
  const lastFpsUpdateRef = useRef(performance.now());
  const frameTimesRef = useRef<number[]>([]);

  useAnimationFrame((deltaTime) => {
    frameCountRef.current++;
    frameTimesRef.current.push(deltaTime);

    // Keep only last 60 frames
    if (frameTimesRef.current.length > 60) {
      frameTimesRef.current.shift();
    }

    const now = performance.now();
    const elapsed = now - lastFpsUpdateRef.current;

    // Update FPS every second
    if (elapsed >= 1000) {
      const currentFps = Math.round((frameCountRef.current * 1000) / elapsed);
      const avgFrameTime = frameTimesRef.current.reduce((a, b) => a + b, 0) / frameTimesRef.current.length;
      
      setFps(currentFps);
      setFrameTime(avgFrameTime);
      
      frameCountRef.current = 0;
      lastFpsUpdateRef.current = now;
    }
  });

  return {
    fps,
    frameTime,
    isPerformant: fps >= 55, // Consider 55+ fps as good performance
  };
}

/**
 * Hook for countdown timer (for conflict time-to-impact)
 */
export function useCountdown(initialSeconds: number, onComplete?: () => void) {
  const [timeRemaining, setTimeRemaining] = useState(initialSeconds);
  const [isRunning, setIsRunning] = useState(true);
  const intervalRef = useRef<NodeJS.Timeout>();
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    setTimeRemaining(initialSeconds);
    setIsRunning(true);
  }, [initialSeconds]);

  useEffect(() => {
    if (!isRunning) return;

    intervalRef.current = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 0) {
          setIsRunning(false);
          onCompleteRef.current?.();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isRunning]);

  const pause = useCallback(() => setIsRunning(false), []);
  const resume = useCallback(() => setIsRunning(true), []);
  const reset = useCallback(() => {
    setTimeRemaining(initialSeconds);
    setIsRunning(true);
  }, [initialSeconds]);

  return {
    timeRemaining,
    isRunning,
    pause,
    resume,
    reset,
    formatted: formatTime(timeRemaining),
  };
}

function formatTime(seconds: number): string {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default usePositionAnimation;
