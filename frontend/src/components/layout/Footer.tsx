import React, { useEffect, useState } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import apiService from '../../services/api';

const Footer: React.FC = () => {
  const { isConnected } = useWebSocket();
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    // Update time every second
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    // Fetch system status
    const fetchSystemStatus = async () => {
      try {
        const status = await apiService.getHealthStatus();
        setSystemStatus(status);
      } catch (error) {
        console.error('Failed to fetch system status:', error);
      }
    };

    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 60000); // Update every minute

    return () => clearInterval(interval);
  }, []);

  return (
    <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 py-4 px-6">
      <div className="flex flex-col sm:flex-row items-center justify-between">
        {/* Left side - System status */}
        <div className="flex items-center space-x-6 text-xs text-gray-600 dark:text-gray-400">
          <div className="flex items-center">
            <span
              className={`h-2 w-2 rounded-full mr-2 ${
                systemStatus?.status === 'ok' ? 'bg-green-500' : 'bg-red-500'
              }`}
            ></span>
            <span>System: {systemStatus?.status?.toUpperCase() || 'UNKNOWN'}</span>
          </div>

          <div className="flex items-center">
            <span
              className={`h-2 w-2 rounded-full mr-2 ${
                systemStatus?.database_status === 'ok' ? 'bg-green-500' : 'bg-red-500'
              }`}
            ></span>
            <span>Database: {systemStatus?.database_status?.toUpperCase() || 'UNKNOWN'}</span>
          </div>

          <div className="flex items-center">
            <span
              className={`h-2 w-2 rounded-full mr-2 ${
                isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`}
            ></span>
            <span>WebSocket: {isConnected ? 'CONNECTED' : 'DISCONNECTED'}</span>
          </div>

          {systemStatus?.active_connections !== undefined && (
            <div className="flex items-center">
              <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                />
              </svg>
              <span>{systemStatus.active_connections} Active</span>
            </div>
          )}
        </div>

        {/* Center - Current time */}
        <div className="text-xs text-gray-600 dark:text-gray-400 mt-2 sm:mt-0">
          <span className="font-mono">
            {currentTime.toLocaleDateString()} {currentTime.toLocaleTimeString()}
          </span>
        </div>

        {/* Right side - Copyright */}
        <div className="text-xs text-gray-600 dark:text-gray-400 mt-2 sm:mt-0">
          <span>© 2025 Railway Traffic Management System</span>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
