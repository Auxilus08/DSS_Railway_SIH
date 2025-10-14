import { useState, useCallback } from 'react';
import apiService from '../services/api';
import { useNotifications } from '../context/NotificationContext';

interface UseApiOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: any) => void;
  showSuccessNotification?: boolean;
  showErrorNotification?: boolean;
  successMessage?: string;
}

export const useApi = <T = any,>(
  apiFunction: (...args: any[]) => Promise<T>,
  options: UseApiOptions<T> = {}
) => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<any>(null);
  const { addNotification } = useNotifications();

  const execute = useCallback(
    async (...args: any[]) => {
      setLoading(true);
      setError(null);

      try {
        const result = await apiFunction(...args);
        setData(result);

        if (options.onSuccess) {
          options.onSuccess(result);
        }

        if (options.showSuccessNotification && options.successMessage) {
          addNotification({
            type: 'SUCCESS',
            title: 'Success',
            message: options.successMessage,
          });
        }

        return result;
      } catch (err: any) {
        setError(err);

        if (options.onError) {
          options.onError(err);
        }

        // Don't show notifications for auth errors (401, 403) as they're handled by interceptor
        const shouldShowNotification = 
          options.showErrorNotification !== false && 
          err.response?.status !== 401 && 
          err.response?.status !== 403;

        if (shouldShowNotification) {
          addNotification({
            type: 'ERROR',
            title: 'Error',
            message: err.response?.data?.detail || err.response?.data?.error || err.message || 'An error occurred',
          });
        }

        throw err;
      } finally {
        setLoading(false);
      }
    },
    [apiFunction, options, addNotification]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return {
    data,
    loading,
    error,
    execute,
    reset,
  };
};

// Specific hooks for common API calls
export const useTrains = () => {
  return useApi(apiService.getTrains);
};

export const useSections = () => {
  return useApi(apiService.getSections);
};

export const useSectionStatuses = () => {
  return useApi(() => apiService.getSectionStatus());
};

export const useConflicts = (hours: number = 24) => {
  return useApi(() => apiService.getConflicts(hours));
};

export const usePerformanceMetrics = () => {
  return useApi(apiService.getPerformanceMetrics);
};

export default useApi;
