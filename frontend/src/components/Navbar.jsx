import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useCart } from '../context/CartContext';
import { useWebSocket } from '../context/WebSocketContext';
import ThemePickerModal from './ThemePickerModal';
import {
  UtensilsCrossed,
  Palette,
  ShoppingBag,
  BellRing,
  LogOut,
  User,
  Clock,
  Receipt,
  Menu
} from 'lucide-react';

export const Navbar = ({
  tableInfo,
  onOpenCart,
  onOpenCallWaiter,
  onOpenBill,
  currentView,
  onNavigate,
  onReturnToLanding,
  activeOrderId,
}) => {
  const { user, logout } = useAuth();
  const { totalCount } = useCart();
  const { connected } = useWebSocket();
  const [themeModalOpen, setThemeModalOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-40 w-full backdrop-blur-xl bg-theme-surface/80 border-b border-theme-border/60 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          {/* Logo & Brand */}
          <div
            onClick={() => {
              if (tableInfo && onReturnToLanding) onReturnToLanding();
              else if (onNavigate) onNavigate('menu');
            }}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-amber-600 flex items-center justify-center text-black font-bold shadow-glow group-hover:scale-105 transition-transform">
              <UtensilsCrossed className="w-5 h-5" />
            </div>
            <div>
              <span className="font-extrabold text-base sm:text-lg tracking-tight bg-gradient-to-r from-white via-white/95 to-amber-400 bg-clip-text text-transparent">
                Dunyo Choyxonasi
              </span>
              {tableInfo ? (
                <div className="text-[11px] text-amber-400 font-bold flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Stol #{tableInfo.number} {tableInfo.room ? `(${tableInfo.room})` : ''}
                  <span className="text-[9px] text-theme-muted font-normal underline ml-1">← Boshqa stol</span>
                </div>
              ) : (
                <div className="text-[11px] text-theme-muted font-medium flex items-center gap-1">
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      connected ? 'bg-emerald-400' : 'bg-red-400'
                    }`}
                  />
                  {connected ? 'Tizim faol' : 'Aloqa...'}
                </div>
              )}
            </div>
          </div>

          {/* Action Items */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Customer specific navigation */}
            {!user && activeOrderId && (
              <button
                onClick={() => onNavigate && onNavigate(currentView === 'tracker' ? 'menu' : 'tracker')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold transition-all ${
                  currentView === 'tracker'
                    ? 'bg-theme-primary/20 border-theme-primary text-theme-primary'
                    : 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/25 animate-pulse'
                }`}
              >
                <Clock className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">
                  {currentView === 'tracker' ? 'Menyuga qaytish' : 'Buyurtma holati'}
                </span>
              </button>
            )}

            {/* Customer Live Bill Button */}
            {tableInfo && !user && onOpenBill && (
              <button
                onClick={onOpenBill}
                title="Mening hisobim (Chek)"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-theme-border/70 hover:border-theme-primary/50 bg-white/5 hover:bg-white/10 text-white text-xs font-semibold transition-all"
              >
                <Receipt className="w-3.5 h-3.5 text-theme-primary" />
                <span className="hidden sm:inline">Hisob (Chek)</span>
              </button>
            )}

            {/* Theme switcher */}
            <button
              onClick={() => setThemeModalOpen(true)}
              title="Dizayn temasini o'zgartirish"
              className="p-2 rounded-xl border border-theme-border/60 hover:border-theme-primary/60 bg-white/5 hover:bg-white/10 transition-all text-theme-text"
            >
              <Palette className="w-4 h-4 text-theme-primary" />
            </button>

            {/* Customer specific: Chaqirish & Savatcha */}
            {tableInfo && !user && (
              <>
                <button
                  onClick={onOpenCallWaiter}
                  className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 text-xs font-semibold transition-all"
                >
                  <BellRing className="w-3.5 h-3.5 animate-bounce-subtle" />
                  <span>Ofitsiant chaqirish</span>
                </button>

                <button
                  onClick={onOpenCart}
                  className="relative p-2.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white shadow-glow transition-all"
                >
                  <ShoppingBag className="w-4 h-4" />
                  {totalCount > 0 && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center animate-pulse">
                      {totalCount}
                    </span>
                  )}
                </button>
              </>
            )}

            {/* Staff / Auth specific */}
            {user ? (
              <div className="flex items-center gap-2">
                <div className="hidden md:flex flex-col items-end">
                  <span className="text-xs font-semibold text-white">
                    {user.full_name || user.username}
                  </span>
                  <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-theme-primary/20 text-theme-primary font-bold">
                    {user.role}
                  </span>
                </div>
                <button
                  onClick={logout}
                  title="Chiqish"
                  className="p-2 rounded-xl border border-theme-border/60 hover:border-red-500/40 text-theme-muted hover:text-red-400 hover:bg-red-500/10 transition-all"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => onNavigate && onNavigate('login')}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-white/10 hover:bg-white/20 border border-white/10 text-white transition-all shadow-sm"
              >
                <User className="w-3.5 h-3.5 text-theme-primary" />
                <span>Xodimlar</span>
              </button>
            )}
          </div>
        </div>
      </header>

      <ThemePickerModal
        isOpen={themeModalOpen}
        onClose={() => setThemeModalOpen(false)}
      />
    </>
  );
};

export default Navbar;
