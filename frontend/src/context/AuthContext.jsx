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
    const fetchUser = async () => {
      if (!token) {
        setUser(null);
        localStorage.removeItem(CACHE_KEY);
        setLoading(false);
        return;
      }

      try {
        const userData = await api.get('/auth/me');
        setUser(userData);
        localStorage.setItem(CACHE_KEY, JSON.stringify(userData));
      } catch (err) {
        console.error('Auth verification error:', err);
        // Only clear credentials on real 401 unauthorized, not on network timeouts or 5xx
        if (err?.status === 401 || err?.response?.status === 401) {
          localStorage.removeItem('restaron_token');
          localStorage.removeItem(CACHE_KEY);
          setToken(null);
          setUser(null);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [token]);

  const login = async (username, password) => {
    const data = await api.post('/auth/login', { username, password });
    localStorage.setItem('restaron_token', data.access_token);
    localStorage.setItem(CACHE_KEY, JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem('restaron_token');
    localStorage.removeItem(CACHE_KEY);
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    loading,
    login,
    logout,
    isWaiter: user?.role === 'waiter',
    isChef: user?.role === 'chef',
    isAdmin: user?.role === 'admin' || user?.role === 'developer',
    isDev: user?.role === 'developer',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);

