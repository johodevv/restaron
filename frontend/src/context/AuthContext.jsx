import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../utils/api';

const AuthContext = createContext(null);
const CACHE_KEY = 'restaron_user_cache';

export const AuthProvider = ({ children }) => {
  // Read cached user immediately to render dashboard without waiting for backend
  const [user, setUser] = useState(() => {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });

  const [token, setToken] = useState(() => localStorage.getItem('restaron_token'));

  // If we already have cached user, loading is false instantly (no black spinner!)
  const [loading, setLoading] = useState(() => {
    const hasToken = !!localStorage.getItem('restaron_token');
    const hasCachedUser = !!localStorage.getItem(CACHE_KEY);
    return hasToken && !hasCachedUser;
  });

  useEffect(() => {
    let cancelled = false;
    const fetchUser = async () => {
      if (!token) {
        setUser(null);
        localStorage.removeItem(CACHE_KEY);
        setLoading(false);
        return;
      }

      try {
        const userData = await api.get('/auth/me');
        if (cancelled || localStorage.getItem('restaron_token') !== token) return;
        setUser(userData);
        localStorage.setItem(CACHE_KEY, JSON.stringify(userData));
      } catch (err) {
        if (cancelled || localStorage.getItem('restaron_token') !== token) return;
        console.error('Auth verification error:', err);
        // Only clear credentials on real 401 unauthorized, not on network timeouts or 5xx
        if (err?.status === 401 || err?.response?.status === 401) {
          localStorage.removeItem('restaron_token');
          localStorage.removeItem(CACHE_KEY);
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchUser();
    return () => { cancelled = true; };
  }, [token]);

  const login = async (username, password) => {
    const data = await api.post('/auth/login', { username, password });
    localStorage.setItem('restaron_token', data.access_token);
    localStorage.setItem(CACHE_KEY, JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const clearCredentials = () => {
    localStorage.removeItem('restaron_token');
    localStorage.removeItem(CACHE_KEY);
    setToken(null);
    setUser(null);
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (err) {
      // Offline logout still removes this device's credentials.
      console.warn('Server sessiyasini bekor qilish amalga oshmadi:', err.message);
    } finally {
      clearCredentials();
    }
  };

  useEffect(() => {
    const handleUnauthorized = () => {
      clearCredentials();
    };
    window.addEventListener('restaron:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('restaron:unauthorized', handleUnauthorized);
    };
  }, []);

  const value = {
    user,
    token,
    loading,
    login,
    logout,
    isWaiter: user?.role === 'waiter',
    isChef: user?.role === 'chef',
    isAdmin: user?.role === 'admin' || user?.role === 'developer',
    isCashier: user?.role === 'cashier' || user?.role === 'admin' || user?.role === 'developer',
    canCheckout: user?.role === 'admin' || user?.role === 'cashier' || user?.role === 'developer',
    canManageOrders: user?.role === 'admin' || user?.role === 'cashier' || user?.role === 'developer',
    isDev: user?.role === 'developer',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);

