import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children, restaurantId = 1, tableId = null }) => {
  const { user, token } = useAuth();
  const [connected, setConnected] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [lastEvent, setLastEvent] = useState(null);
  const wsRef = useRef(null);
  const listenersRef = useRef(new Map());

  // Browser Audio Notification (Chime effect using Web Audio API so no external mp3 required!)
  const playChime = useCallback((type = 'info') => {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.connect(gain);
      gain.connect(ctx.destination);

      if (type === 'urgent') {
        // High alert chime
        osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
        osc.frequency.setValueAtTime(880, ctx.currentTime + 0.15); // A5
        gain.gain.setValueAtTime(0.3, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
        osc.start();
        osc.stop(ctx.currentTime + 0.5);
      } else if (type === 'success') {
        // Sweet bell chime
        osc.frequency.setValueAtTime(523.25, ctx.currentTime); // C5
        osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.1); // E5
        osc.frequency.setValueAtTime(783.99, ctx.currentTime + 0.2); // G5
        gain.gain.setValueAtTime(0.25, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
        osc.start();
        osc.stop(ctx.currentTime + 0.6);
      } else {
        // Soft ping
        osc.frequency.setValueAtTime(440, ctx.currentTime); // A4
        gain.gain.setValueAtTime(0.2, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
        osc.start();
        osc.stop(ctx.currentTime + 0.3);
      }
    } catch (e) {
      console.warn('Audio chime unsupported or blocked:', e);
    }
  }, []);

  const addNotification = useCallback((notif) => {
    const id = Date.now() + Math.random();
    const newNotif = { id, timestamp: new Date(), ...notif };
    setNotifications((prev) => [newNotif, ...prev.slice(0, 19)]);

    // 6 soniyadan keyin avtomatik yopish
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    }, 6000);
  }, []);

  const removeNotification = (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  useEffect(() => {
    const targetRestId = user?.restaurant_id || restaurantId;
    if (!targetRestId) return;

    let wsUrl = '';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;

    const baseWs = import.meta.env.VITE_WS_URL || `${protocol}//${host}/api/v1/ws`;
    const params = new URLSearchParams();
    if (token) params.append('token', token);
    if (tableId) params.append('table_id', tableId);

    wsUrl = `${baseWs}/${targetRestId}?${params.toString()}`;

    let socket;
    let pingInterval;
    let reconnectTimeout;

    const connect = () => {
      try {
        socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          setConnected(true);
          // Ping/pong keepalive
          pingInterval = setInterval(() => {
            if (socket.readyState === WebSocket.OPEN) {
              socket.send(JSON.stringify({ type: 'ping' }));
            }
          }, 25000);
        };

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setLastEvent(data);

            // Audio & Toast triggers
            if (data.type === 'new_order') {
              playChime('urgent');
              addNotification({
                type: 'urgent',
                title: `🔔 Yangi buyurtma — Stol #${data.table_number}`,
                message: `${data.order_number} keldi. Jami: ${(data.total || 0).toLocaleString()} so'm`,
              });
            } else if (data.type === 'call_waiter') {
              playChime('urgent');
              addNotification({
                type: 'urgent',
                title: `🙋 Ofitsiant chaqirildi — Stol #${data.table_number}`,
                message: data.note || "Mijoz ofitsiant yordamini kutmoqda",
              });
            } else if (data.type === 'order_ready') {
              playChime('success');
              addNotification({
                type: 'success',
                title: `🍳 Ovqat tayyor — Stol #${data.table_number}`,
                message: `${data.order_number} tayyor bo'ldi. Stolga olib boring!`,
              });
            } else if (data.type === 'order_delivered') {
              playChime('success');
              addNotification({
                type: 'info',
                title: `✅ Yetkazib berildi — Stol #${data.table_number}`,
                message: data.message || `${data.order_number} mijozga topshirildi`,
              });
            }

            // Callbacks for subscribers
            const listeners = listenersRef.current.get(data.type) || [];
            listeners.forEach((cb) => cb(data));

            const anyListeners = listenersRef.current.get('*') || [];
            anyListeners.forEach((cb) => cb(data));
          } catch (err) {
            console.error('WS parse error:', err);
          }
        };

        socket.onclose = () => {
          setConnected(false);
          clearInterval(pingInterval);
          // Auto reconnect after 4 seconds
          reconnectTimeout = setTimeout(connect, 4000);
        };

        socket.onerror = () => {
          socket.close();
        };
      } catch (err) {
        console.error('WS Connection error:', err);
        reconnectTimeout = setTimeout(connect, 4000);
      }
    };

    connect();

    return () => {
      clearInterval(pingInterval);
      clearTimeout(reconnectTimeout);
      if (socket) socket.close();
    };
  }, [token, user?.restaurant_id, restaurantId, tableId, playChime, addNotification]);

  const addEventListener = useCallback((type, callback) => {
    if (!listenersRef.current.has(type)) {
      listenersRef.current.set(type, new Set());
    }
    listenersRef.current.get(type).add(callback);

    return () => {
      const set = listenersRef.current.get(type);
      if (set) set.delete(callback);
    };
  }, []);

  return (
    <WebSocketContext.Provider
      value={{
        connected,
        notifications,
        removeNotification,
        lastEvent,
        addEventListener,
        playChime,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => useContext(WebSocketContext);
