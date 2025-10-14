import { useEffect, useState, useCallback, useRef } from 'react';
import wsService from '../services/websocket';
import { WebSocketMessage } from '../types';
import { useNotifications } from '../context/NotificationContext';

interface UseWebSocketOptions {
  autoConnect?: boolean;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const {
    autoConnect = true,
    onMessage,
    onConnect,
    onDisconnect
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const { addNotification } = useNotifications();
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);

  // Keep refs up to date
  useEffect(() => {
    onMessageRef.current = onMessage;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
  }, [onMessage, onConnect, onDisconnect]);

  useEffect(() => {
    if (!autoConnect) return;

    // Message handler
    const handleMessage = (message: WebSocketMessage) => {
      setLastMessage(message);
      onMessageRef.current?.(message);

      // Handle conflict alerts
      if (message.type === 'CONFLICT_ALERT') {
        addNotification({
          type: 'WARNING',
          title: 'Conflict Detected',
          message: message.data.description || 'A conflict has been detected in the railway system.',
        });
      }

      // Handle system notifications
      if (message.type === 'NOTIFICATION') {
        const { type, title, message: msg } = message.data;
        addNotification({
          type: type || 'INFO',
          title: title || 'System Notification',
          message: msg || 'You have a new notification.',
        });
      }
    };

    // Connection handler
    const handleConnect = () => {
      setIsConnected(true);
      onConnectRef.current?.();
      console.log('WebSocket connected');
    };

    // Disconnection handler
    const handleDisconnect = () => {
      setIsConnected(false);
      onDisconnectRef.current?.();
      console.log('WebSocket disconnected');
    };

    // Register handlers
    const unsubMessage = wsService.onMessage(handleMessage);
    const unsubConnect = wsService.onConnect(handleConnect);
    const unsubDisconnect = wsService.onDisconnect(handleDisconnect);

    // Connect
    wsService.connect();

    // Update initial state
    setIsConnected(wsService.isConnected());

    // Cleanup
    return () => {
      unsubMessage();
      unsubConnect();
      unsubDisconnect();
    };
  }, [autoConnect, addNotification]);

  const sendMessage = useCallback((message: Omit<WebSocketMessage, 'timestamp'>) => {
    wsService.send({
      ...message,
      timestamp: new Date().toISOString(),
    });
  }, []);

  const connect = useCallback(() => {
    wsService.connect();
  }, []);

  const disconnect = useCallback(() => {
    wsService.disconnect();
  }, []);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
  };
};

export default useWebSocket;
