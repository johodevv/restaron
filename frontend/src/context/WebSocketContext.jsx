import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { openSocketConnection } from '../utils/socketConnection';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children, restaurantId = 1, tableId = null }) => {
  const { user, token } = useAuth();
  const [connected, setConnected] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [lastEvent, setLastEvent] = useState(null);
  const [connectionError, setConnectionError] = useState(null);
  const [connectionPhase, setConnectionPhase] = useState('connecting');
  const connectionRef = useRef(null);
  const reconnect = useCallback(() => connectionRef.current?.resume(), []);
  const listenersRef = useRef(new Map());
  const audioCtxRef = useRef(null);

  // AudioContext: bitta umumiy instansiya (useRef), har chimeda yangisi yaratilmaydi
  const getAudioContext = useCallback(() => {
    if (!audioCtxRef.current) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        audioCtxRef.current = new AudioContextClass();
      }
    }
    return audioCtxRef.current;
  }, []);

  // Birinchi foydalanuvchi bosishida (pointerdown, bir marta) uni unlock qilish
  useEffect(() => {
    const unlockAudio = () => {
      const ctx = getAudioContext();
      if (ctx && ctx.state === 'suspended') {
        ctx.resume().catch(() => {});
      }
    };

    window.addEventListener('pointerdown', unlockAudio, { once: true });
    window.addEventListener('keydown', unlockAudio, { once: true });

    return () => {
      window.removeEventListener('pointerdown', unlockAudio);
      window.removeEventListener('keydown', unlockAudio);
    };
  }, [getAudioContext]);

  // Browser Audio Notification (Chime effect using Web Audio API)
  const playChime = useCallback(async (type = 'info') => {
    try {
      const ctx = getAudioContext();
      if (!ctx) return;

      // Chalishdan oldin resume()
      if (ctx.state === 'suspended') {
        await ctx.resume().catch(() => {});
      }

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
  }, [getAudioContext]);

  // Bildirishnoma qo'shish
  const addNotification = useCallback((notif) => {
    const id = Date.now() + Math.random();
    const newNotif = { id, timestamp: new Date(), ...notif };
    setNotifications((prev) => [newNotif, ...prev.slice(0, 19)]);

    // 6. call_waiter turi uchun avtomatik yo'qolish o'chirilgan (foydalanuvchi yopguncha tursin)
    const isCallWaiter = notif.eventType === 'call_waiter' || notif.type === 'call_waiter' || notif.isCallWaiter;
    if (!isCallWaiter && !notif.persistent) {
      setTimeout(() => {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
      }, 6000);
    }
  }, []);

  const removeNotification = (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  useEffect(() => {
    const targetRestId = user?.restaurant_id || restaurantId;
    setConnected(false);
    setConnectionPhase('connecting');
    setConnectionError(null);
    if (!targetRestId || (!token && !tableId) || (token && !user)) return;

    let wsUrl = '';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;

    let baseWs = import.meta.env.VITE_WS_URL;
    if (!baseWs) {
      const rawApi = import.meta.env.VITE_API_URL;
      if (rawApi && rawApi.startsWith('http')) {
        const wsProto = rawApi.startsWith('https') ? 'wss:' : 'ws:';
        const cleanHost = rawApi.replace(/^https?:\/\//, '').replace(/\/api\/v1\/?$/, '').replace(/\/+$/, '');
        baseWs = `${wsProto}//${cleanHost}/api/v1/ws`;
      } else {
        baseWs = `${protocol}//${host}/api/v1/ws`;
      }
    }
    const params = new URLSearchParams();
    if (token) params.append('token', token);
    if (tableId) params.append('table_id', tableId);

    wsUrl = `${baseWs.replace(/\/+$/, '')}/${targetRestId}?${params.toString()}`;

    let established = false;
    const connection = openSocketConnection({
      url: wsUrl,
      onState: value => {
        setConnected(value);
        setConnectionPhase(value ? 'connected' : established ? 'reconnecting' : 'connecting');
        if (value) {
          established = true;
          setConnectionError(null);
          window.dispatchEvent(new Event('restaron:ws-open'));
        }
      },
      onDenied: code => {
        setConnectionPhase('denied');
        if (code === 4401) window.dispatchEvent(new Event('restaron:unauthorized'));
        else setConnectionError('Bu restoran uchun ulanishga ruxsat yo‘q. Qayta kiring.');
      },
      onMessage: data => {
        if (data.type === 'session_revoked' && data.user_id === user?.id) {
          window.dispatchEvent(new Event('restaron:unauthorized'));
          return;
        }
        setLastEvent(data);
            // Audio & Toast triggers
            if (data.type === 'new_order' && !(user?.role === 'waiter' && data.waiter_id === user.id)) {
              playChime('urgent');
              addNotification({
                type: 'urgent',
                title: `🔔 Yangi buyurtma — Stol #${data.table_number}`,
                message: `${data.order_number} keldi. Jami: ${(data.total || 0).toLocaleString()} so'm`,
              });
            } else if (data.type === 'call_waiter') {
              playChime('urgent');
              // 5. navigator.vibrate mavjud bo'lsa call_waiter chaqiruvida [200, 100, 200]
              if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
                try {
                  navigator.vibrate([200, 100, 200]);
                } catch (vErr) {}
              }
              // 6. call_waiter uchun avtomatik yo'qolish o'chirilgan
              addNotification({
                eventType: 'call_waiter',
                callId: data.id,
                type: 'urgent',
                title: `🙋 Ofitsiant chaqirildi — Stol #${data.table_number}`,
                message: data.note || "Mijoz ofitsiant yordamini kutmoqda",
              });
            } else if (data.type === 'call_completed') {
              const resolvedIds = new Set(data.resolved_call_ids || [data.call_id]);
              setNotifications((prev) => prev.filter((n) =>
                n.eventType !== 'call_waiter' || !resolvedIds.has(n.callId)));
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
      },
    });
    connectionRef.current = connection;
    const resume = () => connection.resume();
    const onVisible = () => { if (document.visibilityState === 'visible') resume(); };
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('online', resume);
    window.addEventListener('pageshow', resume);
    return () => {
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('online', resume);
      window.removeEventListener('pageshow', resume);
      connection.dispose();
      if (connectionRef.current === connection) connectionRef.current = null;
    };
  }, [token, user?.id, user?.role, user?.restaurant_id, restaurantId, tableId, playChime, addNotification]);

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
        connectionError,
        connectionPhase,
        reconnect,
        notifications,
        addNotification,
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
export default WebSocketContext;
