import React, { useEffect, useState } from 'react';
import { useWebSocket } from '../../context/WebSocketContext';
import confetti from 'canvas-confetti';
import {
  ShieldCheck,
  UtensilsCrossed,
  BellRing,
  Loader2,
  Clock,
  Sparkles,
  ArrowLeft,
  CheckCircle2
} from 'lucide-react';
import api from '../../utils/api';

export const TableWaitingVerification = ({
  tableInfo,
  onUnlocked,
  onReturnToLanding,
}) => {
  const wsContext = useWebSocket();
  const addEventListener = wsContext?.addEventListener;
  const playChime = wsContext?.playChime;
  const [callingWaiter, setCallingWaiter] = useState(false);
  const [callSent, setCallSent] = useState(false);
  const [unlockedSuccess, setUnlockedSuccess] = useState(false);

  const pinCode = tableInfo?.pin || tableInfo?.current_pin || '----';

  useEffect(() => {
    // Check if table is already unlocked from server
    if (tableInfo?.is_unlocked) {
      onUnlocked();
      return;
    }


    // Listen to real-time table_unlocked websocket event
    if (!addEventListener) return;
    const unsubscribe = addEventListener('table_unlocked', (event) => {
      if (
        event.table_id === tableInfo?.id ||
        event.table_number === tableInfo?.number
      ) {
        setUnlockedSuccess(true);
        if (playChime) playChime('success');
        try {
          confetti({
            particleCount: 80,
            spread: 70,
            origin: { y: 0.6 },
          });
        } catch (e) {}

        localStorage.setItem(`unlocked_table_${tableInfo?.id}`, 'true');

        setTimeout(() => {
          onUnlocked();
        }, 1200);
      }
    });

    return () => { if (unsubscribe) unsubscribe(); };
  }, [tableInfo?.id, onUnlocked, playChime]);

  const handleCallWaiter = async () => {
    if (callingWaiter || callSent) return;
    setCallingWaiter(true);
    try {
      await api.post('/orders/call-waiter', {
        table_id: tableInfo?.id,
        note: `Mijoz stolni ochishni kutmoqda (Kodi: ${pinCode})`,
      });
      setCallSent(true);
      setTimeout(() => setCallSent(false), 8000);
    } catch (err) {
      console.warn('Call waiter error:', err);
    } finally {
      setCallingWaiter(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-theme-bg relative overflow-hidden">
      {/* Glow effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md p-6 sm:p-8 rounded-3xl glass-card border border-theme-border bg-theme-surface/95 shadow-2xl space-y-6 text-center relative z-10 animate-fade-in">
        {/* Brand Icon */}
        <div className="relative mx-auto w-16 h-16 rounded-2xl bg-gradient-to-tr from-amber-500 to-amber-600 flex items-center justify-center text-black font-bold shadow-glow">
          {unlockedSuccess ? (
            <CheckCircle2 className="w-8 h-8 text-black animate-scale-up" />
          ) : (
            <UtensilsCrossed className="w-8 h-8" />
          )}
        </div>

        {/* Header */}
        <div className="space-y-1.5">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-bold">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Dunyo Choyxonasi • Stol #{tableInfo?.number}</span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight pt-1">
            {unlockedSuccess ? "Stolingiz Faollashdi! 🎉" : "Xush kelibsiz! 🫖"}
          </h2>

          <p className="text-xs text-theme-muted">
            {tableInfo?.room ? `${tableInfo.room} bo'limi` : "Asosiy Zal"}
          </p>
        </div>

        {/* 4-digit PIN Box */}
        <div className="p-5 rounded-2xl bg-black/40 border-2 border-amber-500/40 space-y-2 shadow-inner">
          <span className="text-[11px] uppercase tracking-wider font-bold text-amber-300/90 block">
            Sizning Stol Kodingiz:
          </span>
          <div className="text-4xl sm:text-5xl font-mono font-black tracking-widest bg-gradient-to-r from-amber-300 via-yellow-200 to-amber-400 bg-clip-text text-transparent">
            {pinCode}
          </div>
          <span className="text-[10px] text-theme-muted block">
            Ofitsiant kelganda ushbu kodni ko'rsating
          </span>
        </div>

        {/* Notification / Warning Message */}
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10 text-xs text-zinc-300 leading-relaxed text-left space-y-2">
          <div className="flex items-center gap-2 text-amber-400 font-bold">
            <Clock className="w-4 h-4 shrink-0 animate-spin-slow" />
            <span>Shoshilmay turing!</span>
          </div>
          <p className="text-[11px] text-theme-muted">
            Hozir ofitsiantimiz stolingizga keladi, ushbu kodni tasdiqlab menyuni faollashtiradi va buyurtma berishni tushuntirib beradi.
          </p>
        </div>

        {/* Status Indicator / Actions */}
        <div className="space-y-3 pt-1">
          <div className="flex items-center justify-center gap-2 text-xs font-semibold text-amber-300">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Ofitsiant tasdiqlashi kutilmoqda...</span>
          </div>

          <button
            onClick={handleCallWaiter}
            disabled={callingWaiter || callSent}
            className="w-full py-3 rounded-xl bg-white/10 hover:bg-white/15 border border-white/10 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            <BellRing className="w-4 h-4 text-amber-400" />
            <span>{callSent ? "✅ Ofitsiantga xabar yuborildi" : "Ofitsiantni chaqirish"}</span>
          </button>
        </div>

        {/* Return Button */}
        {onReturnToLanding && (
          <div className="pt-2 border-t border-theme-border/60">
            <button
              onClick={onReturnToLanding}
              className="text-xs text-theme-muted hover:text-white transition-colors inline-flex items-center gap-1 font-medium"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Bosh sahifaga qaytish</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default TableWaitingVerification;
