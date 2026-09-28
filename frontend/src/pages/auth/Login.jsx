import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import {
  UtensilsCrossed,
  Lock,
  User,
  ArrowRight,
  Loader2,
  Eye,
  EyeOff,
  ShieldCheck
} from 'lucide-react';

export const Login = ({ onSuccess, onBackToMenu }) => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!username.trim() || !password) {
      setError("Iltimos, login va parolni kiriting");
      return;
    }
    setLoading(true);
    setError('');

    try {
      await login(username.trim(), password);
      if (onSuccess) onSuccess();
    } catch (err) {
      setError(err.message || "Login yoki parol noto'g'ri");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-theme-bg">
      <div className="w-full max-w-md p-6 sm:p-8 rounded-3xl glass-card border border-theme-border bg-theme-surface/95 shadow-2xl space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-theme-primary to-theme-accent flex items-center justify-center text-white mx-auto shadow-glow">
            <UtensilsCrossed className="w-7 h-7" />
          </div>
          <h2 className="text-2xl font-black text-white tracking-tight">
            RestAron Tizimiga Kirish
          </h2>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-theme-primary/10 border border-theme-primary/20 text-theme-primary text-xs font-semibold">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Xavfsiz Xodimlar Portali</span>
          </div>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300 text-xs text-center font-medium animate-fade-in">
            ⚠️ {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-theme-muted mb-1.5">
              Login (Foydalanuvchi nomi):
            </label>
            <div className="relative">
              <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-theme-muted" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Loginni kiriting"
                autoComplete="username"
                className="w-full pl-10 pr-4 py-3 rounded-xl bg-black/30 border border-theme-border text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary transition-colors"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-theme-muted mb-1.5">
              Parol:
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-theme-muted" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Parolni kiriting"
                autoComplete="current-password"
                className="w-full pl-10 pr-11 py-3 rounded-xl bg-black/30 border border-theme-border text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary transition-colors"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-theme-muted hover:text-white transition-colors"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white font-bold text-sm shadow-glow flex items-center justify-center gap-2 active:scale-98 transition-all disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ArrowRight className="w-4 h-4" />
            )}
            <span>{loading ? 'Tekshirilmoqda...' : 'Tizimga kirish'}</span>
          </button>
        </form>

        {onBackToMenu && (
          <div className="text-center pt-2 border-t border-theme-border/60">
            <button
              onClick={onBackToMenu}
              className="text-xs text-theme-muted hover:text-white transition-colors inline-flex items-center gap-1 font-medium"
            >
              ← Bosh sahifaga qaytish
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Login;
