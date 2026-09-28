import React, { createContext, useContext, useState, useEffect } from 'react';

export const ALL_THEMES = [
  { id: 1, slug: 'elegant-dark', name: 'Elegant Dark', icon: '✨', primary: '#D4AF37', bg: '#0b0b14' },
  { id: 2, slug: 'fresh-green', name: 'Fresh Green', icon: '🌿', primary: '#10b981', bg: '#061812' },
  { id: 3, slug: 'warm-sunset', name: 'Warm Sunset', icon: '🌅', primary: '#f97316', bg: '#160c07' },
  { id: 4, slug: 'ocean-blue', name: 'Ocean Blue', icon: '🌊', primary: '#0ea5e9', bg: '#061322' },
  { id: 5, slug: 'royal-purple', name: 'Royal Purple', icon: '👑', primary: '#a855f7', bg: '#12091c' },
  { id: 6, slug: 'minimalist-white', name: 'Minimalist White', icon: '⚪', primary: '#2563eb', bg: '#f8fafc' },
];

const ThemeContext = createContext(null);

export const ThemeProvider = ({ children }) => {
  const [currentTheme, setCurrentTheme] = useState(
    localStorage.getItem('restaron_theme') || 'elegant-dark'
  );
  // Admin tomonidan tanlangan 2 ta tema (default: elegant-dark va fresh-green)
  const [activeThemes, setActiveThemes] = useState([
    'elegant-dark',
    'fresh-green'
  ]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', currentTheme);
    localStorage.setItem('restaron_theme', currentTheme);
  }, [currentTheme]);

  const setTheme = (slug) => {
    setCurrentTheme(slug);
  };

  const toggleBetweenActive = () => {
    const next = currentTheme === activeThemes[0] ? activeThemes[1] : activeThemes[0];
    setTheme(next);
  };

  return (
    <ThemeContext.Provider
      value={{
        currentTheme,
        setTheme,
        activeThemes,
        setActiveThemes,
        toggleBetweenActive,
        allThemes: ALL_THEMES,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
