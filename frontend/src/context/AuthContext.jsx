import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../utils/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('restaron_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }

      try {
        const userData = await api.get('/auth/me');
        setUser(userData);
      } catch (err) {
        console.error('Auth error:', err);
        localStorage.removeItem('restaron_token');
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [token]);

  const login = async (username, password) => {
    const data = await api.post('/auth/login', { username, password });
    localStorage.setItem('restaron_token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem('restaron_token');
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
