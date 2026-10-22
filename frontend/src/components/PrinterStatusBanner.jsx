import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useWebSocket } from '../context/WebSocketContext';
import { api } from '../utils/api';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export const PrinterStatusBanner = () => {
  const [stuckPrinters, setStuckPrinters] = useState([]);
  const { addEventListener } = useWebSocket() || {};
  const isMountedRef = useRef(true);

  const fetchSummary = useCallback(async () => {
    try {
      const data = await api.get('/receipts/print-jobs/summary');
      if (!isMountedRef.current) return;
      if (Array.isArray(data)) {
        // oldest_age_seconds > 20 bo'lgan printerlarni filtrlaymiz
        const stuck = data.filter(
          (p) =>
            p.oldest_age_seconds !== null &&
            p.oldest_age_seconds !== undefined &&
            Number(p.oldest_age_seconds) > 20
        );
        setStuckPrinters(stuck);
      }
    } catch (err) {
      console.warn('Printer summary yuklashda xatolik:', err);
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    fetchSummary();

    // Har 10 soniyada yangilab turish
    const interval = setInterval(() => {
      fetchSummary();
    }, 10000);

    // WebSocket hodisalari: print_alert va print_ok
    const unsubAlert = addEventListener
      ? addEventListener('print_alert', () => {
          fetchSummary();
        })
      : null;

    const unsubOk = addEventListener
      ? addEventListener('print_ok', () => {
          fetchSummary();
        })
      : null;

    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
      if (typeof unsubAlert === 'function') unsubAlert();
      if (typeof unsubOk === 'function') unsubOk();
    };
  }, [fetchSummary, addEventListener]);

  if (!stuckPrinters || stuckPrinters.length === 0) {
    return null;
  }

  return (
    <div className="w-full bg-gradient-to-r from-red-600 via-rose-600 to-red-700 text-white shadow-lg border-b-2 border-red-400 z-50 px-4 py-2 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs sm:text-sm animate-in slide-in-from-top duration-300">
      <div className="flex items-center gap-2.5 min-w-0">
        <div className="p-1.5 rounded-lg bg-black/25 text-white animate-pulse shrink-0">
          <AlertTriangle className="w-4 h-4 text-amber-300" />
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2 truncate font-bold">
          {stuckPrinters.map((p, idx) => (
            <span key={p.printer_name || idx} className="truncate">
              Printer ishlamayapti: <span className="underline decoration-amber-300 decoration-2 font-black">{p.printer_name || 'Noma\'lum'}</span> — {p.pending_count || 1} ta chek kutmoqda
              {p.last_error && <span className="text-[11px] font-normal opacity-90 ml-1.5">({p.last_error})</span>}
              {idx < stuckPrinters.length - 1 ? ' | ' : ''}
            </span>
          ))}
        </div>
      </div>
      <button
        onClick={fetchSummary}
        className="px-2.5 py-1 rounded-lg bg-black/25 hover:bg-black/40 text-white font-semibold text-xs transition-all active:scale-95 shrink-0 flex items-center gap-1.5"
        title="Qayta tekshirish"
      >
        <RefreshCw className="w-3 h-3" />
        <span>Yangilash</span>
      </button>
    </div>
  );
};

export default PrinterStatusBanner;
